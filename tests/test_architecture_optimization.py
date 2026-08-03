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


class TestArchitectureOptimization(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_architecture_search.db"
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

        # Insert 160 realistic candle rows
        base_price = 1.1000
        start_time = datetime.datetime(2026, 8, 1, 0, 0, 0)
        for i in range(160):
            ts = (start_time + datetime.timedelta(minutes=5 * i)).isoformat()
            open_p = base_price + (i % 4) * 0.0004
            high_p = open_p + 0.0012
            low_p = open_p - 0.0009
            close_p = open_p + (0.0006 if i % 2 == 0 else -0.0005)
            vol = 300 + i * 2
            decision = "UP" if i % 3 == 0 else ("DOWN" if i % 3 == 1 else "HOLD")
            cursor.execute('''
                INSERT INTO shadow_states 
                (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ts, "EURUSD", "M5", open_p, high_p, low_p, close_p, vol, "{}", "{}", "TRENDING", decision))

        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_optimize_architecture_search(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path)
        search_res = engine.optimize_architecture(
            candidate_hidden_sizes=[32, 64],
            candidate_num_layers=[1, 2],
            candidate_dropouts=[0.2, 0.3, 0.4],
            train_ratio=0.8,
            epochs=2
        )

        self.assertIn("best_config", search_res)
        self.assertIn("trials", search_res)
        self.assertGreater(len(search_res["trials"]), 0)
        best_cfg = search_res["best_config"]
        self.assertIn(best_cfg["hidden_size"], [32, 64])
        self.assertIn(best_cfg["num_layers"], [1, 2])
        self.assertIn(best_cfg["dropout"], [0.2, 0.3, 0.4])
        self.assertEqual(engine.model.hidden_size, best_cfg["hidden_size"])
        self.assertEqual(engine.model.num_layers, best_cfg["num_layers"])
        self.assertEqual(engine.model.dropout_rate, best_cfg["dropout"])
        self.assertIn("dropout", search_res["trials"][0])

    def test_dynamic_model_reload_after_architecture_change(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path)
        engine.optimize_architecture(
            candidate_hidden_sizes=[32, 128],
            candidate_num_layers=[1],
            train_ratio=0.8,
            epochs=1
        )
        saved_h = engine.model.hidden_size
        saved_l = engine.model.num_layers

        # Re-instantiate engine from saved checkpoint file
        reloaded_engine = PredictorEngine(db_path=self.db_path)
        self.assertTrue(reloaded_engine.is_trained)
        self.assertEqual(reloaded_engine.model.hidden_size, saved_h)
        self.assertEqual(reloaded_engine.model.num_layers, saved_l)


if __name__ == "__main__":
    unittest.main()
