import sys
import os
import sqlite3
import datetime
import unittest
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.predictor import (
    ShadowDataset,
    PredictorEngine,
    TORCH_AVAILABLE
)


class TestChronologicalSplit(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_chrono_split.db"
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

        base_price = 1.0500
        start_time = datetime.datetime(2026, 8, 1, 0, 0, 0)
        # Create 200 chronological candles (5 min intervals)
        for i in range(200):
            ts = (start_time + datetime.timedelta(minutes=5 * i)).isoformat()
            open_p = base_price + (i % 7) * 0.0001
            high_p = open_p + 0.0004
            low_p = open_p - 0.0003
            close_p = open_p + ((i % 5) - 2) * 0.0002
            vol = 100 + i * 3
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

    def test_chronological_split_no_overlap_or_lookahead(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        train_ds = ShadowDataset(self.db_path, seq_length=10, split='train', train_ratio=0.8)
        val_ds = ShadowDataset(self.db_path, seq_length=10, split='val', train_ratio=0.8, scaler=train_ds.scaler)

        self.assertGreater(len(train_ds), 0)
        self.assertGreater(len(val_ds), 0)

        # Train timestamps must be strictly earlier than Val timestamps
        train_max_ts = max(train_ds.timestamps)
        val_min_ts = min(val_ds.timestamps)

        self.assertLess(train_max_ts, val_min_ts, "Train dataset max timestamp must be strictly less than Val dataset min timestamp")

    def test_predictor_engine_incremental_train_with_val(self):
        if not TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed")

        engine = PredictorEngine(db_path=self.db_path)
        engine.train_incremental(train_ratio=0.8, epochs=2)
        self.assertTrue(engine.is_trained)


if __name__ == "__main__":
    unittest.main()
