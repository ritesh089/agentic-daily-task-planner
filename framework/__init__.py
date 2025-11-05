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
    ConversationMemoryMixin,
    MemoryManager,
    with_conversation_memory,
    requires_conversation_memory
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
    'ConversationMemoryMixin',
    'MemoryManager',
    'with_conversation_memory',
    'requires_conversation_memory',
]

