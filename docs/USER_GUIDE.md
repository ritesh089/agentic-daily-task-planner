# Agentic Workflow Framework - User Guide

**Complete guide for building agentic workflows with the framework**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Configuration](#configuration)
4. [Building Workflows](#building-workflows)
5. [Memory Management](#memory-management)
6. [Observability](#observability)
7. [Durability & Checkpointing](#durability--checkpointing)
8. [Error Handling](#error-handling)
9. [MCP Integration](#mcp-integration)
10. [CLI Tools](#cli-tools)
11. [Best Practices](#best-practices)

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd agentic-daily-task-planner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start infrastructure
docker-compose up -d

# Verify setup
bin/framework health
```

### Your First Workflow

1. **Create a new workflow:**

```bash
bin/framework init my-bot --template minimal
cd examples/my-bot
```

2. **Edit the workflow** (`app/workflow.py`):

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from framework import ObservableStateGraph

class MyState(TypedDict):
    input: str
    output: str

def process_agent(state: MyState) -> MyState:
    state['output'] = f"Processed: {state['input']}"
    return state

def build_workflow() -> StateGraph:
    workflow = ObservableStateGraph(MyState)
    workflow.add_node("process", process_agent)
    workflow.add_edge(START, "process")
    workflow.add_edge("process", END)
    return workflow
```

3. **Run it:**

```bash
python main.py
```

---

## Core Concepts

### Framework Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Application                             │
│  app/workflow.py     - build_workflow() function               │
│  app/agents/         - Your agent implementations               │
│  config/             - App-specific configuration               │
│  main.py             - Entry point                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Framework (Reusable)                         │
│  • Configuration Management  • Error Handling                   │
│  • Observability (OTEL)     • Durability                       │
│  • Memory Management        • Resilience Patterns              │
│  • MCP Integration          • Health Checks                    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **ObservableStateGraph**: Enhanced LangGraph with automatic tracing
2. **WorkflowRunner**: Manages workflow execution with durability
3. **MemoryManager**: Handles conversation memory (powered by mem0)
4. **MCPClient**: Integrates with MCP tool servers
5. **FrameworkConfig**: Unified configuration management

---

## Configuration

### Auto-Configuration (Recommended)

The framework automatically detects configuration:

```python
from framework import FrameworkConfig

# Auto-detect: YAML → env variables → defaults
config = FrameworkConfig.auto()
```

### Configuration File

Create `config/framework.yaml`:

```yaml
observability:
  otel_enabled: true
  langfuse_enabled: true
  langfuse_host: http://localhost:3000

durability:
  enabled: true
  auto_resume: true

memory:
  backend: mem0
  max_messages: 50

mcp:
  enabled: true
  use_mock_servers: false

log_level: INFO
```

### Environment Variables

```bash
# Observability
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=http://localhost:3000

# Durability
export POSTGRES_CONNECTION="postgresql://postgres:postgres@localhost:5432/langgraph"

# Framework
export FRAMEWORK_LOG_LEVEL=DEBUG
```

### Programmatic Configuration

```python
from framework import FrameworkConfig, ObservabilityConfig, DurabilityConfig

config = FrameworkConfig(
    observability=ObservabilityConfig(
        otel_enabled=True,
        langfuse_enabled=True
    ),
    durability=DurabilityConfig(
        enabled=True,
        auto_resume=True
    ),
    log_level="INFO"
)
```

### Validation

```bash
# Validate configuration
bin/framework config --validate

# Show current configuration
bin/framework config
```

---

## Building Workflows

### Basic Workflow

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from framework import ObservableStateGraph

# 1. Define State
class MyState(TypedDict):
    input: str
    result: str

# 2. Define Agents
def agent_a(state: MyState) -> MyState:
    state['result'] = f"Processed: {state['input']}"
    return state

# 3. Build Workflow
def build_workflow() -> StateGraph:
    workflow = ObservableStateGraph(MyState)
    
    # Add nodes
    workflow.add_node("process", agent_a)
    
    # Add edges
    workflow.add_edge(START, "process")
    workflow.add_edge("process", END)
    
    return workflow
```

### Conversational Workflow

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from framework import (
    ObservableStateGraph,
    create_memory_aware_reducer,
    MemoryManager,
    InteractiveCommandHandler
)

# 1. Define State with Memory
class ConversationalState(TypedDict):
    user_query: str
    assistant_response: str
    conversation_history: Annotated[list, create_memory_aware_reducer()]

# 2. Define Conversational Agents
def get_user_input_agent(state: ConversationalState) -> ConversationalState:
    query = input("\n🤔 You: ")
    
    # Handle interactive commands (status, export, help, exit)
    if InteractiveCommandHandler.handle(query, state):
        return state
    
    state['user_query'] = query
    return state

def generate_response_agent(state: ConversationalState) -> ConversationalState:
    # Add user message to memory
    MemoryManager.add_user_message(state, state['user_query'])
    
    # Get conversation history for LLM
    messages = MemoryManager.get_langchain_messages(state)
    
    # Generate response
    response = llm.invoke(messages)
    
    # Add assistant response to memory
    MemoryManager.add_assistant_message(state, response.content)
    
    state['assistant_response'] = response.content
    return state

def display_agent(state: ConversationalState) -> ConversationalState:
    print(f"\n💡 Assistant: {state['assistant_response']}")
    return state

# 3. Build Workflow
def build_workflow() -> StateGraph:
    workflow = ObservableStateGraph(ConversationalState)
    
    workflow.add_node("get_input", get_user_input_agent)
    workflow.add_node("generate", generate_response_agent)
    workflow.add_node("display", display_agent)
    
    workflow.add_edge(START, "get_input")
    workflow.add_edge("get_input", "generate")
    workflow.add_edge("generate", "display")
    workflow.add_edge("display", "get_input")  # Loop back
    
    return workflow
```

### Running Workflows

```python
from framework import WorkflowRunner
from app.workflow import build_workflow

# Simple execution
runner = WorkflowRunner(enable_checkpointing=False)
result = runner.run(
    workflow_builder=build_workflow,
    initial_state={'input': 'Hello'}
)

# With durability
runner = WorkflowRunner(enable_checkpointing=True)
result = runner.run(
    workflow_builder=build_workflow,
    initial_state={'input': 'Hello'},
    session_id="my-session",
    auto_resume=True
)
```

---

## Memory Management

### Powered by mem0

The framework uses [mem0](https://mem0.ai) for intelligent memory management with semantic search.

### Automatic Memory (Recommended)

Use the smart reducer for automatic memory management:

```python
from framework import create_memory_aware_reducer
from typing import Annotated

class State(TypedDict):
    conversation_history: Annotated[list, create_memory_aware_reducer()]
```

The framework automatically:
- Adds messages to conversation history
- Prunes old messages when limit is reached
- Stores memories in mem0 for semantic search

### Manual Memory Management

```python
from framework import MemoryManager

# Add messages
MemoryManager.add_user_message(state, "Hello!")
MemoryManager.add_assistant_message(state, "Hi there!")

# Get messages for LLM
messages = MemoryManager.get_langchain_messages(state)

# Semantic search (powered by mem0)
relevant_memories = MemoryManager.search_memories(
    state,
    query="user preferences about summaries",
    limit=5
)
```

### Memory Configuration

```yaml
# config/memory_config.yaml
memory:
  max_messages: 50
  summarization_threshold: 40
  profile: conversational
```

Or programmatically:

```python
from framework import MemoryConfig

config = MemoryConfig(
    max_messages=50,
    summarization_threshold=40,
    profile="conversational"
)
```

### Memory Profiles

- `default`: Basic message management
- `conversational`: Optimized for chat interfaces
- `task_oriented`: Optimized for task completion
- `long_context`: Large context windows

---

## Observability

### Dual Observability System

The framework provides two complementary observability systems:

1. **OpenTelemetry (OTEL)**: Application-level tracing
2. **LangFuse**: LLM-specific tracing

### Automatic Tracing (Zero Code!)

Just enable in configuration:

```yaml
observability:
  otel_enabled: true
  langfuse_enabled: true
```

All workflows and LLM calls are automatically traced!

### View Traces

**OpenTelemetry (Jaeger):**
- Open http://localhost:16686
- View workflow traces, agent calls, state transitions

**LangFuse:**
- Open http://localhost:3000
- View LLM calls, prompts, responses, tokens, costs

### Manual Instrumentation

```python
from framework import create_workflow_span, instrument_agent

# Manual span creation
with create_workflow_span("custom_operation") as span:
    result = do_something()
    span.set_attribute("result_count", len(result))

# Instrument agent
@instrument_agent("my_custom_agent")
def my_agent(state):
    return state
```

### Configuration

```yaml
observability:
  # OTEL
  otel_enabled: true
  otel_service_name: my-workflow
  otel_endpoint: http://localhost:4317
  
  # LangFuse
  langfuse_enabled: true
  langfuse_host: http://localhost:3000
  
  # Tracing options
  trace_llm_calls: true
  trace_agent_calls: true
  trace_state_transitions: true
```

---

## Durability & Checkpointing

### Automatic Checkpoint & Resume

The framework automatically checkpoints workflow state to PostgreSQL:

```python
from framework import WorkflowRunner

runner = WorkflowRunner(enable_checkpointing=True)

result = runner.run(
    workflow_builder=build_workflow,
    initial_state=initial_state,
    session_id="my-session",
    auto_resume=True  # Automatically resumes if interrupted
)
```

### How It Works

1. **Automatic Checkpointing**: State saved after each step
2. **Failure Detection**: Framework detects incomplete sessions
3. **Automatic Resume**: Workflow continues from last checkpoint
4. **State Preservation**: No data loss on failure

### Manual Resume

```python
from framework import needs_resume, resume_workflow, find_failed_workflows

# Check if resume is needed
if needs_resume("my-session"):
    result = resume_workflow("my-session")

# Find all failed workflows
failed = find_failed_workflows()
for checkpoint in failed:
    print(f"Failed: {checkpoint.thread_id}")
    resume_workflow(checkpoint.thread_id)
```

### Configuration

```yaml
durability:
  enabled: true
  postgres_conn: "postgresql://postgres:postgres@localhost:5432/langgraph"
  checkpoint_every_step: true
  auto_resume: true
  use_advisory_locks: true  # Prevent concurrent execution
```

### Concurrency Control

The framework uses PostgreSQL advisory locks to prevent multiple instances:

```python
# Automatically handled by WorkflowRunner
# If workflow is already running, you'll get:
# WorkflowAlreadyRunningError
```

---

## Error Handling

### Rich Error Hierarchy

The framework provides comprehensive error types:

```python
from framework import (
    FrameworkError,
    ConfigurationError,
    CheckpointError,
    WorkflowExecutionError,
    MemoryError,
    MCPError
)

try:
    result = workflow.run()
except CheckpointError as e:
    if e.recoverable:
        time.sleep(e.retry_after)
        retry()
    else:
        raise
```

### Error Properties

```python
error = FrameworkError(
    message="Operation failed",
    recoverable=True,          # Can be retried
    retry_after=30,           # Retry after 30 seconds
    context={'attempt': 1},    # Additional context
    error_code="CUSTOM_ERROR"  # Error code
)

# Check error properties
if error.recoverable:
    delay = error.retry_after
    context = error.context
```

### Automatic Retry

```python
from framework import with_retry, RetryConfig

@with_retry(RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
))
async def fetch_data():
    return await api.call()

# Automatically retries on recoverable errors
# with exponential backoff
```

### Circuit Breaker

```python
from framework import CircuitBreaker, CircuitBreakerConfig

breaker = CircuitBreaker(
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0
    ),
    name="external_api"
)

@breaker.protected
async def call_external_api():
    return await api.fetch()

# Circuit opens after 5 failures
# Rejects requests while open
# Automatically recovers after timeout
```

### Combined Resilience

```python
from framework import resilient, RetryConfig

@resilient(
    retry_config=RetryConfig(max_attempts=3),
    circuit_breaker_name="external_api"
)
async def robust_call():
    return await api.fetch()

# Combines retry + circuit breaker
```

---

## MCP Integration

### Model Context Protocol

The framework integrates with MCP servers for tool calling:

```python
from framework import get_mcp_manager

# Get available tools
manager = get_mcp_manager()
tools = manager.get_tools()

# Use tools in agents
def agent_with_tools(state):
    # Tools are automatically available to LLM
    response = llm_with_tools.invoke(messages, tools=tools)
    return state
```

### Configuration

```json
// config/mcp_config.json
{
  "mcpServers": {
    "email": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gmail"]
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"]
    }
  }
}
```

### Mock Servers

For development/testing:

```yaml
mcp:
  enabled: true
  use_mock_servers: true  # Use mocks instead of real servers
```

---

## CLI Tools

### Framework CLI

```bash
# Health check
bin/framework health

# Configuration
bin/framework config
bin/framework config --validate
bin/framework config --create my-config.yaml

# Create new workflow
bin/framework init my-bot --template conversational

# Validate workflow
bin/framework validate examples/my-bot/

# Version
bin/framework version
```

### Health Check

```bash
$ bin/framework health

======================================================================
Framework Health Check
======================================================================

✅ PostgreSQL: Connected
✅ mem0: Installed and available
✅ OpenTelemetry: Initialized
⚠️  LangFuse: API keys not set
✅ MCP Servers: 2 server(s) configured

Overall Status: PASSED
```

---

## Best Practices

### 1. Configuration Management

✅ **Use auto-configuration:**
```python
config = FrameworkConfig.auto()
```

✅ **Validate before deployment:**
```bash
bin/framework config --validate
```

✅ **Use environment variables for secrets:**
```bash
export LANGFUSE_SECRET_KEY=sk-lf-...
```

### 2. Workflow Design

✅ **Keep agents focused:**
```python
# Good: Single responsibility
def fetch_data_agent(state): ...
def process_data_agent(state): ...
def store_data_agent(state): ...

# Bad: Doing everything
def do_everything_agent(state): ...
```

✅ **Use type hints:**
```python
from typing import TypedDict

class MyState(TypedDict):
    input: str
    output: str
```

✅ **Handle errors gracefully:**
```python
@with_retry()
def risky_operation(state):
    try:
        result = external_api.call()
    except Exception as e:
        state['error'] = str(e)
        return state
```

### 3. Memory Management

✅ **Use automatic memory:**
```python
conversation_history: Annotated[list, create_memory_aware_reducer()]
```

✅ **Configure appropriate limits:**
```yaml
memory:
  max_messages: 50  # Adjust based on your needs
```

✅ **Use semantic search when relevant:**
```python
relevant = MemoryManager.search_memories(state, query="preferences")
```

### 4. Observability

✅ **Enable both OTEL and LangFuse:**
```yaml
observability:
  otel_enabled: true
  langfuse_enabled: true
```

✅ **Add custom spans for important operations:**
```python
with create_workflow_span("data_processing") as span:
    result = process_large_dataset()
    span.set_attribute("rows_processed", len(result))
```

### 5. Durability

✅ **Enable for production workflows:**
```python
runner = WorkflowRunner(enable_checkpointing=True)
```

✅ **Use meaningful session IDs:**
```python
session_id = f"user-{user_id}-{workflow_type}"
```

✅ **Enable auto-resume:**
```python
result = runner.run(..., auto_resume=True)
```

### 6. Error Handling

✅ **Use specific error types:**
```python
raise CheckpointSaveError("Failed to save", thread_id="123")
```

✅ **Add resilience to external calls:**
```python
@resilient(retry_config=RetryConfig(max_attempts=3))
async def call_api(): ...
```

✅ **Implement circuit breakers for unreliable services:**
```python
breaker = CircuitBreaker(name="payment_gateway")

@breaker.protected
def process_payment(): ...
```

---

## Next Steps

1. **Read the API Reference**: [docs/API_REFERENCE.md](API_REFERENCE.md)
2. **Check Troubleshooting**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **Explore Examples**: `examples/` directory
4. **Join the Community**: [GitHub Discussions](#)

---

## Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues
- **Health Check**: `bin/framework health`
- **Configuration**: `bin/framework config --validate`

