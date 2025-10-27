"""
Production monitoring and health check system for CPIA.
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque

# Try to import psutil, but make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from utils.logger import get_logger

# Try to import structured logger if available
try:
    from utils.structured_logger import (
        get_structured_logger, LogContext, ComponentType, PerformanceMetrics
    )
    STRUCTURED_LOGGING_AVAILABLE = True
except ImportError:
    STRUCTURED_LOGGING_AVAILABLE = False


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


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
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "active_connections": self.active_connections,
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
    circuit_breaker_trips: int = 0
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
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        return 100.0 - self.success_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "operation_name": self.operation_name,
            "component": self.component,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "min_duration_ms": self.min_duration_ms if self.min_duration_ms != float('inf') else 0,
            "max_duration_ms": self.max_duration_ms,
            "retry_count": self.retry_count,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "last_called": self.last_called.isoformat() + "Z" if self.last_called else None
        }


class MonitoringSystem:
    """
    Comprehensive monitoring system for CPIA.
    """
    
    def __init__(self):
        # Use structured logger if available, otherwise fall back to basic logger
        if STRUCTURED_LOGGING_AVAILABLE:
            self.logger = get_structured_logger("monitoring")
            self.structured_logging = True
        else:
            self.logger = get_logger("monitoring")
            self.structured_logging = False
            
        self.health_checks: Dict[str, Callable] = {}
        self.operation_metrics: Dict[str, OperationMetrics] = defaultdict(
            lambda: OperationMetrics("", "")
        )
        self.recent_events = deque(maxlen=1000)  # Keep last 1000 events
        self.alerts = deque(maxlen=100)  # Keep last 100 alerts
        self.start_time = datetime.utcnow()
    
    def _log(self, level: str, message: str, **kwargs):
        """Helper method to handle both structured and basic logging"""
        if self.structured_logging:
            # Use structured logging with context
            getattr(self.logger, level.lower())(message, **kwargs)
        else:
            # Use basic logging
            getattr(self.logger, level.lower())(message)
        
        # Register default health checks
        self._register_default_health_checks()
    
    def _register_default_health_checks(self):
        """Register default system health checks"""
        self.register_health_check("system_resources", self._check_system_resources)
        self.register_health_check("disk_space", self._check_disk_space)
        self.register_health_check("memory_usage", self._check_memory_usage)
    
    def register_health_check(self, name: str, check_func: Callable):
        """
        Register a health check function.
        
        Args:
            name: Health check name
            check_func: Async function that returns HealthCheckResult
        """
        self.health_checks[name] = check_func
        if self.structured_logging:
            self.logger.info(
                f"Registered health check: {name}",
                context=LogContext(component=ComponentType.SYSTEM, operation="register_health_check")
            )
        else:
            self.logger.info(f"Registered health check: {name}")
    
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check overall system resource usage"""
        start_time = time.time()
        
        try:
            if not PSUTIL_AVAILABLE:
                # Fallback when psutil is not available
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    component="system_resources",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details={
                        "note": "psutil not available - basic monitoring only",
                        "psutil_available": False
                    }
                )
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine health status based on resource usage
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="system_resources",
                status=status,
                response_time_ms=response_time,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "available_memory_gb": memory.available / (1024**3),
                    "psutil_available": True
                }
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="system_resources",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space availability"""
        start_time = time.time()
        
        try:
            if not PSUTIL_AVAILABLE:
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    component="disk_space",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details={"note": "psutil not available - disk monitoring disabled"}
                )
            
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            
            if free_gb < 1:  # Less than 1GB free
                status = HealthStatus.UNHEALTHY
            elif free_gb < 5:  # Less than 5GB free
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="disk_space",
                status=status,
                response_time_ms=response_time,
                details={
                    "free_gb": free_gb,
                    "used_percent": disk.percent,
                    "total_gb": disk.total / (1024**3)
                }
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="disk_space",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check memory usage patterns"""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Check for memory pressure
            if memory.percent > 95 or swap.percent > 50:
                status = HealthStatus.UNHEALTHY
            elif memory.percent > 80 or swap.percent > 20:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="memory_usage",
                status=status,
                response_time_ms=response_time,
                details={
                    "memory_percent": memory.percent,
                    "swap_percent": swap.percent,
                    "available_gb": memory.available / (1024**3),
                    "cached_gb": memory.cached / (1024**3)
                }
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="memory_usage",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def run_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                result = await check_func()
                results[name] = result
                
                # Log health check result
                self.logger.debug(
                    f"Health check completed: {name}",
                    context=LogContext(
                        component=ComponentType.SYSTEM,
                        operation="health_check"
                    ),
                    extra_data={
                        "health_check": name,
                        "status": result.status.value,
                        "response_time_ms": result.response_time_ms
                    }
                )
                
                # Generate alerts for unhealthy components
                if result.status == HealthStatus.UNHEALTHY:
                    await self._generate_alert(
                        AlertLevel.CRITICAL,
                        f"Health check failed: {name}",
                        {"health_check_result": result.to_dict()}
                    )
                elif result.status == HealthStatus.DEGRADED:
                    await self._generate_alert(
                        AlertLevel.WARNING,
                        f"Health check degraded: {name}",
                        {"health_check_result": result.to_dict()}
                    )
                
            except Exception as e:
                # Health check itself failed
                error_result = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    error=str(e)
                )
                results[name] = error_result
                
                self.logger.error(
                    f"Health check error: {name}",
                    context=LogContext(
                        component=ComponentType.SYSTEM,
                        operation="health_check"
                    ),
                    exception=e
                )
        
        return results
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Count active network connections (simplified)
            connections = len(psutil.net_connections())
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                active_connections=connections
            )
            
            self.logger.debug(
                "System metrics collected",
                context=LogContext(
                    component=ComponentType.SYSTEM,
                    operation="collect_metrics"
                ),
                extra_data=metrics.to_dict()
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(
                "Failed to collect system metrics",
                context=LogContext(
                    component=ComponentType.SYSTEM,
                    operation="collect_metrics"
                ),
                exception=e
            )
            # Return default metrics
            return SystemMetrics(0, 0, 0, 0)
    
    def record_operation_metrics(
        self,
        operation_name: str,
        component: str,
        duration_ms: float,
        success: bool,
        retries: int = 0
    ):
        """Record metrics for an operation"""
        key = f"{component}.{operation_name}"
        
        # Initialize if not exists
        if key not in self.operation_metrics:
            self.operation_metrics[key] = OperationMetrics(operation_name, component)
        
        # Add the call
        self.operation_metrics[key].add_call(duration_ms, success, retries)
        
        # Log performance metrics
        self.logger.performance(
            f"Operation metrics recorded: {operation_name}",
            context=LogContext(
                component=ComponentType.SYSTEM,
                operation="record_metrics"
            ),
            extra_data={
                "operation": operation_name,
                "component": component,
                "duration_ms": duration_ms,
                "success": success,
                "retries": retries,
                "success_rate": self.operation_metrics[key].success_rate
            }
        )
    
    async def _generate_alert(
        self,
        level: AlertLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Generate and store an alert"""
        alert = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.value,
            "message": message,
            "details": details or {}
        }
        
        self.alerts.append(alert)
        
        # Log the alert
        if level == AlertLevel.CRITICAL:
            self.logger.critical(message, extra_data=details)
        elif level == AlertLevel.WARNING:
            self.logger.warning(message, extra_data=details)
        else:
            self.logger.info(message, extra_data=details)
    
    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary"""
        # Run health checks
        health_results = await self.run_health_checks()
        
        # Get system metrics
        system_metrics = await self.get_system_metrics()
        
        # Calculate overall health
        overall_status = HealthStatus.HEALTHY
        for result in health_results.values():
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        # Get operation metrics summary
        operation_summary = {}
        for key, metrics in self.operation_metrics.items():
            operation_summary[key] = metrics.to_dict()
        
        # System uptime
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        summary = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_status": overall_status.value,
            "uptime_seconds": uptime_seconds,
            "health_checks": {name: result.to_dict() for name, result in health_results.items()},
            "system_metrics": system_metrics.to_dict(),
            "operation_metrics": operation_summary,
            "recent_alerts": list(self.alerts)[-10:],  # Last 10 alerts
            "total_operations": sum(m.total_calls for m in self.operation_metrics.values()),
            "average_success_rate": (
                sum(m.success_rate for m in self.operation_metrics.values()) / 
                len(self.operation_metrics) if self.operation_metrics else 100.0
            )
        }
        
        return summary
    
    def get_operation_metrics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get operation metrics, optionally filtered by operation name"""
        if operation_name:
            filtered_metrics = {
                k: v.to_dict() for k, v in self.operation_metrics.items()
                if operation_name in k
            }
        else:
            filtered_metrics = {k: v.to_dict() for k, v in self.operation_metrics.items()}
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": filtered_metrics
        }


# Global monitoring system instance
monitoring_system = MonitoringSystem()


def get_monitoring_system() -> MonitoringSystem:
    """Get the global monitoring system instance"""
    return monitoring_system