import time
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    """Raised when the circuit breaker is open (tripped)."""
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        self._check_state()

        if self.state == "OPEN":
            raise CircuitBreakerOpenException("Circuit breaker is currently OPEN.")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            if isinstance(e, CircuitBreakerOpenException):
                raise
            self._on_failure()
            raise

    def _check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("CircuitBreaker transitioned to HALF_OPEN state")

    def _on_success(self):
        if self.state == "HALF_OPEN" or self.failure_count > 0:
            logger.info("CircuitBreaker reset to CLOSED state after success")
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"CircuitBreaker OPENED after {self.failure_count} consecutive failures")

def with_exponential_backoff(func: Callable, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, exceptions=(Exception,)) -> Any:
    """Retries a function with exponential backoff."""
    retries = 0
    while True:
        try:
            return func()
        except exceptions as e:
            retries += 1
            if retries > max_retries:
                raise
            
            delay = min(base_delay * (2 ** (retries - 1)), max_delay)
            logger.warning(f"Request failed, retrying in {delay}s (Attempt {retries}/{max_retries}): {e}")
            time.sleep(delay)
