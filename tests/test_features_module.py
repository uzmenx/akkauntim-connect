import sys
import os
import unittest
import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.features import (
    calculate_rsi,
    calculate_atr,
    calculate_ma_diff,
    calculate_momentum,
    calculate_volume_change,
    calculate_body_to_range_ratio,
    calculate_time_sine_encoding,
    compute_12_features,
    compute_12_features_dict
)


class TestFeaturesModule(unittest.TestCase):
    def test_individual_indicator_functions(self):
        close = pd.Series([100 + i for i in range(20)], dtype=float)
        high = close + 2.0
        low = close - 1.0
        open_p = close - 0.5
        vol = pd.Series([1000 + i * 50 for i in range(20)], dtype=float)
        times = pd.Series([f"2026-08-02T{i:02d}:00:00" for i in range(20)])

        rsi = calculate_rsi(close, period=14)
        self.assertEqual(len(rsi), 20)
        self.assertTrue((rsi >= 0.0).all() and (rsi <= 100.0).all())

        atr = calculate_atr(high, low, close, period=14)
        self.assertEqual(len(atr), 20)
        self.assertTrue((atr >= 0.0).all())

        ma_diff = calculate_ma_diff(close, fast_period=5, slow_period=20)
        self.assertEqual(len(ma_diff), 20)

        mom = calculate_momentum(close, period=5)
        self.assertEqual(len(mom), 20)

        vol_chg = calculate_volume_change(vol)
        self.assertEqual(len(vol_chg), 20)

        body_ratio = calculate_body_to_range_ratio(open_p, high, low, close)
        self.assertEqual(len(body_ratio), 20)
        self.assertTrue((body_ratio >= 0.0).all() and (body_ratio <= 1.0).all())

        time_sin = calculate_time_sine_encoding(times)
        self.assertEqual(len(time_sin), 20)
        self.assertTrue((time_sin >= -1.0).all() and (time_sin <= 1.0).all())

    def test_compute_12_features_matrix(self):
        candles = [
            {
                "open": 1.0800 + i * 0.0001,
                "high": 1.0805 + i * 0.0001,
                "low": 1.0795 + i * 0.0001,
                "close": 1.0802 + i * 0.0001,
                "volume": 500 + i * 10,
                "time": f"2026-08-02T{(i % 24):02d}:00:00"
            }
            for i in range(25)
        ]

        matrix = compute_12_features(candles)
        self.assertEqual(matrix.shape, (25, 12))
        self.assertFalse(np.isnan(matrix).any())
        self.assertFalse(np.isinf(matrix).any())

    def test_compute_12_features_dict(self):
        candle = {
            "open": 1.0800,
            "high": 1.0810,
            "low": 1.0790,
            "close": 1.0805,
            "volume": 600,
            "time": "2026-08-02T15:30:00"
        }

        res = compute_12_features_dict(candle)
        self.assertIn("f12_vector", res)
        self.assertEqual(len(res["f12_vector"]), 12)
        self.assertEqual(res["open"], 1.0800)
        self.assertEqual(res["high"], 1.0810)


if __name__ == "__main__":
    unittest.main()
