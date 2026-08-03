import sys
import os
import sqlite3
import json
import unittest
import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.shadow_collector import ShadowStateCollector


class TestShadowCollector12Features(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_shadow_collector_12f.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
        self.collector = ShadowStateCollector(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_record_state_computes_and_saves_12_features(self):
        now = datetime.datetime.now()
        recent_candles = []
        for i in range(20):
            ts = (now + datetime.timedelta(minutes=15 * i)).isoformat()
            candle = {
                'open': 1.1000 + i * 0.0002,
                'high': 1.1005 + i * 0.0002,
                'low': 1.0995 + i * 0.0002,
                'close': 1.1003 + i * 0.0002,
                'tick_volume': 150 + i * 10,
                'time': ts
            }
            recent_candles.append(candle)

        last_candle = recent_candles[-1]
        self.collector.record_state(
            symbol="EURUSD",
            timeframe="H1",
            candle=last_candle,
            smc_context={"structure": "BULLISH"},
            indicators={"pattern": "ENGULFING"},
            market_regime="TRENDING",
            ai_decision="BUY",
            recent_candles=recent_candles
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT indicators, f12_features FROM shadow_states ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        indicators_json = json.loads(row[0])
        f12_json = json.loads(row[1])

        self.assertIn("f12_features", indicators_json)
        self.assertIn("rsi_14", f12_json)
        self.assertIn("atr_14", f12_json)
        self.assertIn("ma_diff", f12_json)
        self.assertIn("momentum", f12_json)
        self.assertIn("vol_change", f12_json)
        self.assertIn("body_ratio", f12_json)
        self.assertIn("time_sin", f12_json)
        self.assertIn("f12_vector", f12_json)
        self.assertEqual(len(f12_json["f12_vector"]), 12)


if __name__ == "__main__":
    unittest.main()
