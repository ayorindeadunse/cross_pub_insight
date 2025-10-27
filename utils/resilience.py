"""
Resilience utilities for the CPIA API.
Includes retry logic with exponential backoff, circuit breakers, and timeout handling.
"""
import asyncio
import time
import random
from typing import Callable, Any, Optional, Dict, List
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: tuple = (Exception,)
    timeout: Optional[float] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: tuple = (Exception,)
    name: str = "default"


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class TimeoutError(Exception):
    """Exception raised when operation times out"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"Circuit breaker {self.config.name} switching to HALF_OPEN")
                else:
                    logger.warning(f"Circuit breaker {self.config.name} is OPEN, blocking request")
                    raise CircuitBreakerError(f"Circuit breaker {self.config.name} is open")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type is None:
                # Success
                self._on_success()
            elif isinstance(exc_val, self.config.expected_exception):
                # Expected failure
                self._on_failure()
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            logger.info(f"Circuit breaker {self.config.name} reset to CLOSED")
        self.failure_count = 0
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker {self.config.name} tripped OPEN after {self.failure_count} failures")


class ResilienceManager:
    """
    Central manager for resilience patterns including retry logic and circuit breakers.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Get or create a circuit breaker by name"""
        if name not in self.circuit_breakers:
            config.name = name
            self.circuit_breakers[name] = CircuitBreaker(config)
        return self.circuit_breakers[name]
    
    async def execute_with_retry(
        self,
        func: Callable,
        retry_config: RetryConfig,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic and optional circuit breaker.
        """
        circuit_breaker = None
        if circuit_breaker_config:
            circuit_breaker = self.get_circuit_breaker(
                circuit_breaker_config.name, 
                circuit_breaker_config
            )
        
        for attempt in range(retry_config.max_attempts):
            try:
                if circuit_breaker:
                    async with circuit_breaker:
                        return await self._execute_with_timeout(func, retry_config.timeout, *args, **kwargs)
                else:
                    return await self._execute_with_timeout(func, retry_config.timeout, *args, **kwargs)
            
            except retry_config.retryable_exceptions as e:
                if attempt == retry_config.max_attempts - 1:
                    logger.error(f"Function {func.__name__} failed after {retry_config.max_attempts} attempts: {str(e)}")
                    raise
                
                delay = self._calculate_delay(attempt, retry_config)
                logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{retry_config.max_attempts}), retrying in {delay:.2f}s: {str(e)}")
                await asyncio.sleep(delay)
            
            except Exception as e:
                # Non-retryable exception
                logger.error(f"Function {func.__name__} failed with non-retryable exception: {str(e)}")
                raise
    
    async def _execute_with_timeout(self, func: Callable, timeout: Optional[float], *args, **kwargs) -> Any:
        """Execute function with optional timeout"""
        if timeout is None:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        try:
            if asyncio.iscoroutinefunction(func):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            else:
                # For sync functions, run in executor with timeout
                loop = asyncio.get_event_loop()
                future = loop.run_in_executor(None, lambda: func(*args, **kwargs))
                return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s")
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt"""
        if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.exponential_base ** attempt)
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * (attempt + 1)
        else:  # FIXED_DELAY
            delay = config.base_delay
        
        # Apply maximum delay
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


# Global resilience manager instance
resilience_manager = ResilienceManager()


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    retryable_exceptions: tuple = (Exception,),
    timeout: Optional[float] = None,
    circuit_breaker_name: Optional[str] = None,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: float = 60.0
):
    """
    Decorator for adding retry logic and circuit breaker to functions.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retry_config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                strategy=strategy,
                retryable_exceptions=retryable_exceptions,
                timeout=timeout
            )
            
            circuit_breaker_config = None
            if circuit_breaker_name:
                circuit_breaker_config = CircuitBreakerConfig(
                    failure_threshold=circuit_breaker_threshold,
                    recovery_timeout=circuit_breaker_timeout,
                    expected_exception=retryable_exceptions,
                    name=circuit_breaker_name
                )
            
            return await resilience_manager.execute_with_retry(
                func, retry_config, circuit_breaker_config, *args, **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in an async context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Predefined configurations for common scenarios
class RetryConfigs:
    """Predefined retry configurations for common scenarios"""
    
    LLM_CALLS = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=(ConnectionError, TimeoutError, Exception),
        timeout=60.0
    )
    
    REPOSITORY_CLONING = RetryConfig(
        max_attempts=2,
        base_delay=2.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=120.0
    )
    
    AGENT_COMMUNICATION = RetryConfig(
        max_attempts=2,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=30.0
    )


class CircuitBreakerConfigs:
    """Predefined circuit breaker configurations"""
    
    LLM_SERVICE = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        expected_exception=(ConnectionError, TimeoutError, Exception),
        name="llm_service"
    )
    
    REPOSITORY_SERVICE = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        expected_exception=(ConnectionError, TimeoutError),
        name="repository_service"
    )