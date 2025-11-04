"""
Framework Module
Provides cross-cutting concerns like OpenTelemetry instrumentation and durable executions
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
    'get_durability_manager'
]

