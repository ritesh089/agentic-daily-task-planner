# Framework User Guide

## Overview

This is a **production-ready framework** for building multi-agent workflows with built-in observability, durability, MCP (Model Context Protocol) integration, and **conversation memory management**.

## Framework Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Application                         │
│                    (examples/your-app/)                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  app/workflow.py                                      │  │
│  │  • build_workflow() → Returns LangGraph workflow      │  │
│  │                                                        │  │
│  │  app/agents/                                          │  │
│  │  • Your agent functions                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                      Framework Layer                         │
│               (framework/ - reusable across apps)            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Observability│  │  Durability  │  │  MCP Client  │     │
│  │              │  │              │  │              │     │
│  │ • OTEL       │  │ • PostgreSQL │  │ • Tool Servers│    │
│  │ • Tracing    │  │ • Checkpoints│  │ • Connections│     │
│  │ • Metrics    │  │ • Resume     │  │ • Discovery  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────────────────────────┐   │
│  │   Memory     │  │  loader.py                        │   │
│  │              │  │  Dynamic app loading & execution  │   │
│  │ • Auto-mgmt  │  └───────────────────────────────────┘   │
│  │ • Pruning    │                                           │
│  │ • Decorators │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Framework Loader (`framework/loader.py`)

**Purpose**: Dynamically loads and executes your application

**Key Function**:
```python
def load_and_run_app(
    app_module_path: str,
    initial_state: Dict[str, Any],
    use_mcp_mocks: bool = False
) -> Dict[str, Any]:
    """
    Loads your app and executes it with framework services
    """
```

**What it does**:
1. Initializes observability (OpenTelemetry)
2. Initializes MCP client and connects to tool servers
3. Initializes durability (PostgreSQL checkpointing)
4. Dynamically imports your `app.workflow` module
5. Calls your `build_workflow()` function
6. Compiles workflow with checkpointer
7. Executes workflow with initial state
8. Handles cleanup

### 2. Observability (`framework/observability.py`)

**Purpose**: Automatic tracing and metrics for all agents

**Key Components**:
- `ObservableStateGraph` - Drop-in replacement for LangGraph's `StateGraph`
- Automatic span creation for every node
- Metrics collection
- Jaeger/OTLP export

**Usage in your app**:
```python
from framework import ObservableStateGraph

# Use instead of StateGraph - everything else is the same!
workflow = ObservableStateGraph(YourStateType)
workflow.add_node("agent1", agent1_func)
```

**Configuration**: `config/observability_config.yaml`

### 3. Durability (`framework/durability.py`)

**Purpose**: PostgreSQL-backed checkpointing for fault tolerance

**Features**:
- Automatic checkpoint creation after each node
- Workflow resumption after crashes
- Thread-based execution tracking
- Interrupt detection and recovery

**How it works**:
- Framework compiles your workflow with `PostgresSaver`
- LangGraph automatically saves state after each node
- On restart, framework detects interrupted workflows and resumes them
- Uses `thread_id` to track individual workflow executions

**Configuration**: `config/durability_config.yaml`

### 4. MCP Client (`framework/mcp_client.py`)

**Purpose**: Connect agents to external services via MCP tool servers

**Features**:
- Automatic server connection management
- Tool discovery and invocation
- Support for real and mock servers
- Helper functions for synchronous tool calls

**Key Functions**:
```python
from framework import run_async_tool_call

# Call an MCP tool from your agent
result = run_async_tool_call(
    server_name="email",
    tool_name="collect_emails",
    arguments={"hours": 24}
)
```

**Configuration**: `config/mcp_config.yaml`

### 5. Memory Management (`framework/memory.py`)

**Purpose**: Built-in conversation memory for interactive workflows

**Features**:
- Automatic conversation history management
- Memory pruning (prevents context overflow)
- LangChain message conversion
- Decorators for zero-config memory

**Key Components**:

#### ConversationMemoryMixin

Base class that provides memory to your state:

```python
from framework import ConversationMemoryMixin

class MyState(ConversationMemoryMixin):
    # conversation_history automatically available!
    my_field: str
```

#### MemoryManager

Utility class for memory operations:

```python
from framework import MemoryManager

# Initialize
MemoryManager.init_conversation(state, "You are a helpful assistant")

# Add messages
MemoryManager.add_user_message(state, "Hello!")
MemoryManager.add_assistant_message(state, "Hi there!")

# Get LangChain messages
messages = MemoryManager.get_langchain_messages(state)

# Auto-pruning (happens automatically)
MemoryManager.prune_if_needed(state)
```

#### @with_conversation_memory Decorator

**Advanced auto-memory decorator** - memory is completely automatic:

```python
from framework import with_conversation_memory, MemoryManager

@with_conversation_memory(
    system_prompt="You are a helpful assistant",
    max_messages=50,
    auto_add_response=True  # Automatically adds assistant_response!
)
def my_chat_agent(state):
    # Memory initialization - automatic!
    # Memory pruning - automatic!
    # Response adding - automatic!
    
    MemoryManager.add_user_message(state, state['user_query'])
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    state['assistant_response'] = response.content
    return state  # Framework handles the rest!
```

**Benefits**:
- Zero manual memory management
- Automatic pruning prevents context overflow
- Framework checkpoints memory (durable conversations!)
- Standard interface across all workflows

## Application Requirements

Your application must provide:

### 1. Workflow Module (`app/workflow.py`)

Must export a `build_workflow()` function:

```python
from framework import ObservableStateGraph
from langgraph.graph import START, END

def build_workflow():
    """
    Build and return your LangGraph workflow
    
    Returns:
        Uncompiled workflow (framework will compile with checkpointer)
    """
    workflow = ObservableStateGraph(YourStateType)
    
    # Add nodes
    workflow.add_node("agent1", agent1_func)
    workflow.add_node("agent2", agent2_func)
    
    # Add edges
    workflow.add_edge(START, "agent1")
    workflow.add_edge("agent1", "agent2")
    workflow.add_edge("agent2", END)
    
    # Return UNCOMPILED workflow
    return workflow
```

**Important**: Return the uncompiled workflow! The framework will compile it with the checkpointer.

### 2. Config Module (`app/config.py`)

Provide initial state and configuration:

```python
from typing import Dict, Any

def get_initial_state() -> Dict[str, Any]:
    """
    Return initial state for your workflow
    """
    return {
        'param1': value1,
        'param2': value2,
        # ... your state fields
    }

def get_app_config() -> Dict[str, Any]:
    """
    Optional: Return app-specific configuration
    """
    return {
        'setting1': value1,
        # ... your settings
    }
```

### 3. State Definition

Define your state type:

```python
from typing import TypedDict, List

class YourStateType(TypedDict):
    """
    Your workflow state
    All agents receive and return this state
    """
    # Input fields
    input_data: str
    
    # Processing fields
    intermediate_result: str
    
    # Output fields
    final_result: str
    
    # Error tracking
    errors: List[str]
```

### 4. Agent Functions

Create agent functions that follow this signature:

```python
from typing import Dict, Any

def your_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Your agent implementation
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state (can modify in place or return new dict)
    """
    print("🤖 Agent: Doing work...")
    
    # Do your work
    result = process(state['input_data'])
    
    # Update state
    state['intermediate_result'] = result
    
    # Return state
    return state
```

**Best Practices**:
- Print status messages for visibility
- Handle errors gracefully
- Add errors to `state['errors']` list
- Always return the state

## Using MCP Tools in Agents

If your agents need to call external APIs, use MCP tool servers:

### 1. Define your MCP server

See `mcp-servers/` for examples. Each server exposes tools:

```python
# mcp-servers/your-server/server.py
from mcp.server import Server
from mcp.types import Tool, TextContent

class YourMCPServer:
    async def list_tools(self) -> List[Tool]:
        return [
            Tool(
                name="your_tool",
                description="What your tool does",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"}
                    }
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Dict) -> List[TextContent]:
        if name == "your_tool":
            # Do the work
            result = do_something(arguments['param1'])
            return [TextContent(
                type="text",
                text=json.dumps(result)
            )]
```

### 2. Call tools from agents

```python
from framework import run_async_tool_call

def your_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # Call MCP tool
    result = run_async_tool_call(
        server_name="your-server",
        tool_name="your_tool",
        arguments={"param1": "value"}
    )
    
    if result.get('success'):
        state['data'] = result['data']
    else:
        state['errors'].append(result.get('error'))
    
    return state
```

## Configuration Files

Your app should provide these configs in `config/`:

### `observability_config.yaml`
```yaml
service_name: "your-app"
exporters:
  console: true
  otlp:
    traces: true
    metrics: false
```

### `durability_config.yaml`
```yaml
enabled: true
database:
  host: "localhost"
  port: 5432
  database: "langgraph"
  user: "postgres"
  password: "postgres"
resume:
  auto_resume: true
```

### `mcp_config.yaml`
```yaml
use_mocks: false
servers:
  your-server:
    name: "your-server"
    tools:
      - name: "your_tool"
```

## Main Entry Point

Create a `main.py` for your app:

```python
#!/usr/bin/env python3
import os
import sys
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework.loader import load_and_run_app
from app.config import get_initial_state

def main():
    parser = argparse.ArgumentParser(description='Your App')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock MCP servers')
    args = parser.parse_args()
    
    print("🚀 Starting Your App...\n")
    
    initial_state = get_initial_state()
    
    result = load_and_run_app(
        'app.workflow',
        initial_state,
        use_mcp_mocks=args.mock
    )
    
    print(result['final_result'])
    print("\n✅ Completed!\n")

if __name__ == "__main__":
    main()
```

## Testing

### Unit Testing Agents

```python
def test_your_agent():
    state = {
        'input_data': 'test',
        'errors': []
    }
    
    result = your_agent(state)
    
    assert result['intermediate_result'] == 'expected'
    assert len(result['errors']) == 0
```

### Integration Testing with Mocks

```bash
# Run with mock MCP servers
python main.py --mock
```

### Testing Durability

The framework provides tools to test checkpoint/resume:

```bash
# Simulate interruption and resumption
../../test_durability.sh
```

## Deployment

### Dependencies

Your app inherits all framework dependencies. Add app-specific ones to a local `requirements.txt`:

```txt
# App-specific dependencies
your-library==1.0.0
```

Install with:
```bash
pip install -r ../../requirements.txt  # Framework deps
pip install -r requirements.txt         # App deps
```

### Docker

The framework provides base docker-compose for PostgreSQL and observability. Extend for your app:

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  your-app:
    build: .
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/langgraph
    depends_on:
      - postgres
```

### Environment Variables

Configure via environment:
- `DATABASE_URL` - PostgreSQL connection string
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OTLP collector endpoint
- `OTEL_SERVICE_NAME` - Service name for traces

## Advanced Features

### Custom Observability

Add custom spans and metrics:

```python
from framework import create_workflow_span, log_event

def your_agent(state):
    with create_workflow_span("custom_operation") as span:
        span.set_attribute("custom.metric", value)
        result = do_work()
    
    log_event("custom_event", {"data": "value"})
    return state
```

### Conditional Workflow Edges

Use LangGraph's conditional edges:

```python
def route_decision(state):
    if state['condition']:
        return "path_a"
    else:
        return "path_b"

workflow.add_conditional_edges(
    "decision_node",
    route_decision,
    {
        "path_a": "agent_a",
        "path_b": "agent_b"
    }
)
```

### Parallel Execution

```python
from langgraph.graph import START

# Both run in parallel
workflow.add_edge(START, "agent1")
workflow.add_edge(START, "agent2")

# Join after both complete
workflow.add_edge("agent1", "join")
workflow.add_edge("agent2", "join")
```

## Troubleshooting

### MCP Connection Issues

```bash
# Check MCP server status
../../mcp status

# View server logs
../../mcp logs your-server
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker-compose ps postgres

# View logs
docker-compose logs postgres
```

### Import Errors

Make sure project root is in `sys.path`:
```python
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
```

## Next Steps

- Read `CREATE_WORKFLOW.md` for step-by-step workflow creation
- See `examples/` for complete working examples
- Explore `MCP_ARCHITECTURE.md` for MCP details

