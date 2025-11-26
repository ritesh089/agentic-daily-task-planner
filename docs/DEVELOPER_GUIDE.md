# Agentic Workflow Framework - Developer Guide

**Complete guide for framework developers and contributors**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Framework Components](#framework-components)
3. [Design Principles](#design-principles)
4. [Development Setup](#development-setup)
5. [Testing](#testing)
6. [Contributing](#contributing)
7. [Implementation Details](#implementation-details)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
│  • User-defined workflows                                       │
│  • Agent implementations                                        │
│  • Business logic                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Framework Layer                              │
│  ┌─────────────┬──────────────┬──────────────┬─────────────┐  │
│  │ Config      │ Observability│ Durability   │ Memory      │  │
│  │ Management  │ (OTEL/LF)    │ (PostgreSQL) │ (mem0)      │  │
│  ├─────────────┼──────────────┼──────────────┼─────────────┤  │
│  │ Errors &    │ Resilience   │ Workflow     │ MCP         │  │
│  │ Exceptions  │ (Retry/CB)   │ Runner       │ Integration │  │
│  └─────────────┴──────────────┴──────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                         │
│  • PostgreSQL (checkpoints, locks)                             │
│  • Jaeger (OTEL backend)                                       │
│  • LangFuse (LLM tracing)                                      │
│  • MCP Servers (tools)                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Design Philosophy

1. **Zero Boilerplate**: Applications should focus on business logic
2. **Separation of Concerns**: Framework handles cross-cutting concerns
3. **Opt-In Features**: Everything is optional and composable
4. **Backward Compatibility**: Never break existing code
5. **Developer Experience**: Make the right thing easy

---

## Framework Components

### 1. Configuration Management

**File**: `framework/config.py`

**Purpose**: Unified configuration for all framework components

**Architecture**:
```python
FrameworkConfig
├── ObservabilityConfig
├── DurabilityConfig
├── MemoryConfig
├── MCPConfig
└── DevelopmentConfig
```

**Key Design Decisions**:
- **Auto-detection**: YAML → env → defaults (priority order)
- **Type-safe**: Using dataclasses for compile-time checking
- **Validation**: Built-in validation with helpful error messages
- **Singleton**: Global config accessible via `get_config()`

**Implementation**:
```python
@dataclass
class FrameworkConfig:
    @classmethod
    def auto(cls) -> 'FrameworkConfig':
        # Try explicit config file
        config_path = os.getenv('FRAMEWORK_CONFIG')
        if config_path and Path(config_path).exists():
            return cls.from_yaml(config_path)
        
        # Try default locations
        for path in ['config/framework.yaml', 'framework.yaml']:
            if Path(path).exists():
                config = cls.from_yaml(path)
                env_config = cls.from_env()
                return cls._merge(config, env_config)
        
        # Fall back to env + defaults
        return cls.from_env()
```

---

### 2. Error Handling

**File**: `framework/errors.py`

**Purpose**: Comprehensive error hierarchy with recovery support

**Architecture**:
```python
FrameworkError (base)
├── ConfigurationError
├── CheckpointError
│   ├── CheckpointNotFoundError
│   ├── CheckpointSaveError
│   └── DatabaseConnectionError
├── LockError
│   ├── LockAcquisitionError
│   └── LockAlreadyHeldError
├── WorkflowExecutionError
│   ├── WorkflowAlreadyRunningError
│   ├── WorkflowBuildError
│   └── WorkflowTimeoutError
├── MemoryError
├── MCPError
└── ObservabilityError
```

**Key Design Decisions**:
- **Recovery Hints**: `recoverable` flag + `retry_after` guidance
- **Context Preservation**: Dict for additional debugging info
- **Serialization**: `.to_dict()` for logging/telemetry
- **Error Codes**: Unique codes for categorization

**Implementation**:
```python
class FrameworkError(Exception):
    def __init__(
        self,
        message: str,
        recoverable: bool = False,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.context = context or {}
        self.error_code = error_code or self.__class__.__name__
        self.timestamp = datetime.now()
```

---

### 3. Resilience Patterns

**File**: `framework/resilience.py`

**Purpose**: Fault tolerance via retry and circuit breaker patterns

**Components**:

#### Retry Pattern
```python
@with_retry(RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    exponential_base=2.0,
    jitter=True
))
async def operation():
    return await api.call()
```

**Algorithm**:
1. Attempt operation
2. On failure, check if recoverable
3. Calculate delay with exponential backoff + jitter
4. Sleep and retry
5. Repeat up to max_attempts

**Jitter Calculation**:
```python
delay = min(initial_delay * (base ** attempt), max_delay)
jitter_range = delay * jitter_factor
delay += random.uniform(-jitter_range, jitter_range)
```

#### Circuit Breaker Pattern
```python
breaker = CircuitBreaker(
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0
    )
)

@breaker.protected
def operation():
    return external_service.call()
```

**State Machine**:
```
CLOSED ──failure_threshold──> OPEN
  ↑                             │
  └── success_threshold ──  HALF_OPEN
                             ↑
                             └── recovery_timeout
```

**Key Design Decisions**:
- **Dual Support**: Works with both sync and async functions
- **Automatic Recovery**: Circuit transitions to half-open after timeout
- **Failure Counting**: Tracks consecutive failures
- **Manager Pattern**: `CircuitBreakerManager` for multiple breakers

---

### 4. Lifecycle Management

**File**: `framework/lifecycle.py`

**Purpose**: Centralized component initialization and cleanup

**Architecture**:
```python
FrameworkContext (async)
├── __aenter__()
│   ├── init_observability()
│   ├── init_mcp_client()
│   ├── init_checkpointer()
│   └── init_memory()
└── __aexit__()
    ├── shutdown_mcp_client()
    └── close_checkpointer()

SyncFrameworkContext (sync wrapper)
```

**Key Design Decisions**:
- **Context Manager**: Ensures cleanup even on errors
- **Lazy Initialization**: Only init enabled components
- **Error Handling**: Component failures don't break others
- **Sync/Async**: Separate wrappers for both paradigms

**Implementation**:
```python
class FrameworkContext:
    async def __aenter__(self):
        if self.config.observability.otel_enabled:
            await self._init_observability()
        if self.config.mcp.enabled:
            await self._init_mcp()
        # ... more initializations
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cleanup()
```

---

### 5. Health Checks

**File**: `framework/health.py`

**Purpose**: Diagnostics for all framework components

**Architecture**:
```python
FrameworkHealth
├── check_all() -> Dict[str, HealthCheckResult]
├── check_postgres()
├── check_mem0()
├── check_redis()
├── check_otel()
├── check_langfuse()
└── check_mcp_servers()

HealthCheckResult
├── component: str
├── status: HealthStatus (healthy/degraded/unhealthy/disabled)
├── message: str
├── details: Dict
└── checked_at: datetime
```

**Key Design Decisions**:
- **Detailed Status**: Four states (healthy, degraded, unhealthy, disabled)
- **Context**: Details dict for debugging
- **Non-Blocking**: Failures don't prevent other checks
- **CLI Integration**: Formatted output for `bin/framework health`

---

### 6. Observability

**File**: `framework/observability.py`

**Purpose**: Dual tracing (OTEL + LangFuse) with zero-code instrumentation

**Architecture**:
```python
ObservabilitySystem
├── OpenTelemetry (OTEL)
│   ├── TracerProvider
│   ├── JaegerExporter
│   └── ObservableStateGraph (LangGraph wrapper)
└── LangFuse
    ├── CallbackHandler (global registration)
    └── Automatic LLM tracing
```

**Key Design Decisions**:
- **Global Callbacks**: LangChain's `set_default_callbacks()` for automatic LLM tracing
- **Wrapper Pattern**: `ObservableStateGraph` wraps LangGraph for automatic spans
- **Separation**: OTEL for application, LangFuse for LLM calls
- **Zero-Code**: No manual instrumentation needed

**Implementation**:
```python
def init_langfuse():
    from langfuse.callback import CallbackHandler
    from langchain.callbacks import set_default_callbacks
    
    handler = CallbackHandler(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key,
        host=config.langfuse_host
    )
    
    # Global registration - all LLM calls traced automatically
    set_default_callbacks([handler])
```

---

### 7. Durability

**File**: `framework/durability.py`

**Purpose**: PostgreSQL-backed checkpointing for durable execution

**Architecture**:
```python
Durability System
├── CheckpointerManager (singleton)
│   └── PostgresSaver (LangGraph's checkpointer)
├── Checkpoint Operations
│   ├── needs_resume()
│   ├── resume_workflow()
│   ├── find_failed_workflows()
│   └── get_checkpoint_status()
└── Lock Management
    ├── PostgresLockManager
    └── Advisory locks for concurrency control
```

**Database Schema** (LangGraph-managed):
```sql
-- checkpoints table
CREATE TABLE checkpoints (
    thread_id TEXT,
    checkpoint_ns TEXT,
    checkpoint_id UUID,
    parent_checkpoint_id UUID,
    type TEXT,
    checkpoint BYTEA,
    metadata JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- checkpoint_blobs table (for large data)
CREATE TABLE checkpoint_blobs (
    thread_id TEXT,
    checkpoint_ns TEXT,
    channel TEXT,
    version TEXT,
    data BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
```

**Key Design Decisions**:
- **Automatic**: Saved after each workflow step
- **Resume Detection**: Check `checkpoint_ns` for completion
- **Advisory Locks**: Prevent concurrent execution
- **Thread-based**: Each workflow execution has unique thread_id

**Implementation**:
```python
def needs_resume(thread_id: str) -> bool:
    """Check if workflow needs resume."""
    cursor.execute("""
        SELECT checkpoint_id, checkpoint_ns
        FROM checkpoints
        WHERE thread_id = %s
        ORDER BY checkpoint_id DESC
        LIMIT 1
    """, (thread_id,))
    
    row = cursor.fetchone()
    if not row:
        return False
    
    # Check if workflow completed
    # Empty checkpoint_ns means workflow reached END
    return row[1] != ""
```

---

### 8. Memory Management

**File**: `framework/memory.py`

**Purpose**: Conversation memory with semantic search (powered by mem0)

**Architecture**:
```python
Memory System
├── _Mem0Backend (internal wrapper)
│   ├── Memory (mem0.ai)
│   └── Chroma (vector store)
├── create_memory_aware_reducer()
│   └── Smart reducer for automatic memory
├── MemoryManager (API)
│   ├── add_user_message()
│   ├── add_assistant_message()
│   ├── get_langchain_messages()
│   └── search_memories()
└── MemoryConfig (configuration)
```

**Key Design Decisions**:
- **Backend Abstraction**: mem0 wrapped for framework API
- **Smart Reducer**: Automatic memory management via LangGraph reducers
- **Semantic Search**: Powered by mem0's vector search
- **Pruning Strategy**: Keep recent messages, search older ones

**Implementation**:
```python
def create_memory_aware_reducer():
    """Create reducer with automatic memory management."""
    def reducer(current: list, new: list) -> list:
        # Add new messages
        updated = current + new
        
        # Prune if needed
        if len(updated) > max_messages:
            # Store in mem0 for semantic search
            _Mem0Backend.add_messages(thread_id, updated)
            
            # Keep recent messages
            updated = updated[-max_messages:]
        
        return updated
    
    return reducer
```

---

### 9. Workflow Runner

**File**: `framework/workflow_runner.py`

**Purpose**: High-level API for workflow execution with durability

**Architecture**:
```python
WorkflowRunner
├── __init__(enable_checkpointing, postgres_conn)
├── run(workflow_builder, initial_state, session_id, auto_resume)
├── list_incomplete_sessions()
└── get_session_status(session_id)
```

**Execution Flow**:
```
1. Check if session needs resume
   ├── Yes → Resume from checkpoint
   └── No → Start fresh

2. Initialize checkpointer (if enabled)
   └── Create PostgresSaver

3. Build workflow
   └── Call workflow_builder()

4. Compile workflow
   └── workflow.compile(checkpointer=...)

5. Execute workflow
   └── compiled_workflow.invoke(state, config)

6. Return result
   └── {status, data, session_id}
```

**Key Design Decisions**:
- **Automatic Resume**: Detects and resumes interrupted workflows
- **Session Management**: Thread IDs track workflow instances
- **Checkpointer Integration**: Seamless PostgreSQL checkpointing
- **Error Handling**: Wraps execution with proper error handling

---

### 10. CLI Tool

**File**: `framework/framework_cli.py`

**Purpose**: Command-line interface for framework operations

**Architecture**:
```python
FrameworkCLI
├── cmd_init()        # Create workflows
├── cmd_validate()    # Validate structure
├── cmd_health()      # Health checks
├── cmd_config()      # Config management
├── cmd_test()        # Test workflows (future)
└── cmd_version()     # Show version
```

**Templates**:
- `minimal`: Basic workflow template
- `conversational`: Chat-based workflow
- `data-processor`: Data processing workflow

**Key Design Decisions**:
- **Argparse**: Standard Python CLI library
- **Templates**: Scaffolding for quick starts
- **Validation**: Check workflow structure
- **Integration**: Uses framework components (health, config)

---

## Design Principles

### 1. Zero Boilerplate Philosophy

**Problem**: Repetitive setup code in every workflow

**Solution**: Framework handles cross-cutting concerns automatically

**Example**:
```python
# Application code (clean!)
def build_workflow():
    workflow = ObservableStateGraph(MyState)
    workflow.add_node("process", process_agent)
    return workflow

# Framework handles:
# - Observability instrumentation
# - Checkpoint configuration
# - Error handling
# - Resource cleanup
```

### 2. Opt-In Features

**Problem**: One-size-fits-all doesn't work

**Solution**: Everything is optional and composable

**Example**:
```python
# Minimal (no extras)
runner = WorkflowRunner(enable_checkpointing=False)

# With durability
runner = WorkflowRunner(enable_checkpointing=True)

# Full features (via config)
config = FrameworkConfig.auto()  # All features enabled
```

### 3. Backward Compatibility

**Problem**: Breaking changes frustrate users

**Solution**: Never break existing APIs, add new ones

**Example**:
```python
# Old API (still works)
from framework import WorkflowRunner
runner = WorkflowRunner()

# New API (opt-in)
from framework import FrameworkContext, WorkflowRunner
async with FrameworkContext.auto() as framework:
    runner = WorkflowRunner()
```

### 4. Separation of Concerns

**Problem**: Mixed responsibilities make code hard to maintain

**Solution**: Clear boundaries between layers

**Layers**:
1. **Application**: Business logic, agents, workflows
2. **Framework**: Cross-cutting concerns, utilities
3. **Infrastructure**: Databases, services, APIs

### 5. Developer Experience

**Problem**: Framework hard to use

**Solution**: Make the right thing easy

**Strategies**:
- Auto-configuration (smart defaults)
- Rich error messages (helpful hints)
- CLI tools (quick commands)
- Comprehensive documentation
- Examples for common patterns

---

## Development Setup

### Prerequisites

- Python 3.13+
- Docker & Docker Compose
- PostgreSQL client (for testing)
- Git

### Setup

```bash
# Clone repository
git clone <repo-url>
cd agentic-daily-task-planner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov black mypy ruff

# Start infrastructure
docker-compose up -d

# Verify setup
bin/framework health
```

### Development Workflow

```bash
# 1. Make changes
vim framework/my_feature.py

# 2. Run tests
pytest tests/unit/ -v
pytest tests/ -v  # All tests

# 3. Check code quality
black framework/  # Format
mypy framework/   # Type check
ruff framework/   # Lint

# 4. Run examples
cd examples/conversational-assistant
python main.py
```

---

## Testing

### Test Structure

```
tests/
├── unit/                      # Unit tests
│   ├── test_config.py         # Configuration
│   ├── test_errors.py         # Error handling
│   └── test_resilience.py     # Retry/circuit breaker
├── integration/               # Integration tests
│   └── test_durability.py     # Checkpoint & resume
└── e2e/                       # End-to-end tests
    └── test_conversational_assistant_durability.py
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/test_durability.py -v

# With coverage
pytest tests/ --cov=framework --cov-report=html
```

### Writing Tests

**Unit Test Example**:
```python
def test_config_auto_detection():
    """Test automatic configuration detection."""
    config = FrameworkConfig.auto()
    assert config is not None
    assert config.observability.otel_enabled is True
```

**Integration Test Example**:
```python
def test_checkpoint_and_resume():
    """Test workflow can checkpoint and resume."""
    # Create workflow that fails mid-execution
    workflow = create_test_workflow(fail_on_step=2)
    
    # Run until failure
    with pytest.raises(SimulatedFailure):
        workflow.invoke(initial_state)
    
    # Verify checkpoint exists
    assert needs_resume(thread_id)
    
    # Resume and complete
    result = resume_workflow(thread_id)
    assert result['status'] == 'success'
```

---

## Contributing

### Code Style

- **Formatting**: Black (line length 100)
- **Type Hints**: Required for all public APIs
- **Docstrings**: Google style
- **Imports**: Sorted (isort)

### Commit Guidelines

```
type(scope): subject

body

footer
```

**Types**: feat, fix, docs, test, refactor, perf, chore

**Example**:
```
feat(config): add auto-detection for configuration

Implement FrameworkConfig.auto() that tries YAML files,
then environment variables, then defaults.

Closes #123
```

### Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/my-feature`)
3. Make changes with tests
4. Run full test suite
5. Update documentation
6. Submit PR with description

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Error handling implemented
- [ ] Backward compatible
- [ ] Performance acceptable
- [ ] Security considerations addressed

---

## Implementation Details

### Adding a New Framework Component

1. **Create module** in `framework/`:
```python
# framework/my_feature.py
class MyFeature:
    """My new feature."""
    def __init__(self, config):
        self.config = config
    
    def do_something(self):
        pass
```

2. **Add configuration**:
```python
# framework/config.py
@dataclass
class MyFeatureConfig:
    enabled: bool = True
    option: str = "default"

@dataclass
class FrameworkConfig:
    my_feature: MyFeatureConfig = field(default_factory=MyFeatureConfig)
```

3. **Export from __init__.py**:
```python
# framework/__init__.py
from framework.my_feature import MyFeature

__all__ = [
    # ... existing exports
    'MyFeature',
]
```

4. **Add tests**:
```python
# tests/unit/test_my_feature.py
def test_my_feature():
    feature = MyFeature(config)
    assert feature.do_something() == expected
```

5. **Update documentation**:
- Add to `docs/USER_GUIDE.md`
- Add to `docs/API_REFERENCE.md`
- Update `README.md` if major feature

### Debugging Tips

**Enable verbose logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Use health checks**:
```bash
bin/framework health
```

**Check configuration**:
```bash
bin/framework config --validate
```

**Inspect checkpoints**:
```sql
SELECT thread_id, checkpoint_id, checkpoint_ns
FROM checkpoints
ORDER BY checkpoint_id DESC
LIMIT 10;
```

---

## Support

- **Documentation**: `docs/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: [framework@example.com]

---

**Last Updated**: November 25, 2025  
**Framework Version**: 1.0.0-beta
