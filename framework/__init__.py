"""
Framework Module
Provides cross-cutting concerns like OpenTelemetry instrumentation, durable executions, 
MCP integration, and conversation memory management
"""

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
    init_durability,
    get_durability_manager
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

__all__ = [
    # Observability
    'init_observability',
    'ObservableStateGraph',
    'create_workflow_span',
    'instrument_agent',
    'get_metrics',
    'log_event',
    'log_state_transition',
    # Durability
    'init_durability',
    'get_durability_manager',
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
]

