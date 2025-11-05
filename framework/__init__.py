"""
Framework Module
Provides cross-cutting concerns like OpenTelemetry instrumentation, durable executions, and MCP integration
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
]

