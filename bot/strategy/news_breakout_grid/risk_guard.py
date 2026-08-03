import time
import logging

logger = logging.getLogger(__name__)

class GridRiskGuard:
    def __init__(self, max_daily_loss_pct: float, max_attempts_per_day: int, initial_balance: float):
        """
        Guards against excessive losses for the aggressive grid strategy.
        :param max_daily_loss_pct: Max allowed loss percentage (e.g., 0.40 for 40%).
        :param max_attempts_per_day: Max number of grid placement cycles per day.
        :param initial_balance: The account balance to calculate the max loss amount.
        """
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_attempts_per_day = max_attempts_per_day
        self.initial_balance = initial_balance
        
        self.daily_loss = 0.0
        self.attempts_today = 0
        self.last_reset_day = time.localtime().tm_yday
        self.is_stopped = False
        
    def _check_reset(self):
        """Resets counters on a new day."""
        current_day = time.localtime().tm_yday
        if current_day != self.last_reset_day:
            self.daily_loss = 0.0
            self.attempts_today = 0
            self.last_reset_day = current_day
            self.is_stopped = False
            logger.info("GridRiskGuard: Daily limits reset.")

    def can_trade(self) -> bool:
        """Returns True if trading is currently allowed based on risk rules."""
        self._check_reset()
        if self.is_stopped:
            return False
            
        if self.attempts_today >= self.max_attempts_per_day:
            logger.warning(f"GridRiskGuard: Max daily attempts reached ({self.max_attempts_per_day}). Strategy stopped.")
            self.is_stopped = True
            return False
            
        max_allowed_loss = self.initial_balance * self.max_daily_loss_pct
        if self.daily_loss >= max_allowed_loss:
            logger.error(
                f"GridRiskGuard: MAX DAILY LOSS REACHED! "
                f"Loss: {self.daily_loss:.2f}, Allowed: {max_allowed_loss:.2f}. "
                f"Strategy stopped for the day."
            )
            self.is_stopped = True
            return False
            
        return True

    def record_attempt(self):
        """Call this when a new grid is placed."""
        self.attempts_today += 1
        
    def record_pnl(self, pnl: float):
        """Records closed profit/loss of a grid cycle."""
        if pnl < 0:
            self.daily_loss += abs(pnl)
        else:
            self.daily_loss -= pnl
            if self.daily_loss < 0:
                self.daily_loss = 0.0
                
        logger.info(f"GridRiskGuard: Cycle PnL = {pnl:.2f}. Accumulated Daily Loss = {self.daily_loss:.2f}")
