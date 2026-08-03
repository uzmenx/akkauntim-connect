import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from bot.strategy.smc.engine import analyze_smc
from bot.strategy.harmonic.engine import analyze_harmonic_patterns
from bot.strategy.wyckoff.engine import analyze_wyckoff
from bot.strategy.sr_volume.engine import analyze_sr_volume
from bot.strategy.auto_patterns.engine import analyze_auto_patterns

class TestStrategyGeometrics(unittest.TestCase):
    def setUp(self):
        dates = [datetime.now() - timedelta(hours=x) for x in range(200)]
        dates.reverse()
        
        np.random.seed(42)
        base_price = 100.0
        prices = base_price + np.cumsum(np.random.randn(200) * 0.3)
        
        self.df = pd.DataFrame({
            'open': prices,
            'high': prices + np.random.uniform(0.1, 0.5, 200),
            'low': prices - np.random.uniform(0.1, 0.5, 200),
            'close': prices + np.random.uniform(-0.2, 0.2, 200),
            'tick_volume': np.random.randint(100, 1000, 200)
        }, index=dates)

    def test_wyckoff_geometrics(self):
        res = analyze_wyckoff(self.df)
        self.assertIn("phase", res)
        self.assertIn("trading_range", res)
        self.assertIn("spring_upthrust", res)
        self.assertIn("event_details", res)
        
        event_details = res["event_details"]
        self.assertIn("type", event_details)
        self.assertIn("event_bar_index", event_details)
        self.assertIn("event_time", event_details)

    def test_sr_volume_geometrics(self):
        res = analyze_sr_volume(self.df)
        self.assertIn("signal", res)
        self.assertIn("support_zone", res)
        self.assertIn("resistance_zone", res)
        self.assertIn("event_details", res)
        
        if res["support_zone"]:
            self.assertIn("top", res["support_zone"])
            self.assertIn("bottom", res["support_zone"])
            self.assertIn("bar_index", res["support_zone"])
            self.assertIn("time", res["support_zone"])
            
        if res["resistance_zone"]:
            self.assertIn("top", res["resistance_zone"])
            self.assertIn("bottom", res["resistance_zone"])
            self.assertIn("bar_index", res["resistance_zone"])
            self.assertIn("time", res["resistance_zone"])

    def test_harmonic_geometrics(self):
        res = analyze_harmonic_patterns(self.df)
        self.assertIn("signal", res)
        self.assertIn("active_pattern", res)
        self.assertIn("all_detected_patterns", res)
        
        if res["active_pattern"]:
            pat = res["active_pattern"]
            self.assertIn("xabcd_points", pat)
            self.assertIn("xabcd_coords", pat)
            self.assertIn("xabcd_times", pat)
            self.assertIn("xabcd_bar_indices", pat)

    def test_auto_patterns_geometrics(self):
        res = analyze_auto_patterns(self.df)
        self.assertIn("signal", res)
        self.assertIn("pivots", res)
        self.assertIn("pattern_points", res)
        
        for pivot in res["pivots"]:
            self.assertIn("index", pivot)
            self.assertIn("bar_index", pivot)
            self.assertIn("price", pivot)
            self.assertIn("type", pivot)
            self.assertIn("time", pivot)
            self.assertIn("timestamp", pivot)

if __name__ == '__main__':
    unittest.main()
