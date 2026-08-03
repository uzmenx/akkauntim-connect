import unittest
import os
import tempfile
from bot.strategy.harmonic.manager import HarmonicPatternManager
from bot.strategy.wyckoff.manager import WyckoffEventManager
from bot.strategy.sr_volume.manager import SRVolumeZoneManager
from bot.strategy.auto_patterns.manager import AutoPatternManager

class TestStrategyManagers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.harmonic_db = os.path.join(self.temp_dir.name, "harmonic.db")
        self.wyckoff_db = os.path.join(self.temp_dir.name, "wyckoff.db")
        self.sr_db = os.path.join(self.temp_dir.name, "sr.db")
        self.auto_db = os.path.join(self.temp_dir.name, "auto.db")

        self.harmonic_mgr = HarmonicPatternManager(db_path=self.harmonic_db)
        self.wyckoff_mgr = WyckoffEventManager(db_path=self.wyckoff_db)
        self.sr_mgr = SRVolumeZoneManager(db_path=self.sr_db)
        self.auto_mgr = AutoPatternManager(db_path=self.auto_db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_harmonic_manager(self):
        mock_result = {
            "signal": "BUY",
            "active_pattern": {
                "name": "Gartley",
                "direction": "Bullish",
                "xabcd_coords": {
                    "x": {"price": 100.0, "time": "2026-08-01 10:00", "bar_index": 10},
                    "a": {"price": 105.0, "time": "2026-08-01 11:00", "bar_index": 15},
                    "b": {"price": 102.0, "time": "2026-08-01 12:00", "bar_index": 20},
                    "c": {"price": 104.0, "time": "2026-08-01 13:00", "bar_index": 25},
                    "d": {"price": 101.0, "time": "2026-08-01 14:00", "bar_index": 30}
                },
                "bars_since_d": 5
            },
            "all_detected_patterns": [
                {"name": "ABCD", "direction": "Bullish", "d_price": 101.0, "time": "2026-08-01 14:00", "bar_index": 30}
            ]
        }

        inserted = self.harmonic_mgr.save_patterns("EURUSD", "H1", mock_result)
        self.assertGreaterEqual(inserted, 1)

        active = self.harmonic_mgr.get_active_patterns("EURUSD", "H1")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["pattern_name"], "Gartley")
        self.assertEqual(active[0]["direction"], "Bullish")
        self.assertEqual(active[0]["d_price"], 101.0)

        # BaseStrategyManager inherited methods test
        self.assertEqual(self.harmonic_mgr.count_records("EURUSD", "H1"), 2)
        rec_id = active[0]["id"]
        marked = self.harmonic_mgr.mark_stale(rec_id, "stale")
        self.assertTrue(marked)
        self.assertEqual(len(self.harmonic_mgr.get_active_patterns("EURUSD", "H1")), 0)

    def test_wyckoff_manager(self):
        mock_result = {
            "phase": "Accumulation",
            "spring_upthrust": "Spring",
            "trading_range": {"is_ranging": True, "top": 1.1000, "bottom": 1.0800},
            "event_details": {
                "type": "Spring",
                "event_bar_index": 45,
                "event_time": "2026-08-01 15:00",
                "price": 1.0790,
                "level_broken": 1.0800
            },
            "momentum_sign": "SOS",
            "momentum_details": {
                "type": "SOS",
                "event_bar_index": 48,
                "event_time": "2026-08-01 16:00",
                "price": 1.0850
            }
        }

        inserted = self.wyckoff_mgr.save_events("EURUSD", "H1", mock_result)
        self.assertGreaterEqual(inserted, 1)

        active = self.wyckoff_mgr.get_active_events("EURUSD", "H1")
        self.assertGreaterEqual(len(active), 1)
        event_types = [e["event_type"] for e in active]
        self.assertIn("Spring", event_types)

        # Inherited count test
        self.assertGreaterEqual(self.wyckoff_mgr.count_records("EURUSD"), 1)

    def test_sr_volume_manager(self):
        mock_result = {
            "signal": "BUY",
            "confidence": 75.0,
            "support_zone": {"top": 1.0820, "bottom": 1.0800, "bar_index": 50, "time": "2026-08-01 12:00"},
            "resistance_zone": {"top": 1.0950, "bottom": 1.0930, "bar_index": 40, "time": "2026-08-01 10:00"}
        }

        inserted = self.sr_mgr.save_zones("EURUSD", "H1", mock_result)
        self.assertEqual(inserted, 2)

        active = self.sr_mgr.get_active_zones("EURUSD", "H1")
        self.assertEqual(len(active), 2)
        zone_types = [z["zone_type"] for z in active]
        self.assertIn("support", zone_types)
        self.assertIn("resistance", zone_types)

        # Inherited mark_stale test
        rec_id = active[0]["id"]
        self.sr_mgr.mark_stale(rec_id, "mitigated")
        self.assertEqual(len(self.sr_mgr.get_active_zones("EURUSD", "H1")), 1)

    def test_auto_pattern_manager(self):
        mock_result = {
            "pattern_name": "Double Bottom",
            "signal": "BUY",
            "confidence": 80.0,
            "slopes": {"res": 0.001, "sup": -0.001},
            "pivots": [
                {"bar_index": 10, "price": 1.0800, "type": "Low", "time": "2026-08-01 08:00"},
                {"bar_index": 20, "price": 1.0900, "type": "High", "time": "2026-08-01 09:00"},
                {"bar_index": 30, "price": 1.0805, "type": "Low", "time": "2026-08-01 10:00"}
            ],
            "pattern_points": {
                "h1": {"index": 20, "price": 1.0900},
                "l1": {"index": 10, "price": 1.0800},
                "l2": {"index": 30, "price": 1.0805}
            }
        }

        inserted = self.auto_mgr.save_pattern("EURUSD", "H1", mock_result)
        self.assertEqual(inserted, 1)

        active = self.auto_mgr.get_active_patterns("EURUSD", "H1")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["pattern_name"], "Double Bottom")
        self.assertEqual(active[0]["signal"], "BUY")
        self.assertEqual(len(active[0]["pivots"]), 3)

if __name__ == '__main__':
    unittest.main()
