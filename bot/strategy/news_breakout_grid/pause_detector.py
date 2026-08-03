import time
from collections import deque
import logging

logger = logging.getLogger(__name__)

class PauseDetector:
    def __init__(self, pause_threshold_sec: float = 2.0, high_vol_threshold: float = 2.0, pause_vol_threshold: float = 0.5):
        """
        :param pause_threshold_sec: How many seconds to consider as the "pause" window.
        :param high_vol_threshold: The minimum price movement required before the pause (in absolute price units).
        :param pause_vol_threshold: The maximum allowed price movement during the pause window (in absolute price units).
        """
        self.pause_threshold_sec = pause_threshold_sec
        self.high_vol_threshold = high_vol_threshold
        self.pause_vol_threshold = pause_vol_threshold
        
        # Store tuples of (timestamp, price)
        self.history = deque(maxlen=2000) 

    def update(self, current_price: float) -> bool:
        """
        Updates the price history and returns True if a pause is detected after a big move.
        """
        now = time.time()
        self.history.append((now, current_price))
        
        # Clean up old data (> 10 seconds)
        while self.history and now - self.history[0][0] > 10.0:
            self.history.popleft()
            
        if len(self.history) < 10:
            return False
            
        # Analyze the last 10 seconds
        pause_window = [p for t, p in self.history if now - t <= self.pause_threshold_sec]
        move_window = [p for t, p in self.history if now - t > self.pause_threshold_sec]
        
        if not pause_window or not move_window:
            return False
            
        pause_vol = max(pause_window) - min(pause_window)
        move_vol = max(move_window) - min(move_window)
        
        if move_vol >= self.high_vol_threshold and pause_vol <= self.pause_vol_threshold:
            logger.debug(f"Pause detected! move_vol={move_vol:.3f}, pause_vol={pause_vol:.3f}")
            return True
            
        return False
        
    def reset(self):
        """Clears the history, usually called after a grid is placed."""
        self.history.clear()
