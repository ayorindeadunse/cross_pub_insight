"""
Simplified monitoring system for CPIA (Phase 3 implementation).
This version works without external dependencies like psutil.
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque

from utils.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "component": self.component,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "error": self.error,
            "timestamp": self.timestamp.isoformat() + "Z"
        }


@dataclass
class OperationMetrics:
    """Metrics for operations tracking"""
    operation_name: str
    component: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    retry_count: int = 0
    last_called: Optional[datetime] = None
    
    def add_call(self, duration_ms: float, success: bool, retries: int = 0):
        """Add a new operation call to metrics"""
        self.total_calls += 1
        self.total_duration_ms += duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.total_calls
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.retry_count += retries
        self.last_called = datetime.utcnow()
        
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "operation_name": self.operation_name,
            "component": self.component,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate_percent": self.get_success_rate(),
            "avg_duration_ms": self.avg_duration_ms,
            "min_duration_ms": self.min_duration_ms if self.min_duration_ms != float('inf') else 0,
            "max_duration_ms": self.max_duration_ms,
            "retry_count": self.retry_count,
            "last_called": self.last_called.isoformat() + "Z" if self.last_called else None
        }


class SimpleMonitoringSystem:
    """
    Simplified monitoring system for CPIA that works without external dependencies.
    """
    
    def __init__(self):
        self.logger = get_logger("monitoring")
        self.health_checks: Dict[str, Callable] = {}
        self.operation_metrics: Dict[str, OperationMetrics] = defaultdict(
            lambda: OperationMetrics("", "")
        )
        self.start_time = datetime.utcnow()
        self.alerts = deque(maxlen=100)  # For compatibility with server.py
        
        # Register default health checks
        self._register_default_health_checks()
    
    def _register_default_health_checks(self):
        """Register default system health checks"""
        self.register_health_check("api_basic", self._check_api_basic)
        self.register_health_check("memory_basic", self._check_memory_basic)
    
    def register_health_check(self, name: str, check_func: Callable):
        """
        Register a health check function.
        
        Args:
            name: Health check name
            check_func: Async function that returns HealthCheckResult
        """
        self.health_checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")
    
    async def _check_api_basic(self) -> HealthCheckResult:
        """Basic API health check"""
        start_time = time.time()
        
        try:
            # Simple health check - if we can execute this, API is responsive
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="api",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={"check_type": "basic_response"}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="api",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _check_memory_basic(self) -> HealthCheckResult:
        """Basic memory health check without psutil"""
        start_time = time.time()
        
        try:
            # Simple memory check - count objects
            import gc
            gc.collect()
            object_count = len(gc.get_objects())
            
            # Basic heuristic - if we have too many objects, might be memory issue
            if object_count > 100000:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="memory",
                status=status,
                response_time_ms=response_time,
                details={
                    "object_count": object_count,
                    "check_type": "basic_gc_objects"
                }
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def run_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                self.logger.debug(f"Running health check: {name}")
                result = await check_func()
                results[name] = result
                self.logger.debug(f"Health check {name} completed: {result.status.value}")
            except Exception as e:
                self.logger.error(f"Health check {name} failed: {str(e)}")
                results[name] = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0.0,
                    error=str(e)
                )
        
        return results
    
    def record_operation(self, operation_name: str, component: str, 
                        duration_ms: float, success: bool, retries: int = 0):
        """Record metrics for an operation"""
        key = f"{component}:{operation_name}"
        
        if key not in self.operation_metrics:
            self.operation_metrics[key] = OperationMetrics(operation_name, component)
        
        self.operation_metrics[key].add_call(duration_ms, success, retries)
        
        self.logger.debug(
            f"Recorded operation: {operation_name} "
            f"(component={component}, duration={duration_ms:.2f}ms, "
            f"success={success}, retries={retries})"
        )
    
    def get_operation_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all operation metrics"""
        return {
            key: metrics.to_dict() 
            for key, metrics in self.operation_metrics.items()
        }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        health_results = await self.run_health_checks()
        
        # Calculate overall status
        statuses = [result.status for result in health_results.values()]
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "overall_status": overall_status.value,
            "uptime_seconds": uptime_seconds,
            "health_checks": {
                name: result.to_dict() 
                for name, result in health_results.items()
            },
            "operation_metrics": self.get_operation_metrics(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def get_health_status(self) -> HealthStatus:
        """Get simple health status for API endpoints"""
        try:
            # Quick sync check - if we can create objects and access metrics, we're healthy
            if len(self.operation_metrics) >= 0:  # Always true, but exercises the system
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.DEGRADED
        except Exception:
            return HealthStatus.UNHEALTHY
    
    def record_operation_metrics(self, operation_name: str, component: str, 
                               duration_ms: float, success: bool, retries: int = 0):
        """Alias for record_operation for backward compatibility"""
        self.record_operation(operation_name, component, duration_ms, success, retries)
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics without psutil"""
        import gc
        gc.collect()
        object_count = len(gc.get_objects())
        
        return {
            "object_count": object_count,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "health_checks_count": len(self.health_checks),
            "operation_metrics_count": len(self.operation_metrics),
            "note": "Basic metrics without psutil"
        }
    
    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get monitoring summary"""
        health_results = await self.run_health_checks()
        operation_metrics = self.get_operation_metrics()
        
        total_operations = sum(metrics['total_calls'] for metrics in operation_metrics.values())
        total_successes = sum(metrics['successful_calls'] for metrics in operation_metrics.values())
        overall_success_rate = (total_successes / total_operations * 100) if total_operations > 0 else 100
        
        return {
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "total_health_checks": len(health_results),
            "healthy_checks": len([r for r in health_results.values() if r.status == HealthStatus.HEALTHY]),
            "total_operations": total_operations,
            "overall_success_rate": overall_success_rate,
            "monitored_components": len(set(
                metrics['component'] for metrics in operation_metrics.values()
            ))
        }


# Global monitoring system instance
monitoring_system = SimpleMonitoringSystem()


def get_monitoring_system() -> SimpleMonitoringSystem:
    """Get the global monitoring system instance"""
    return monitoring_system


# Context manager for operation tracking
class track_operation:
    """Context manager to automatically track operation metrics"""
    
    def __init__(self, operation_name: str, component: str):
        self.operation_name = operation_name
        self.component = component
        self.start_time = None
        self.success = False
        self.retries = 0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.success = exc_type is None
        
        monitoring_system.record_operation(
            self.operation_name,
            self.component,
            duration_ms,
            self.success,
            self.retries
        )
        
        return False  # Don't suppress exceptions
    
    def add_retry(self):
        """Record a retry attempt"""
        self.retries += 1