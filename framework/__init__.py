"""
Framework Module
Provides cross-cutting concerns like OpenTelemetry instrumentation, durable executions, 
MCP integration, and conversation memory management
"""

# Configuration
from framework.config import (
    FrameworkConfig,
    ObservabilityConfig,
    DurabilityConfig,
    MemoryConfig,
    MCPConfig,
    DevelopmentConfig,
    get_config,
    set_config,
    reset_config
)

# Errors
from framework.errors import (
    FrameworkError,
    ConfigurationError,
    CheckpointError,
    LockError,
    WorkflowExecutionError as WorkflowExecutionErrorNew,
    MemoryError,
    MCPError,
    ObservabilityError,
    LifecycleError,
    is_recoverable,
    get_retry_delay,
    error_context
)

# Resilience
from framework.resilience import (
    RetryConfig,
    with_retry,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerManager,
    resilient
)

# Lifecycle
from framework.lifecycle import (
    FrameworkContext,
    SyncFrameworkContext
)

# Health
from framework.health import (
    FrameworkHealth,
    HealthCheckResult,
    print_health_report
)

from framework.observability import (
    init_observability,
    ObservableStateGraph,
    create_workflow_span,
    instrument_agent,
    get_metrics,
    log_event,
    log_state_transition
)

from framework.durability import (
    CheckpointerManager,
    create_checkpointer,
    WorkflowCheckpoint,
    get_checkpoint_status,
    find_failed_workflows,
    resume_workflow,
    needs_resume
)

from framework.lock_manager import (
    PostgresLockManager,
    create_lock_manager_with_retry
)

from framework.workflow_executor import (
    WorkflowExecutor,
    with_workflow_lock,
    LockableWorkflowMixin,
    WorkflowExecutionError,
    WorkflowAlreadyRunningError
)

from framework.mcp_client import (
    init_mcp_client,
    shutdown_mcp_client,
    get_mcp_manager,
    run_async_tool_call,
    MCPClient,
    MCPManager,
    MCPServerConfig
)

from framework.memory import (
    add_messages,
    create_memory_aware_reducer,
    to_langchain_messages,
    ConversationMemoryMixin,
    MemoryManager,
    MemoryProfile,
    MemoryInspector,
    MemoryConfig,
    with_conversation_memory,
    requires_conversation_memory
)

from framework.interactive import (
    InteractiveCommandHandler,
    interactive_command
)

from framework.cli import (
    FrameworkCLI,
    run_framework_app
)

from framework.workflow_runner import (
    WorkflowRunner,
    run_workflow_with_durability
)

__all__ = [
    # Configuration
    'FrameworkConfig',
    'ObservabilityConfig',
    'DurabilityConfig',
    'MemoryConfig',
    'MCPConfig',
    'DevelopmentConfig',
    'get_config',
    'set_config',
    'reset_config',
    # Errors
    'FrameworkError',
    'ConfigurationError',
    'CheckpointError',
    'LockError',
    'WorkflowExecutionErrorNew',
    'MemoryError',
    'MCPError',
    'ObservabilityError',
    'LifecycleError',
    'is_recoverable',
    'get_retry_delay',
    'error_context',
    # Resilience
    'RetryConfig',
    'with_retry',
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitBreakerManager',
    'resilient',
    # Lifecycle
    'FrameworkContext',
    'SyncFrameworkContext',
    # Health
    'FrameworkHealth',
    'HealthCheckResult',
    'print_health_report',
    # Observability
    'init_observability',
    'ObservableStateGraph',
    'create_workflow_span',
    'instrument_agent',
    'get_metrics',
    'log_event',
    'log_state_transition',
    # Durability & Checkpointing
    'CheckpointerManager',
    'create_checkpointer',
    'WorkflowCheckpoint',
    'get_checkpoint_status',
    'find_failed_workflows',
    'resume_workflow',
    'needs_resume',
    # Lock Management
    'PostgresLockManager',
    'create_lock_manager_with_retry',
    # Workflow Execution
    'WorkflowExecutor',
    'with_workflow_lock',
    'LockableWorkflowMixin',
    'WorkflowExecutionError',
    'WorkflowAlreadyRunningError',
    # MCP Integration
    'init_mcp_client',
    'shutdown_mcp_client',
    'get_mcp_manager',
    'run_async_tool_call',
    'MCPClient',
    'MCPManager',
    'MCPServerConfig',
    # Memory Management
    'add_messages',
    'create_memory_aware_reducer',
    'to_langchain_messages',
    'ConversationMemoryMixin',
    'MemoryManager',
    'MemoryProfile',
    'MemoryInspector',
    'MemoryConfig',
    'with_conversation_memory',
    'requires_conversation_memory',
    # Interactive Commands
    'InteractiveCommandHandler',
    'interactive_command',
    # CLI
    'FrameworkCLI',
    'run_framework_app',
    # Workflow Runner
    'WorkflowRunner',
    'run_workflow_with_durability',
]

