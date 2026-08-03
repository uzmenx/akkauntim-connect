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


class TestInstitutionalMultiSymbolABImportance(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_institutional_learning.db"
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

        # Insert EURUSD data (lower volatility)
        base_eur = 1.0800
        start_time = datetime.datetime(2026, 8, 1, 0, 0, 0)
        for i in range(120):
            ts = (start_time + datetime.timedelta(minutes=5 * i)).isoformat()
            open_p = base_eur + (i % 3) * 0.0005
            high_p = open_p + 0.0010
            low_p = open_p - 0.0008
            close_p = open_p + (0.0004 if i % 2 == 0 else -0.0004)
            vol = 500 + i * 5
            cursor.execute('''
                INSERT INTO shadow_states 
                (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ts, "EURUSD", "M5", open_p, high_p, low_p, close_p, vol, "{}", "{}", "TRENDING_UP", "UP" if i % 2 == 0 else "DOWN"))

        # Insert XAUUSD (Gold) data (much higher price scale & volatility)
        base_gold = 2400.00
        for i in range(120):
            ts = (start_time + datetime.timedelta(minutes=5 * i)).isoformat()
            open_p = base_gold + (i % 5) * 5.5
            high_p = open_p + 15.0
            low_p = open_p - 12.0
            close_p = open_p + (8.0 if i % 3 == 0 else -6.0)
            vol = 2500 + i * 10
            cursor.execute('''
                INSERT INTO shadow_states 
                (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ts, "XAUUSD", "M5", open_p, high_p, low_p, close_p, vol, "{}", "{}", "HIGH_VOLATILITY", "UP" if i % 3 == 0 else "DOWN"))

        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_multi_symbol_strategy_evaluation(self):
        engine = PredictorEngine(db_path=self.db_path)
        strategy_audit = engine.evaluate_multi_symbol_strategy()

        self.assertIn("symbols", strategy_audit)
        self.assertIn("EURUSD", strategy_audit["symbols"])
        self.assertIn("XAUUSD", strategy_audit["symbols"])
        self.assertTrue(strategy_audit["should_use_per_symbol"])
        self.assertIn("USE_PER_SYMBOL_MODELS", strategy_audit["recommendation"])

    def test_per_symbol_dataset_and_engine(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        ds_eur = ShadowDataset(self.db_path, seq_length=10, split='all', symbol="EURUSD")
        ds_gold = ShadowDataset(self.db_path, seq_length=10, split='all', symbol="XAUUSD")

        self.assertGreater(len(ds_eur), 0)
        self.assertGreater(len(ds_gold), 0)

        # EURUSD engine training
        eur_engine = PredictorEngine(db_path=self.db_path, symbol="EURUSD")
        eur_engine.train_incremental(train_ratio=0.8, epochs=2)
        self.assertTrue(eur_engine.is_trained)
        self.assertIn("EURUSD", eur_engine.model_path)

    def test_ab_model_benchmark(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path, symbol="EURUSD")
        engine.train_incremental(train_ratio=0.8, epochs=2)

        ab_report = engine.compare_models_ab()
        self.assertIn("model_b_new", ab_report)
        self.assertIn("verdict", ab_report)
        self.assertIn("accuracy", ab_report["model_b_new"])
        self.assertIn("macro_f1", ab_report["model_b_new"])

    def test_permutation_feature_importance(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path, symbol="EURUSD")
        engine.train_incremental(train_ratio=0.8, epochs=2)

        importance = engine.calculate_feature_importance(n_repeats=2)
        self.assertIn("baseline_macro_f1", importance)
        self.assertIn("feature_importance_ranking", importance)
        self.assertEqual(len(importance["feature_importance_ranking"]), 12)
        first = importance["feature_importance_ranking"][0]
        self.assertIn("feature_name", first)
        self.assertIn("importance_score", first)
        self.assertIn("classification", first)


if __name__ == "__main__":
    unittest.main()
