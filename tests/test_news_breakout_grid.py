import pytest
from bot.strategy.news_breakout_grid.risk_guard import GridRiskGuard
from bot.strategy.news_breakout_grid.pause_detector import PauseDetector
from bot.config import BotConfig

def test_pause_detector():
    detector = PauseDetector(pause_threshold_sec=2.0, high_vol_threshold=2.0, pause_vol_threshold=0.5)
    
    # Not enough data
    assert detector.update(100.0) == False
    
    # Simulate high volatility
    for i in range(10):
        detector.update(100.0 + i)
        
    # Simulate pause
    import time
    # We would need to mock time for proper testing, but let's just test basic logic
    detector.history.clear()
    
    now = time.time()
    # High vol before 2 seconds ago
    for j in range(5):
        detector.history.append((now - 5 + j*0.1, 100.0 + j))
        
    # Low vol in the last 2 seconds
    for j in range(5):
        detector.history.append((now - 1.5 + j*0.2, 105.1 + j*0.01))
    
    # Override time.time in the update method if possible, or just call update
    assert detector.update(105.2) == True

def test_risk_guard():
    guard = GridRiskGuard(max_daily_loss_pct=0.40, max_attempts_per_day=5, initial_balance=1000.0)
    
    assert guard.can_trade() == True
    guard.record_attempt()
    assert guard.attempts_today == 1
    
    guard.record_pnl(-200.0) # Lost 200 (20%)
    assert guard.can_trade() == True
    
    guard.record_pnl(-250.0) # Lost another 250 (Total 450 > 400)
    assert guard.can_trade() == False
    assert guard.is_stopped == True
