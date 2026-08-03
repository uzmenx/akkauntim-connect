import sys
import os
import sqlite3
import datetime
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.predictor import (
    ShadowDataset,
    PredictorEngine,
    TORCH_AVAILABLE
)


class TestClassImbalanceHandling(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_class_imbalance.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE shadow_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                price_open REAL,
                price_high REAL,
                price_low REAL,
                price_close REAL,
                tick_volume REAL,
                smc_context TEXT,
                indicators TEXT,
                market_regime TEXT,
                ai_decision TEXT
            )
        ''')

        # Insert 150 rows where price barely moves (80%+ HOLD class dominance)
        base_price = 1.0500
        start_time = datetime.datetime(2026, 8, 1, 0, 0, 0)
        for i in range(150):
            ts = (start_time + datetime.timedelta(minutes=5 * i)).isoformat()
            # Very small fluctuations so mostly HOLD class
            open_p = base_price
            high_p = base_price + 0.00001
            low_p = base_price - 0.00001
            close_p = base_price
            vol = 100
            cursor.execute('''
                INSERT INTO shadow_states 
                (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ts, "EURUSD", "M5", open_p, high_p, low_p, close_p, vol, "{}", "{}", "RANGING", "HOLD"))

        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_class_distribution_and_critical_imbalance(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        ds = ShadowDataset(self.db_path, seq_length=10, split='all')
        dist = ds.get_class_distribution()

        self.assertGreater(dist["total"], 0)
        self.assertIn("counts", dist)
        self.assertIn("percentages", dist)
        self.assertTrue(dist["has_critical_imbalance"], "Expected critical imbalance due to flat market prices")
        self.assertEqual(len(dist["class_weights"]), 3)

    def test_predictor_engine_check_imbalance(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path)
        audit = engine.check_class_imbalance()
        self.assertIn("imbalance_ratio", audit)
        self.assertIn("class_weights", audit)

    def test_predictor_train_with_class_weighting(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path)
        engine.train_incremental(train_ratio=0.8, epochs=2)
        self.assertTrue(engine.is_trained)


if __name__ == "__main__":
    unittest.main()
