import sys
import os
import sqlite3
import datetime
import unittest
import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.predictor import (
    compute_12_features,
    MarketPredictorLSTM,
    ShadowDataset,
    PredictorEngine,
    TORCH_AVAILABLE
)


class TestPredictor12Features(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_predictor_12f.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

        # Create dummy database with 150 rows of shadow_states
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

        base_price = 1.0500
        now = datetime.datetime.now()
        for i in range(150):
            ts = (now + datetime.timedelta(minutes=5 * i)).isoformat()
            open_p = base_price + (i % 5) * 0.0001
            high_p = open_p + 0.0003
            low_p = open_p - 0.0002
            close_p = open_p + ((i % 3) - 1) * 0.0002
            vol = 100 + i * 2
            cursor.execute('''
                INSERT INTO shadow_states 
                (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ts, "EURUSD", "M5", open_p, high_p, low_p, close_p, vol, "{}", "{}", "TRENDING", "HOLD"))

        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_compute_12_features_shape_and_cleanliness(self):
        candles = [
            {
                "open": 1.0500 + i * 0.0001,
                "high": 1.0505 + i * 0.0001,
                "low": 1.0495 + i * 0.0001,
                "close": 1.0502 + i * 0.0001,
                "tick_volume": 100 + i * 5,
                "time": f"2026-08-02T12:{i:02d}:00"
            }
            for i in range(30)
        ]

        features = compute_12_features(candles)
        self.assertEqual(features.shape, (30, 12))
        self.assertFalse(np.isnan(features).any(), "Features contain NaNs")
        self.assertFalse(np.isinf(features).any(), "Features contain Infs")

    def test_market_predictor_lstm_dimensions(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        model = MarketPredictorLSTM(input_size=12, hidden_size=64, num_layers=2, num_classes=3)
        self.assertEqual(model.input_size, 12)

        import torch
        dummy_input = torch.randn(2, 10, 12)  # batch=2, seq_len=10, features=12
        output = model(dummy_input)
        self.assertEqual(output.shape, (2, 3))

        state = model.get_network_state()
        self.assertEqual(state["status"], "active")
        self.assertIn("output_probabilities", state)

    def test_predictor_engine_predict_and_train(self):
        predictor = PredictorEngine(db_path=self.db_path)
        self.assertIsNotNone(predictor.model)
        if TORCH_AVAILABLE:
            self.assertEqual(predictor.model.input_size, 12)

        candles = [
            {
                "open": 1.0800 + i * 0.0001,
                "high": 1.0805 + i * 0.0001,
                "low": 1.0795 + i * 0.0001,
                "close": 1.0801 + i * 0.0001,
                "tick_volume": 120 + i,
                "time": f"2026-08-02T14:{i:02d}:00"
            }
            for i in range(15)
        ]

        res = predictor.predict(candles)
        self.assertIn("prediction", res)
        self.assertIn(res["prediction"], ["UP", "DOWN", "HOLD"])
        self.assertIn("confidence", res)
        self.assertIn("network_state", res)

        if TORCH_AVAILABLE:
            predictor.train_incremental()
            self.assertTrue(predictor.is_trained)


if __name__ == "__main__":
    unittest.main()
