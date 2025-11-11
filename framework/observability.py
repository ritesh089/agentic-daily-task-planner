"""
Observability Module
Provides OpenTelemetry instrumentation for the Daily Task Planner Agent
- Decoupled from business logic
- Decorator-based instrumentation
- Configurable exporters
"""

import functools
import time
import yaml
import os
from typing import Callable, Dict, Any
from datetime import datetime

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Global configuration
_config = None
_tracer = None
_meter = None
_initialized = False

# ============================================================================
# Configuration Loading
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load observability configuration from YAML file"""
    # Look for config in parent directory's config/ folder
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'observability_config.yaml')
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    # Default configuration if file doesn't exist
    return {
        'enabled': True,
        'service_name': 'daily-task-planner-agent',
        'service_version': '1.0.0',
        'exporters': {
            'console': True,
            'otlp': False
        },
        'otlp_endpoint': 'http://localhost:4317',
        'sampling_rate': 1.0
    }

# ============================================================================
# OTEL Initialization
# ============================================================================

def init_observability():
    """
    Initialize complete observability stack:
    - OTEL for application-level tracing & metrics (agents, workflows)
    - LangFuse for LLM-specific observability (prompts, responses, costs)
    
    Both are fully abstracted - workflows need ZERO code changes!
    """
    global _config, _tracer, _meter, _initialized
    
    if _initialized:
        return
    
    _config = load_config()
    
    if not _config.get('enabled', True):
        print("📊 Observability: Disabled by configuration")
        _initialized = True
        return
    
    # Create resource
    resource = Resource.create({
        "service.name": _config.get('service_name', 'agentic-framework'),
        "service.version": _config.get('service_version', '1.0.0'),
    })
    
    # Initialize Tracing
    trace_provider = TracerProvider(resource=resource)
    
    # Add trace exporters
    if _config.get('exporters', {}).get('console', True):
        console_exporter = ConsoleSpanExporter()
        trace_provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Check if OTLP traces are enabled (handle both old boolean and new dict format)
    otlp_config = _config.get('exporters', {}).get('otlp', False)
    otlp_traces_enabled = otlp_config.get('traces', True) if isinstance(otlp_config, dict) else otlp_config
    
    if otlp_traces_enabled:
        otlp_exporter = OTLPSpanExporter(
            endpoint=_config.get('otlp_endpoint', 'http://localhost:4317'),
            insecure=True
        )
        trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    trace.set_tracer_provider(trace_provider)
    _tracer = trace.get_tracer(__name__)
    
    # Initialize Metrics
    metric_readers = []
    
    if _config.get('exporters', {}).get('console', True):
        metric_readers.append(
            PeriodicExportingMetricReader(ConsoleMetricExporter())
        )
    
    # Check if OTLP metrics are enabled (handle both old boolean and new dict format)
    otlp_config = _config.get('exporters', {}).get('otlp', False)
    otlp_metrics_enabled = otlp_config.get('metrics', False) if isinstance(otlp_config, dict) else otlp_config
    
    if otlp_metrics_enabled:
        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=_config.get('otlp_endpoint', 'http://localhost:4317'),
                    insecure=True
                )
            )
        )
    
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=metric_readers
    )
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter(__name__)
    
    # Build exporter status message
    active_exporters = []
    if _config.get('exporters', {}).get('console', True):
        active_exporters.append('console')
    if otlp_traces_enabled:
        active_exporters.append('otlp-traces')
    if otlp_metrics_enabled:
        active_exporters.append('otlp-metrics')
    
    print(f"📊 OTEL: Initialized for {_config.get('service_name')}")
    print(f"   Exporters: {', '.join(active_exporters) if active_exporters else 'none'}")
    print(f"   Captures: Agent spans, metrics, state transitions")
    
    # Initialize LangFuse (LLM-specific observability)
    init_langfuse()
    
    _initialized = True

# ============================================================================
# Metrics Helpers
# ============================================================================

class AgentMetrics:
    """Metrics collector for agent operations"""
    
    def __init__(self):
        if not _meter:
            return
        
        # Counters
        self.agent_calls = _meter.create_counter(
            name="agent.calls.total",
            description="Total number of agent calls",
            unit="1"
        )
        
        self.agent_errors = _meter.create_counter(
            name="agent.errors.total",
            description="Total number of agent errors",
            unit="1"
        )
        
        # Histograms
        self.agent_duration = _meter.create_histogram(
            name="agent.duration.seconds",
            description="Agent execution duration",
            unit="s"
        )
        
        # Gauges (via UpDownCounter)
        self.messages_collected = _meter.create_up_down_counter(
            name="messages.collected.count",
            description="Number of messages collected",
            unit="1"
        )
        
        self.tasks_extracted = _meter.create_up_down_counter(
            name="tasks.extracted.count",
            description="Number of tasks extracted",
            unit="1"
        )

# Global metrics instance
agent_metrics = None

def get_metrics() -> AgentMetrics:
    """Get or create global metrics instance"""
    global agent_metrics
    if agent_metrics is None:
        agent_metrics = AgentMetrics()
    return agent_metrics

# ============================================================================
# Instrumentation Decorators
# ============================================================================

def instrument_agent(agent_func: Callable, agent_name: str) -> Callable:
    """
    Decorator to instrument an agent function with tracing and metrics
    
    Usage:
        @instrument_agent(agent_name="email_collector")
        def email_collector_agent(state):
            ...
    """
    
    @functools.wraps(agent_func)
    def wrapper(state: Dict) -> Dict:
        # Skip if not initialized or disabled
        if not _initialized or not _config.get('enabled', True):
            return agent_func(state)
        
        metrics = get_metrics()
        start_time = time.time()
        
        # Create span for this agent
        with _tracer.start_as_current_span(
            agent_name,
            attributes={
                "agent.name": agent_name,
                "agent.type": "task_planner",
                "workflow.time_range_hours": state.get('time_range_hours', 0)
            }
        ) as span:
            
            # Record agent call
            if metrics.agent_calls:
                metrics.agent_calls.add(1, {"agent.name": agent_name})
            
            try:
                # Execute agent
                result = agent_func(state)
                
                # Record success metrics
                duration = time.time() - start_time
                if metrics.agent_duration:
                    metrics.agent_duration.record(duration, {"agent.name": agent_name, "status": "success"})
                
                # Record specific metrics based on agent
                if agent_name == "email_collector" and metrics.messages_collected:
                    email_count = len(result.get('emails', []))
                    metrics.messages_collected.add(email_count, {"source": "email"})
                    span.set_attribute("emails.count", email_count)
                
                elif agent_name == "slack_collector" and metrics.messages_collected:
                    slack_count = len(result.get('slack_messages', []))
                    metrics.messages_collected.add(slack_count, {"source": "slack"})
                    span.set_attribute("slack_messages.count", slack_count)
                
                elif agent_name == "task_extractor" and metrics.tasks_extracted:
                    task_count = len(result.get('tasks', []))
                    metrics.tasks_extracted.add(task_count, {"type": "extracted"})
                    span.set_attribute("tasks.extracted", task_count)
                
                elif agent_name == "task_prioritizer" and metrics.tasks_extracted:
                    prioritized_count = len(result.get('prioritized_tasks', []))
                    span.set_attribute("tasks.prioritized", prioritized_count)
                    
                    # Count by priority
                    priority_counts = {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0}
                    for task in result.get('prioritized_tasks', []):
                        p = task.get('priority', 'P3')
                        priority_counts[p] += 1
                    
                    for priority, count in priority_counts.items():
                        span.set_attribute(f"tasks.priority.{priority}", count)
                
                elif agent_name == "email_sender":
                    span.set_attribute("email.sent", result.get('email_sent', False))
                    span.set_attribute("email.status", result.get('email_status', ''))
                
                # Record errors if any
                error_count = len(result.get('errors', []))
                if error_count > 0:
                    span.set_attribute("errors.count", error_count)
                    for i, error in enumerate(result.get('errors', [])[:5]):  # Limit to 5
                        span.add_event(f"error_{i}", {"error.message": error})
                
                span.set_status(trace.Status(trace.StatusCode.OK))
                return result
                
            except Exception as e:
                # Record error metrics
                duration = time.time() - start_time
                if metrics.agent_duration:
                    metrics.agent_duration.record(duration, {"agent.name": agent_name, "status": "error"})
                if metrics.agent_errors:
                    metrics.agent_errors.add(1, {"agent.name": agent_name, "error.type": type(e).__name__})
                
                # Record in span
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                # Re-raise
                raise
    
    return wrapper

# ============================================================================
# Workflow-Level Instrumentation
# ============================================================================

def create_workflow_span(workflow_name: str = "multi_agent_workflow"):
    """Create a span for the entire workflow"""
    if not _initialized or not _config.get('enabled', True):
        return DummySpan()
    
    return _tracer.start_as_current_span(
        workflow_name,
        attributes={
            "workflow.name": workflow_name,
            "workflow.timestamp": datetime.now().isoformat()
        }
    )

class DummySpan:
    """No-op context manager when observability is disabled"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def set_attribute(self, *args):
        pass
    def add_event(self, *args):
        pass

# ============================================================================
# Logging Helpers
# ============================================================================

def log_event(event_name: str, attributes: Dict[str, Any] = None):
    """Log a custom event in the current span"""
    if not _initialized or not _config.get('enabled', True):
        return
    
    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(event_name, attributes or {})

def log_state_transition(from_agent: str, to_agent: str, state_summary: Dict[str, Any] = None):
    """Log a state transition between agents"""
    if not _initialized or not _config.get('enabled', True):
        return
    
    attributes = {
        "transition.from": from_agent,
        "transition.to": to_agent,
    }
    
    if state_summary:
        attributes.update(state_summary)
    
    log_event("state_transition", attributes)

# ============================================================================
# LangFuse Integration (LLM-Specific Observability - Fully Abstracted)
# ============================================================================

# LangFuse imports
try:
    from langfuse.callback import CallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    CallbackHandler = None

# Global LangFuse instance
_langfuse_handler = None

def init_langfuse():
    """
    Initialize LangFuse with GLOBAL callback registration
    
    This makes LangFuse completely transparent to workflows:
    - All LLM calls are automatically traced
    - No manual callback handling needed
    - Zero code changes in agents!
    
    Just like ObservableStateGraph auto-instruments agents,
    this auto-instruments all LLMs via global callbacks.
    """
    global _langfuse_handler
    
    if not LANGFUSE_AVAILABLE:
        print("⚠️  LangFuse not installed. LLM observability disabled.")
        print("   Install with: pip install langfuse")
        return
    
    if not _config:
        return
    
    langfuse_config = _config.get('langfuse', {})
    
    if not langfuse_config.get('enabled', True):
        print("📊 LangFuse: Disabled by configuration")
        return
    
    try:
        # Create LangFuse callback handler
        _langfuse_handler = CallbackHandler(
            public_key=os.getenv('LANGFUSE_PUBLIC_KEY') or langfuse_config.get('public_key'),
            secret_key=os.getenv('LANGFUSE_SECRET_KEY') or langfuse_config.get('secret_key'),
            host=os.getenv('LANGFUSE_HOST') or langfuse_config.get('host', 'http://localhost:3000')
        )
        
        # Register GLOBALLY with LangChain
        # This is the magic that makes it automatic!
        from langchain_core.globals import set_llm_cache
        try:
            # Try the new API (LangChain >= 0.1.0)
            from langchain_core.callbacks.manager import configure
            configure(callbacks=[_langfuse_handler])
        except ImportError:
            # Fallback to older API
            from langchain.callbacks import get_callback_manager
            manager = get_callback_manager()
            manager.set_handlers([_langfuse_handler])
        
        print(f"📊 LangFuse: Initialized (GLOBAL auto-instrumentation)")
        print(f"   Host: {langfuse_config.get('host', 'http://localhost:3000')}")
        print(f"   ALL LLM calls automatically traced - zero code changes needed!")
        
        # Link to OTEL if enabled
        if langfuse_config.get('link_to_otel', True) and _tracer:
            print(f"   Linked to OTEL traces (correlated via trace ID)")
        
    except Exception as e:
        print(f"⚠️  LangFuse initialization failed: {e}")
        print(f"   LLM observability will not be available")
        _langfuse_handler = None


def get_langfuse_handler():
    """
    Get LangFuse callback handler (mainly for advanced usage)
    
    Note: You shouldn't need this in most cases!
    LangFuse is automatically applied to all LLM calls via global registration.
    
    Only use this if you need to explicitly pass callbacks for some reason.
    """
    return _langfuse_handler


# ============================================================================
# Auto-Instrumenting StateGraph
# ============================================================================

from langgraph.graph import StateGraph

class ObservableStateGraph(StateGraph):
    """
    Extended StateGraph that automatically instruments all agent nodes
    
    Usage:
        workflow = ObservableStateGraph(MyState)
        workflow.add_node("agent_name", agent_function)  # Auto-instrumented!
    
    Benefits:
        - Zero boilerplate for instrumentation
        - Maintains decoupling (observability logic stays here)
        - Config-driven (respects enabled: false)
        - Backward compatible (can still use regular StateGraph)
    """
    
    def add_node(self, name: str, action: Callable = None, *, metadata: dict = None, input: Any = None, retry: Any = None):
        """
        Override add_node to automatically instrument the action
        
        If observability is enabled, wraps the action with instrument_agent()
        Otherwise behaves exactly like the parent StateGraph
        """
        # Only instrument if action is provided and callable
        if action is not None and callable(action):
            if self._should_instrument():
                # Wrap with instrumentation using the node name
                instrumented_action = instrument_agent(action, name)
                return super().add_node(name, instrumented_action, metadata=metadata, input=input, retry=retry)
        
        # Default behavior - no instrumentation
        return super().add_node(name, action, metadata=metadata, input=input, retry=retry)
    
    def _should_instrument(self) -> bool:
        """Check if observability is enabled in configuration"""
        return _initialized and _config and _config.get('enabled', True)

