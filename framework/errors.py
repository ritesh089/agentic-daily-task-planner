"""
Centralized Error Handling

Provides a unified error hierarchy for all framework components,
with support for error recovery, retries, and detailed context.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class FrameworkError(Exception):
    """
    Base exception for all framework errors.
    
    Attributes:
        message: Human-readable error message
        recoverable: Whether the error can be recovered from
        retry_after: Seconds to wait before retrying (if recoverable)
        context: Additional context about the error
        error_code: Unique error code for categorization
        timestamp: When the error occurred
    """
    
    def __init__(
        self,
        message: str,
        recoverable: bool = False,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.context = context or {}
        self.error_code = error_code or self.__class__.__name__
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'recoverable': self.recoverable,
            'retry_after': self.retry_after,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}"
        if self.recoverable:
            base += f" (recoverable, retry after {self.retry_after}s)"
        if self.context:
            base += f"\nContext: {self.context}"
        return base


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(FrameworkError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            recoverable=False,  # Configuration errors are not recoverable
            error_code="CONFIG_ERROR",
            **kwargs
        )


class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file not found."""
    
    def __init__(self, path: str):
        super().__init__(
            f"Configuration file not found: {path}",
            context={'config_path': path},
            error_code="CONFIG_FILE_NOT_FOUND"
        )


class InvalidConfigurationError(ConfigurationError):
    """Configuration validation failed."""
    
    def __init__(self, issues: list[str]):
        super().__init__(
            f"Configuration validation failed: {'; '.join(issues)}",
            context={'validation_issues': issues},
            error_code="INVALID_CONFIG"
        )


# ============================================================================
# Checkpoint/Durability Errors
# ============================================================================

class CheckpointError(FrameworkError):
    """Checkpoint and durability-related errors."""
    pass


class CheckpointNotFoundError(CheckpointError):
    """Checkpoint not found in database."""
    
    def __init__(self, thread_id: str, checkpoint_id: Optional[str] = None):
        context = {'thread_id': thread_id}
        if checkpoint_id:
            context['checkpoint_id'] = checkpoint_id
        
        super().__init__(
            f"Checkpoint not found for thread: {thread_id}",
            recoverable=False,
            context=context,
            error_code="CHECKPOINT_NOT_FOUND"
        )


class CheckpointSaveError(CheckpointError):
    """Failed to save checkpoint."""
    
    def __init__(self, reason: str, thread_id: Optional[str] = None):
        super().__init__(
            f"Failed to save checkpoint: {reason}",
            recoverable=True,
            retry_after=5,
            context={'thread_id': thread_id, 'reason': reason},
            error_code="CHECKPOINT_SAVE_FAILED"
        )


class CheckpointLoadError(CheckpointError):
    """Failed to load checkpoint."""
    
    def __init__(self, reason: str, thread_id: Optional[str] = None):
        super().__init__(
            f"Failed to load checkpoint: {reason}",
            recoverable=True,
            retry_after=5,
            context={'thread_id': thread_id, 'reason': reason},
            error_code="CHECKPOINT_LOAD_FAILED"
        )


class DatabaseConnectionError(CheckpointError):
    """Database connection failed."""
    
    def __init__(self, db_url: str, reason: str):
        super().__init__(
            f"Database connection failed: {reason}",
            recoverable=True,
            retry_after=10,
            context={'db_url': db_url, 'reason': reason},
            error_code="DB_CONNECTION_FAILED"
        )


# ============================================================================
# Lock Management Errors
# ============================================================================

class LockError(FrameworkError):
    """Lock management errors."""
    pass


class LockAcquisitionError(LockError):
    """Failed to acquire lock."""
    
    def __init__(self, lock_id: int, timeout: int):
        super().__init__(
            f"Failed to acquire lock {lock_id} within {timeout}s",
            recoverable=True,
            retry_after=timeout,
            context={'lock_id': lock_id, 'timeout': timeout},
            error_code="LOCK_ACQUISITION_FAILED"
        )


class LockAlreadyHeldError(LockError):
    """Lock is already held by another process."""
    
    def __init__(self, lock_id: int, holder_info: Optional[str] = None):
        super().__init__(
            f"Lock {lock_id} is already held by another process",
            recoverable=True,
            retry_after=60,
            context={'lock_id': lock_id, 'holder': holder_info},
            error_code="LOCK_ALREADY_HELD"
        )


# ============================================================================
# Workflow Execution Errors
# ============================================================================

class WorkflowExecutionError(FrameworkError):
    """Workflow execution errors."""
    pass


class WorkflowAlreadyRunningError(WorkflowExecutionError):
    """Workflow is already running."""
    
    def __init__(self, thread_id: str):
        super().__init__(
            f"Workflow {thread_id} is already running",
            recoverable=False,
            context={'thread_id': thread_id},
            error_code="WORKFLOW_ALREADY_RUNNING"
        )


class WorkflowBuildError(WorkflowExecutionError):
    """Failed to build workflow."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Failed to build workflow: {reason}",
            recoverable=False,
            context={'reason': reason},
            error_code="WORKFLOW_BUILD_FAILED"
        )


class WorkflowCompilationError(WorkflowExecutionError):
    """Failed to compile workflow."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Failed to compile workflow: {reason}",
            recoverable=False,
            context={'reason': reason},
            error_code="WORKFLOW_COMPILATION_FAILED"
        )


class WorkflowTimeoutError(WorkflowExecutionError):
    """Workflow execution timed out."""
    
    def __init__(self, thread_id: str, timeout_seconds: int):
        super().__init__(
            f"Workflow {thread_id} timed out after {timeout_seconds}s",
            recoverable=False,
            context={'thread_id': thread_id, 'timeout': timeout_seconds},
            error_code="WORKFLOW_TIMEOUT"
        )


# ============================================================================
# Memory Management Errors
# ============================================================================

class MemoryError(FrameworkError):
    """Memory management errors."""
    pass


class MemoryBackendError(MemoryError):
    """Memory backend initialization or operation failed."""
    
    def __init__(self, backend: str, reason: str):
        super().__init__(
            f"Memory backend '{backend}' error: {reason}",
            recoverable=True,
            retry_after=5,
            context={'backend': backend, 'reason': reason},
            error_code="MEMORY_BACKEND_ERROR"
        )


class MemoryStorageError(MemoryError):
    """Failed to store memory."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Failed to store memory: {reason}",
            recoverable=True,
            retry_after=5,
            context={'reason': reason},
            error_code="MEMORY_STORAGE_FAILED"
        )


class MemoryRetrievalError(MemoryError):
    """Failed to retrieve memory."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Failed to retrieve memory: {reason}",
            recoverable=True,
            retry_after=5,
            context={'reason': reason},
            error_code="MEMORY_RETRIEVAL_FAILED"
        )


# ============================================================================
# MCP Errors
# ============================================================================

class MCPError(FrameworkError):
    """MCP (Model Context Protocol) errors."""
    pass


class MCPServerError(MCPError):
    """MCP server-related errors."""
    
    def __init__(self, server_name: str, reason: str):
        super().__init__(
            f"MCP server '{server_name}' error: {reason}",
            recoverable=True,
            retry_after=10,
            context={'server_name': server_name, 'reason': reason},
            error_code="MCP_SERVER_ERROR"
        )


class MCPServerStartupError(MCPError):
    """Failed to start MCP server."""
    
    def __init__(self, server_name: str, timeout: int):
        super().__init__(
            f"MCP server '{server_name}' failed to start within {timeout}s",
            recoverable=True,
            retry_after=timeout,
            context={'server_name': server_name, 'timeout': timeout},
            error_code="MCP_SERVER_STARTUP_FAILED"
        )


class MCPToolCallError(MCPError):
    """MCP tool call failed."""
    
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            f"MCP tool '{tool_name}' call failed: {reason}",
            recoverable=True,
            retry_after=5,
            context={'tool_name': tool_name, 'reason': reason},
            error_code="MCP_TOOL_CALL_FAILED"
        )


# ============================================================================
# Observability Errors
# ============================================================================

class ObservabilityError(FrameworkError):
    """Observability-related errors."""
    pass


class TracingError(ObservabilityError):
    """Tracing system error."""
    
    def __init__(self, system: str, reason: str):
        super().__init__(
            f"Tracing system '{system}' error: {reason}",
            recoverable=True,  # Observability errors should not break the app
            retry_after=5,
            context={'system': system, 'reason': reason},
            error_code="TRACING_ERROR"
        )


class MetricsError(ObservabilityError):
    """Metrics collection error."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Metrics collection error: {reason}",
            recoverable=True,
            retry_after=5,
            context={'reason': reason},
            error_code="METRICS_ERROR"
        )


# ============================================================================
# Lifecycle Errors
# ============================================================================

class LifecycleError(FrameworkError):
    """Framework lifecycle errors."""
    pass


class InitializationError(LifecycleError):
    """Framework initialization failed."""
    
    def __init__(self, component: str, reason: str):
        super().__init__(
            f"Failed to initialize {component}: {reason}",
            recoverable=False,
            context={'component': component, 'reason': reason},
            error_code="INITIALIZATION_FAILED"
        )


class ShutdownError(LifecycleError):
    """Framework shutdown error."""
    
    def __init__(self, component: str, reason: str):
        super().__init__(
            f"Failed to shutdown {component}: {reason}",
            recoverable=False,
            context={'component': component, 'reason': reason},
            error_code="SHUTDOWN_FAILED"
        )


# ============================================================================
# Helper Functions
# ============================================================================

def is_recoverable(error: Exception) -> bool:
    """Check if an error is recoverable."""
    if isinstance(error, FrameworkError):
        return error.recoverable
    return False


def get_retry_delay(error: Exception) -> Optional[int]:
    """Get retry delay for recoverable errors."""
    if isinstance(error, FrameworkError) and error.recoverable:
        return error.retry_after
    return None


def error_context(error: Exception) -> Dict[str, Any]:
    """Extract context from error."""
    if isinstance(error, FrameworkError):
        return error.context
    return {}

