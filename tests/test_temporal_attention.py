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
    MarketPredictorLSTM,
    TemporalCandleAttention,
    TORCH_AVAILABLE
)

if TORCH_AVAILABLE:
    import torch


class TestTemporalAttentionMechanism(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_temporal_attention.db"
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

        # Populate 180 rows of clean market data for Stage 2 readiness tests
        base_price = 1.0800
        start_time = datetime.datetime(2026, 8, 1, 0, 0, 0)
        for i in range(180):
            ts = (start_time + datetime.timedelta(minutes=5 * i)).isoformat()
            open_p = base_price + (i % 5) * 0.0005
            high_p = open_p + 0.0015
            low_p = open_p - 0.0010
            close_p = open_p + (0.0008 if i % 2 == 0 else -0.0006)
            vol = 400 + i * 3
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

    def test_attention_module_standalone(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        batch_size = 4
        seq_len = 10
        hidden_size = 64

        attn_layer = TemporalCandleAttention(hidden_size=hidden_size)
        dummy_lstm_out = torch.randn(batch_size, seq_len, hidden_size)

        context, weights = attn_layer(dummy_lstm_out)

        self.assertEqual(context.shape, (batch_size, hidden_size))
        self.assertEqual(weights.shape, (batch_size, seq_len, 1))

        # Check softmax normalization (weights for each sequence sum to 1.0)
        sums = torch.sum(weights, dim=1).squeeze(-1)
        for val in sums:
            self.assertAlmostEqual(val.item(), 1.0, places=4)

    def test_lstm_model_with_attention_flag(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        model_attn = MarketPredictorLSTM(input_size=12, hidden_size=64, num_layers=2, use_attention=True)
        dummy_x = torch.randn(2, 10, 12)

        out = model_attn(dummy_x)
        self.assertEqual(out.shape, (2, 3))
        self.assertIsNotNone(model_attn.last_attention_weights)
        self.assertEqual(model_attn.last_attention_weights.shape, (2, 10, 1))

        net_state = model_attn.get_network_state()
        self.assertTrue(net_state["use_attention"])
        self.assertIn("attention_weights", net_state)

    def test_evaluate_attention_readiness(self):
        engine = PredictorEngine(db_path=self.db_path)

        # min_samples = 200 -> 180 samples in DB, should return fallback
        res_insufficient = engine.evaluate_attention_readiness(min_samples=200)
        self.assertFalse(res_insufficient["stage2_ready"])
        self.assertEqual(res_insufficient["recommendation"], "USE_STANDARD_LSTM_FALLBACK")

        # min_samples = 100 -> 180 samples in DB, should pass Stage 2 check
        res_ready = engine.evaluate_attention_readiness(min_samples=100)
        self.assertTrue(res_ready["stage2_ready"])
        self.assertEqual(res_ready["recommendation"], "ENABLE_TEMPORAL_ATTENTION")
        self.assertTrue(res_ready["has_balanced_classes"])
        self.assertTrue(res_ready["has_clean_features"])

    def test_train_and_predict_with_attention(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path)
        engine.train_incremental(train_ratio=0.8, epochs=2, force_attention=True)

        self.assertTrue(engine.model.use_attention)

        mock_candles = [
            {"open": 1.0800 + i * 0.0001, "high": 1.0810, "low": 1.0790, "close": 1.0805, "volume": 500 + i * 10}
            for i in range(12)
        ]

        pred_res = engine.predict(mock_candles)
        self.assertIn("prediction", pred_res)
        self.assertIn("confidence", pred_res)
        self.assertIn("attention_weights", pred_res)
        self.assertIn("most_important_candle_index", pred_res)
        self.assertEqual(len(pred_res["attention_weights"]), 10)
        self.assertGreaterEqual(pred_res["most_important_candle_index"], 0)
        self.assertLess(pred_res["most_important_candle_index"], 10)

    def test_attention_model_checkpoint_persistence(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path)
        engine.train_incremental(train_ratio=0.8, epochs=1, force_attention=True)

        # Reload engine from saved checkpoint file
        reloaded_engine = PredictorEngine(db_path=self.db_path)
        self.assertTrue(reloaded_engine.is_trained)
        self.assertTrue(reloaded_engine.model.use_attention)
        self.assertIsNotNone(reloaded_engine.model.attention)


if __name__ == "__main__":
    unittest.main()
