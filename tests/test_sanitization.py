import sys
import os
import unittest
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.features import sanitize_market_dataframe, compute_12_features


class TestDataSanitization(unittest.TestCase):
    def test_sanitize_market_dataframe_filters_corrupt_rows(self):
        raw_data = [
            {"time": "2026-08-02T10:00:00", "open": 1.0500, "high": 1.0510, "low": 1.0490, "close": 1.0505, "volume": 100}, # Valid
            {"time": "2026-08-02T10:05:00", "open": 0.0, "high": 1.0510, "low": 1.0490, "close": 1.0505, "volume": 100},    # Zero Open (Invalid)
            {"time": "2026-08-02T10:10:00", "open": 1.0500, "high": 1.0400, "low": 1.0490, "close": 1.0505, "volume": 100}, # High < Low (Invalid)
            {"time": "2026-08-02T10:15:00", "open": 1.0500, "high": 1.0500, "low": 1.0500, "close": 1.0500, "volume": 0},   # Dead zero vol bar (Invalid)
            {"time": "2026-08-02T10:20:00", "open": 1.0500, "high": 2.5000, "low": 1.0490, "close": 2.5000, "volume": 100}, # Extreme >30% spike (Invalid)
            {"time": "2026-08-02T10:25:00", "open": 1.0505, "high": 1.0520, "low": 1.0500, "close": 1.0515, "volume": 120}, # Valid
            {"time": "2026-08-02T10:25:00", "open": 1.0505, "high": 1.0520, "low": 1.0500, "close": 1.0515, "volume": 120}, # Duplicate timestamp
        ]

        df_raw = pd.DataFrame(raw_data)
        df_clean = sanitize_market_dataframe(df_raw)

        # Should keep only rows 0 and 5 (row 6 is duplicate of row 5)
        self.assertEqual(len(df_clean), 2)
        self.assertEqual(df_clean.iloc[0]['close'], 1.0505)
        self.assertEqual(df_clean.iloc[1]['close'], 1.0515)

    def test_compute_12_features_on_clean_data(self):
        raw_data = [
            {"time": f"2026-08-02T10:{i:02d}:00", "open": 1.0500 + i * 0.0001, "high": 1.0505 + i * 0.0001, "low": 1.0495 + i * 0.0001, "close": 1.0502 + i * 0.0001, "volume": 100 + i * 5}
            for i in range(15)
        ]
        df = pd.DataFrame(raw_data)
        df_clean = sanitize_market_dataframe(df)
        matrix = compute_12_features(df_clean)

        self.assertEqual(matrix.shape, (15, 12))
        self.assertFalse(np.isnan(matrix).any())
        self.assertFalse(np.isinf(matrix).any())


if __name__ == "__main__":
    unittest.main()
