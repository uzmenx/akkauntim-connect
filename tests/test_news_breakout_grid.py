import unittest
from bot.strategy.news_breakout_grid.risk_guard import GridRiskGuard
from bot.strategy.news_breakout_grid.pause_detector import PauseDetector
from bot.config import BotConfig

class TestNewsBreakoutGrid(unittest.TestCase):
    def test_pause_detector(self):
        detector = PauseDetector(pause_threshold_sec=2.0, high_vol_threshold=2.0, pause_vol_threshold=0.5)
        
        # Not enough data
        self.assertFalse(detector.update(100.0))
        
        # Simulate high volatility
        for i in range(10):
            detector.update(100.0 + i)
            
        # Simulate pause
        import time
        detector.history.clear()
        
        now = time.time()
        # High vol before 2 seconds ago
        for j in range(5):
            detector.history.append((now - 5 + j*0.1, 100.0 + j))
            
        # Low vol in the last 2 seconds
        for j in range(5):
            detector.history.append((now - 1.5 + j*0.2, 105.1 + j*0.01))
        
        self.assertTrue(detector.update(105.2))

    def test_risk_guard(self):
        guard = GridRiskGuard(max_daily_loss_pct=0.40, max_attempts_per_day=5, initial_balance=1000.0)
        
        self.assertTrue(guard.can_trade())
        guard.record_attempt()
        self.assertEqual(guard.attempts_today, 1)
        
        guard.record_pnl(-200.0) # Lost 200 (20%)
        self.assertTrue(guard.can_trade())
        
        guard.record_pnl(-250.0) # Lost another 250 (Total 450 > 400)
        self.assertFalse(guard.can_trade())
        self.assertTrue(guard.is_stopped)

if __name__ == "__main__":
    unittest.main()
