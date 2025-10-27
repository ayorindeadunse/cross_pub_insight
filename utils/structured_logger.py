"""
Enhanced structured logging system for production monitoring and debugging.
"""
import json
import logging
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from uuid import uuid4

from utils.config_loader import load_config


class LogLevel(Enum):
    """Enhanced log levels for different types of events"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"  # For security and compliance events
    PERFORMANCE = "PERFORMANCE"  # For performance monitoring
    BUSINESS = "BUSINESS"  # For business logic events


class ComponentType(Enum):
    """System components for structured logging"""
    API = "api"
    ORCHESTRATOR = "orchestrator"
    AGENT = "agent"
    LLM = "llm"
    REPOSITORY = "repository"
    SECURITY = "security"
    RESILIENCE = "resilience"
    SYSTEM = "system"


@dataclass
class LogContext:
    """Structured context for log entries"""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    component: ComponentType = ComponentType.SYSTEM
    operation: str = ""
    repo_path: Optional[str] = None
    agent_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, Enum):
                    result[key] = value.value
                else:
                    result[key] = value
        return result


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    operation_start_time: float = field(default_factory=time.time)
    operation_end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    retry_count: int = 0
    cache_hit: bool = False
    tokens_used: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    
    def finish(self):
        """Mark operation as finished and calculate duration"""
        self.operation_end_time = time.time()
        self.duration_ms = (self.operation_end_time - self.operation_start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class StructuredLogger:
    """
    Enhanced structured logger for production monitoring.
    """
    
    def __init__(self, name: str = "cpia", context: Optional[LogContext] = None):
        self.name = name
        self.base_context = context or LogContext()
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup the underlying logger with enhanced formatting"""
        logger = logging.getLogger(self.name)
        
        if logger.hasHandlers():
            return logger
        
        # Load configuration
        config = load_config()
        logging_config = config.get("Logging", {})
        
        log_level = getattr(logging, logging_config.get("level", "INFO").upper(), logging.INFO)
        log_file = logging_config.get("log_file", "output/cpia.log")
        enable_structured = logging_config.get("structured", True)
        
        logger.setLevel(log_level)
        
        # Create formatters
        if enable_structured:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file_path = Path(log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Audit log handler (separate file for security events)
        audit_file = log_file_path.parent / "audit.log"
        audit_handler = logging.FileHandler(audit_file, encoding="utf-8")
        audit_handler.setFormatter(formatter)
        audit_handler.setLevel(logging.WARNING)  # Only warnings and above go to audit
        logger.addHandler(audit_handler)
        
        return logger
    
    def log(
        self, 
        level: Union[LogLevel, str], 
        message: str,
        context: Optional[LogContext] = None,
        metrics: Optional[PerformanceMetrics] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ):
        """
        Enhanced structured logging method.
        
        Args:
            level: Log level (LogLevel enum or string)
            message: Log message
            context: Additional context (merged with base context)
            metrics: Performance metrics
            extra_data: Additional structured data
            exception: Exception object if logging an error
        """
        # Determine log level
        if isinstance(level, LogLevel):
            log_level = getattr(logging, level.value)
        else:
            log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Build structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.value if isinstance(level, LogLevel) else level.upper(),
            "message": message,
            "logger": self.name
        }
        
        # Add context
        merged_context = LogContext(
            session_id=self.base_context.session_id,
            request_id=context.request_id if context else self.base_context.request_id,
            user_id=context.user_id if context else self.base_context.user_id,
            component=context.component if context else self.base_context.component,
            operation=context.operation if context else self.base_context.operation,
            repo_path=context.repo_path if context else self.base_context.repo_path,
            agent_name=context.agent_name if context else self.base_context.agent_name
        )
        log_entry["context"] = merged_context.to_dict()
        
        # Add performance metrics
        if metrics:
            log_entry["metrics"] = metrics.to_dict()
        
        # Add extra data
        if extra_data:
            log_entry["data"] = extra_data
        
        # Add exception information
        if exception:
            log_entry["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc()
            }
        
        # Store structured data in extra for custom formatter
        extra = {"structured_data": log_entry}
        
        self.logger.log(log_level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Debug level logging"""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Info level logging"""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning level logging"""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Error level logging"""
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical level logging"""
        self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def audit(self, message: str, **kwargs):
        """Audit level logging for security events"""
        self.log(LogLevel.AUDIT, message, **kwargs)
    
    def performance(self, message: str, **kwargs):
        """Performance level logging for monitoring"""
        self.log(LogLevel.PERFORMANCE, message, **kwargs)
    
    def business(self, message: str, **kwargs):
        """Business level logging for business logic events"""
        self.log(LogLevel.BUSINESS, message, **kwargs)
    
    @contextmanager
    def operation_context(
        self, 
        operation: str, 
        component: ComponentType,
        context: Optional[LogContext] = None
    ):
        """
        Context manager for tracking operations with automatic timing.
        
        Usage:
            with logger.operation_context("analyze_repository", ComponentType.AGENT):
                # Your operation code here
                pass
        """
        # Create operation context
        op_context = LogContext(
            session_id=self.base_context.session_id,
            request_id=context.request_id if context else self.base_context.request_id,
            component=component,
            operation=operation
        )
        
        # Create performance metrics
        metrics = PerformanceMetrics()
        
        # Log operation start
        self.info(
            f"Starting operation: {operation}",
            context=op_context,
            metrics=metrics
        )
        
        try:
            yield op_context, metrics
            
            # Log successful completion
            metrics.finish()
            self.info(
                f"Completed operation: {operation}",
                context=op_context,
                metrics=metrics,
                extra_data={"status": "success"}
            )
            
        except Exception as e:
            # Log failure
            metrics.finish()
            self.error(
                f"Failed operation: {operation}",
                context=op_context,
                metrics=metrics,
                extra_data={"status": "failed"},
                exception=e
            )
            raise
    
    def child_logger(self, context: LogContext) -> 'StructuredLogger':
        """Create a child logger with extended context"""
        merged_context = LogContext(
            session_id=context.session_id or self.base_context.session_id,
            request_id=context.request_id or self.base_context.request_id,
            user_id=context.user_id or self.base_context.user_id,
            component=context.component,
            operation=context.operation or self.base_context.operation,
            repo_path=context.repo_path or self.base_context.repo_path,
            agent_name=context.agent_name or self.base_context.agent_name
        )
        return StructuredLogger(self.name, merged_context)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs"""
    
    def format(self, record) -> str:
        # If structured data is present, format as JSON
        if hasattr(record, 'structured_data'):
            return json.dumps(record.structured_data, ensure_ascii=False, indent=None)
        
        # Otherwise, use default formatting
        return super().format(record)


# Global structured logger instance
structured_logger = StructuredLogger()


def get_structured_logger(name: str = "cpia", context: Optional[LogContext] = None) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name
        context: Base context for all log entries
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, context)


def get_logger(name: str = "cross_pub_insight") -> logging.Logger:
    """
    Legacy logger function for backward compatibility.
    """
    return structured_logger.logger


# Convenience function for creating operation-specific loggers
def get_operation_logger(
    operation: str, 
    component: ComponentType,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> StructuredLogger:
    """
    Create a logger with operation-specific context.
    
    Args:
        operation: Operation name (e.g., "analyze_repository")
        component: Component type (e.g., ComponentType.AGENT)
        session_id: Optional session ID
        request_id: Optional request ID
        
    Returns:
        StructuredLogger with operation context
    """
    context = LogContext(
        session_id=session_id or str(uuid4()),
        request_id=request_id,
        component=component,
        operation=operation
    )
    return StructuredLogger("cpia", context)