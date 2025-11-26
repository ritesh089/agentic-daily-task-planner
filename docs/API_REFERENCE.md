# API Reference

Complete API reference for the Agentic Workflow Framework.

## Table of Contents

- [Configuration](#configuration)
- [Errors](#errors)
- [Resilience](#resilience)
- [Lifecycle](#lifecycle)
- [Health](#health)
- [Observability](#observability)
- [Durability](#durability)
- [Memory](#memory)
- [MCP](#mcp)
- [CLI](#cli)

---

## Configuration

### FrameworkConfig

Unified framework configuration class.

```python
from framework import FrameworkConfig

# Auto-detect configuration
config = FrameworkConfig.auto()

# Load from YAML
config = FrameworkConfig.from_yaml("config/framework.yaml")

# Load from environment variables
config = FrameworkConfig.from_env()

# Programmatic configuration
config = FrameworkConfig(
    observability=ObservabilityConfig(otel_enabled=True),
    durability=DurabilityConfig(enabled=True),
    memory=MemoryConfig(backend='mem0'),
)
```

**Methods:**

- `from_yaml(path: str) -> FrameworkConfig`: Load from YAML file
- `from_env() -> FrameworkConfig`: Load from environment variables
- `auto() -> FrameworkConfig`: Auto-detect configuration (YAML → env → defaults)
- `to_dict() -> Dict`: Convert to dictionary
- `to_yaml(path: str)`: Save to YAML file
- `validate() -> List[str]`: Validate configuration, returns list of issues

**Properties:**

- `observability: ObservabilityConfig`: Observability settings
- `durability: DurabilityConfig`: Durability settings
- `memory: MemoryConfig`: Memory settings
- `mcp: MCPConfig`: MCP settings
- `development: DevelopmentConfig`: Development settings
- `log_level: str`: Logging level
- `workspace_path: Optional[str]`: Workspace path

---

### Sub-Configurations

#### ObservabilityConfig

```python
@dataclass
class ObservabilityConfig:
    otel_enabled: bool = True
    otel_service_name: str = "agentic-workflow"
    otel_endpoint: str = "http://localhost:4317"
    
    langfuse_enabled: bool = True
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "http://localhost:3000"
    
    trace_llm_calls: bool = True
    trace_agent_calls: bool = True
    trace_state_transitions: bool = True
    collect_metrics: bool = True
```

#### DurabilityConfig

```python
@dataclass
class DurabilityConfig:
    enabled: bool = True
    postgres_conn: Optional[str] = None
    checkpoint_every_step: bool = True
    auto_resume: bool = True
    compress_checkpoints: bool = False
    checkpoint_retention_days: int = 30
    use_advisory_locks: bool = True
    lock_timeout_seconds: int = 300
```

#### MemoryConfig

```python
@dataclass
class MemoryConfig:
    enabled: bool = True
    backend: Literal['mem0', 'redis', 'postgres'] = 'mem0'
    
    # mem0 specific
    mem0_vector_store: Literal['chroma', 'qdrant', 'pinecone'] = 'chroma'
    mem0_embedding_model: str = 'all-MiniLM-L6-v2'
    
    # Redis/Postgres specific
    redis_url: Optional[str] = None
    postgres_conn: Optional[str] = None
    
    # Memory management
    max_messages: int = 50
    summarization_threshold: int = 40
    enable_semantic_search: bool = True
```

---

## Errors

### Base Error Class

```python
from framework import FrameworkError

# Create error
error = FrameworkError(
    message="Operation failed",
    recoverable=True,
    retry_after=30,
    context={'operation': 'save', 'attempt': 1},
    error_code="CUSTOM_ERROR"
)

# Check properties
print(error.recoverable)  # True
print(error.retry_after)  # 30
print(error.context)  # {'operation': 'save', 'attempt': 1}

# Serialize
error_dict = error.to_dict()
```

### Specific Error Types

All inherit from `FrameworkError`:

- **ConfigurationError**: Configuration issues
  - `ConfigFileNotFoundError(path)`
  - `InvalidConfigurationError(issues)`

- **CheckpointError**: Checkpoint/durability issues
  - `CheckpointNotFoundError(thread_id, checkpoint_id)`
  - `CheckpointSaveError(reason, thread_id)`
  - `CheckpointLoadError(reason, thread_id)`
  - `DatabaseConnectionError(db_url, reason)`

- **LockError**: Lock management issues
  - `LockAcquisitionError(lock_id, timeout)`
  - `LockAlreadyHeldError(lock_id, holder_info)`

- **WorkflowExecutionError**: Workflow execution issues
  - `WorkflowAlreadyRunningError(thread_id)`
  - `WorkflowBuildError(reason)`
  - `WorkflowCompilationError(reason)`
  - `WorkflowTimeoutError(thread_id, timeout_seconds)`

- **MemoryError**: Memory management issues
  - `MemoryBackendError(backend, reason)`
  - `MemoryStorageError(reason)`
  - `MemoryRetrievalError(reason)`

- **MCPError**: MCP issues
  - `MCPServerError(server_name, reason)`
  - `MCPServerStartupError(server_name, timeout)`
  - `MCPToolCallError(tool_name, reason)`

### Helper Functions

```python
from framework import is_recoverable, get_retry_delay, error_context

try:
    risky_operation()
except Exception as e:
    if is_recoverable(e):
        delay = get_retry_delay(e)
        context = error_context(e)
        print(f"Retrying in {delay}s, context: {context}")
```

---

## Resilience

### Retry Pattern

```python
from framework import with_retry, RetryConfig

# Simple retry
@with_retry()
async def fetch_data():
    return await api.call()

# Custom configuration
@with_retry(RetryConfig(
    max_attempts=5,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
))
async def fetch_data_with_custom_retry():
    return await api.call()
```

### Circuit Breaker Pattern

```python
from framework import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerManager

# Create circuit breaker
breaker = CircuitBreaker(
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        success_threshold=2
    ),
    name="external_api"
)

# Use as decorator
@breaker.protected
async def call_external_api():
    return await api.fetch()

# Or call directly
result = breaker.call(lambda: api.fetch())

# Manual reset
breaker.reset()

# Get status
print(breaker.state)  # CLOSED, OPEN, or HALF_OPEN
```

### Combined Pattern

```python
from framework import resilient

@resilient(
    retry_config=RetryConfig(max_attempts=3),
    circuit_breaker_name="external_api"
)
async def robust_api_call():
    return await api.fetch()
```

---

## Lifecycle

### FrameworkContext

Manages framework component lifecycle.

```python
from framework import FrameworkContext, FrameworkConfig

# Async context manager
async def main():
    async with FrameworkContext.auto() as framework:
        # All components initialized
        runner = WorkflowRunner()
        result = runner.run(...)
    # All components shut down

# Custom configuration
config = FrameworkConfig.from_yaml("config/framework.yaml")
async with FrameworkContext(config) as framework:
    # Use framework
    checkpointer = framework.checkpointer
    mcp_client = framework.mcp_client
```

### SyncFrameworkContext

Synchronous version for non-async code.

```python
from framework import SyncFrameworkContext

def main():
    with SyncFrameworkContext.auto() as framework:
        # Use framework
        pass
```

---

## Health

### FrameworkHealth

Health check system for framework components.

```python
from framework import FrameworkHealth, print_health_report

# Create health checker
health = FrameworkHealth()

# Check all components
results = health.check_all()
for component, result in results.items():
    print(f"{result.component}: {result.status} - {result.message}")

# Check specific component
postgres_health = health.check_postgres()
mem0_health = health.check_mem0()
langfuse_health = health.check_langfuse()

# Overall status
is_healthy = health.is_healthy()
summary = health.get_summary()

# Print formatted report
print_health_report()
```

**Methods:**

- `check_all() -> Dict[str, HealthCheckResult]`: Check all enabled components
- `check_postgres() -> HealthCheckResult`: Check PostgreSQL
- `check_mem0() -> HealthCheckResult`: Check mem0
- `check_redis() -> HealthCheckResult`: Check Redis
- `check_otel() -> HealthCheckResult`: Check OpenTelemetry
- `check_langfuse() -> HealthCheckResult`: Check LangFuse
- `check_mcp_servers() -> HealthCheckResult`: Check MCP servers
- `is_healthy() -> bool`: True if all components healthy/degraded
- `get_summary() -> Dict[str, int]`: Count of each status

---

## Observability

(Existing observability APIs remain unchanged)

```python
from framework import (
    init_observability,
    ObservableStateGraph,
    create_workflow_span,
    instrument_agent
)

# Initialize (usually automatic via FrameworkContext)
init_observability()

# Use observable graph
workflow = ObservableStateGraph(MyState)

# Create spans
with create_workflow_span("my_operation") as span:
    # Automatically traced
    pass

# Instrument agent
@instrument_agent("my_agent")
def my_agent(state):
    return state
```

---

## Durability

(Existing durability APIs remain unchanged)

```python
from framework import (
    WorkflowRunner,
    CheckpointerManager,
    needs_resume,
    resume_workflow,
    find_failed_workflows
)

# High-level API (recommended)
runner = WorkflowRunner(enable_checkpointing=True)
result = runner.run(
    workflow_builder=build_workflow,
    initial_state=initial_state,
    session_id="my-session",
    auto_resume=True
)

# Low-level API
if needs_resume("my-thread-id"):
    result = resume_workflow("my-thread-id")

# Find failed workflows
failed = find_failed_workflows()
for checkpoint in failed:
    print(f"Failed: {checkpoint.thread_id}")
```

---

## Memory

(Existing memory APIs remain unchanged)

```python
from framework import (
    MemoryManager,
    create_memory_aware_reducer,
    with_conversation_memory
)

# Smart reducer (recommended)
reducer = create_memory_aware_reducer()

# Decorator
@with_conversation_memory(
    system_prompt="You are helpful",
    max_messages=50
)
def chat_agent(state):
    MemoryManager.add_user_message(state, query)
    messages = MemoryManager.get_langchain_messages(state)
    return state

# Semantic search (powered by mem0)
relevant = MemoryManager.search_memories(
    state,
    query="user preferences",
    limit=5
)
```

---

## MCP

(Existing MCP APIs remain unchanged)

```python
from framework import (
    init_mcp_client,
    shutdown_mcp_client,
    get_mcp_manager
)

# Initialize (usually automatic)
client = await init_mcp_client()

# Get tools
manager = get_mcp_manager()
tools = manager.get_tools()

# Cleanup
await shutdown_mcp_client()
```

---

## CLI

### Command-Line Interface

```bash
# Health check
bin/framework health

# Create new workflow
bin/framework init my-workflow --template conversational --output examples/

# Validate workflow
bin/framework validate examples/my-workflow/

# Configuration
bin/framework config  # Show config
bin/framework config --validate  # Validate
bin/framework config --create my-config.yaml  # Create template

# Version
bin/framework version
```

### Programmatic CLI

```python
from framework import FrameworkCLI

cli = FrameworkCLI()
exit_code = cli.run(["health"])
```

---

## Quick Reference

### Most Common Patterns

#### 1. Basic Workflow with Auto-Configuration

```python
from framework import WorkflowRunner
from app.workflow import build_workflow

runner = WorkflowRunner()
result = runner.run(
    workflow_builder=build_workflow,
    initial_state={'input': 'data'}
)
```

#### 2. Workflow with Custom Configuration

```python
from framework import FrameworkConfig, FrameworkContext, WorkflowRunner

config = FrameworkConfig.from_yaml("custom-config.yaml")

async with FrameworkContext(config) as framework:
    runner = WorkflowRunner(enable_checkpointing=True)
    result = runner.run(...)
```

#### 3. Error Handling with Retry

```python
from framework import with_retry, RetryConfig

@with_retry(RetryConfig(max_attempts=3))
async def fetch_data():
    return await api.call()
```

#### 4. Health Check Before Running

```python
from framework import FrameworkHealth

health = FrameworkHealth()
if not health.is_healthy():
    print("Framework not ready!")
    exit(1)

# Proceed with workflow
```

---

## Type Hints

The framework is fully typed. Use your IDE's autocomplete and type checking:

```python
from framework import FrameworkConfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    reveal_type(FrameworkConfig.auto())  # FrameworkConfig
```

---

## See Also

- [Framework Guide](FRAMEWORK_GUIDE.md) - How to use the framework
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Durability Guide](DURABILITY_GUIDE.md) - Checkpoint and resume patterns
- [Observability Guide](OBSERVABILITY_GUIDE.md) - Tracing and monitoring
- [Memory Guide](MEMORY_MANAGEMENT_GUIDE.md) - Conversation memory

