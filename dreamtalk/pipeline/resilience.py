"""
DreamTalk — Resilience Utilities

Provides:
- Retry with exponential backoff
- Circuit breaker pattern
- Graceful degradation wrappers
- Timeout management
"""

import time
import logging
import functools
from typing import Optional, Callable, Any, Dict
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("dreamtalk.pipeline.resilience")


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject calls
    HALF_OPEN = "half_open" # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    half_open_max_calls: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    half_open_calls: int = 0

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker: CLOSED (recovered)")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker: OPEN (half-open test failed)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker: OPEN (failures: {self.failure_count})")

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.success_count = 0
                logger.info("Circuit breaker: HALF_OPEN (testing recovery)")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        return False

    def to_dict(self) -> Dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
        }


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
    exceptions: tuple = (Exception,),
):
    """Decorator: retry with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    delay = base_delay * (2 ** attempt if exponential else 1)
                    delay = min(delay, max_delay)
                    logger.warning(f"Retry {attempt+1}/{max_retries} for {func.__name__}: {e} (delay={delay:.1f}s)")
                    import asyncio
                    await asyncio.sleep(delay)
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    delay = base_delay * (2 ** attempt if exponential else 1)
                    delay = min(delay, max_delay)
                    logger.warning(f"Retry {attempt+1}/{max_retries} for {func.__name__}: {e} (delay={delay:.1f}s)")
                    time.sleep(delay)
            raise last_exception

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


async def with_fallback(
    primary_fn: Callable,
    fallback_fn: Callable,
    error_message: str = "Primary failed, using fallback",
) -> Any:
    """Execute primary function with fallback on failure."""
    try:
        return await primary_fn()
    except Exception as e:
        logger.warning(f"{error_message}: {e}")
        return await fallback_fn()


class GracefulPipeline:
    """Pipeline wrapper that continues even if individual steps fail."""

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._step_results: Dict[str, Any] = {}

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker()
        return self._circuit_breakers[name]

    async def run_step(
        self,
        name: str,
        fn: Callable,
        fallback: Optional[Callable] = None,
        critical: bool = False,
    ) -> Optional[Any]:
        """Run a pipeline step with error handling."""
        cb = self.get_circuit_breaker(name)

        if not cb.can_execute():
            logger.warning(f"Circuit open for '{name}', using fallback")
            if fallback:
                try:
                    result = await fallback()
                    return result
                except Exception as e:
                    logger.error(f"Fallback also failed for '{name}': {e}")
            if critical:
                raise RuntimeError(f"Critical step '{name}' circuit is open")
            return None

        try:
            result = await fn()
            cb.record_success()
            self._step_results[name] = {"status": "success", "result": result}
            return result
        except Exception as e:
            cb.record_failure()
            logger.error(f"Step '{name}' failed: {e}")
            self._step_results[name] = {"status": "failed", "error": str(e)}

            if fallback:
                try:
                    result = await fallback()
                    self._step_results[name]["fallback_used"] = True
                    return result
                except Exception as fb_e:
                    logger.error(f"Fallback also failed for '{name}': {fb_e}")

            if critical:
                raise
            return None

    def get_status(self) -> Dict:
        return {
            "circuit_breakers": {name: cb.to_dict() for name, cb in self._circuit_breakers.items()},
            "step_results": self._step_results,
        }
