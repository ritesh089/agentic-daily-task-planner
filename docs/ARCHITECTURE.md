# Daily Task Planner Agent - System Architecture

## Overview

This is a **framework/application architecture** that separates cross-cutting concerns (observability) from business logic (agents and workflow). The system collects emails and Slack messages, extracts actionable tasks, prioritizes them, and delivers a daily todo list.

## Architecture Layers

### Framework Layer (Cross-Cutting Concerns)
```
framework/
├── observability.py    # OpenTelemetry instrumentation
├── durability.py       # PostgreSQL checkpointing
├── loader.py           # Dynamic application loading
├── setup_postgres.py   # Database setup helper
└── __init__.py         # Framework API
```

**Responsibilities:**
- OpenTelemetry tracing and metrics
- PostgreSQL-backed durable executions
- Auto-instrumentation of LangGraph workflows
- Automatic workflow resumption
- Dynamic application loading via `importlib`

### Application Layer (Business Logic)
```
app/
├── workflow.py         # LangGraph workflow definition
├── config.py           # Application configuration
├── agents/             # Agent implementations
│   ├── email_agents.py
│   ├── slack_agents.py
│   ├── task_agents.py
│   └── communication_agents.py
└── __init__.py         # Application API
```

**Responsibilities:**
- Define workflow structure
- Implement agent logic
- Manage application state

### Entry Point
```
main.py                 # Uses framework to load and run application
```

## How It Works

```
1. main.py
   └─> framework.loader.load_and_run_app('app.workflow', initial_state)
       │
       ├─> Initialize OTEL (framework concern)
       │
       ├─> Initialize Durability (PostgreSQL checkpointing)
       │   ├─> Connect to PostgreSQL
       │   ├─> Check for interrupted workflows
       │   └─> Resume if auto_resume enabled
       │
       ├─> importlib.import_module('app.workflow')
       │
       ├─> Call app.workflow.build_workflow()
       │   └─> Returns LangGraph workflow graph
       │
       ├─> Compile workflow with PostgreSQL checkpointer
       │   └─> Automatic state persistence at each node
       │
       ├─> Generate unique thread_id
       │
       └─> Execute workflow with:
           • Auto-instrumentation (OTEL)
           • Automatic checkpointing (PostgreSQL)
           • Resumption capability
```

## Agent Execution Flow

```
START
  │
  ├─→ [1] Email Collector Agent
  │     │ • Authenticate with Gmail
  │     │ • Fetch emails from time range
  │     │ • Store in state['emails']
  │     ↓
  ├─→ [2] Slack Collector Agent
  │     │ • Authenticate with Slack
  │     │ • Fetch DMs, channels, mentions
  │     │ • Store in state['slack_messages']
  │     ↓
  ├─→ [3] Task Extractor Agent
  │     │ • Read state['emails'] + state['slack_messages']
  │     │ • Call LLM to extract actionable tasks
  │     │ • Store in state['tasks']
  │     ↓
  ├─→ [4] Email Summarizer Agent
  │     │ • Read state['emails']
  │     │ • Call LLM for summary
  │     │ • Store in state['email_summary']
  │     ↓
  ├─→ [5] Slack Summarizer Agent
  │     │ • Read state['slack_messages']
  │     │ • Call LLM for summary
  │     │ • Store in state['slack_summary']
  │     ↓
  ├─→ [6] Task Prioritizer Agent
  │     │ • Read state['tasks']
  │     │ • Assign priorities (P0-P3)
  │     │ • Store in state['prioritized_tasks']
  │     ↓
  ├─→ [7] Email Sender Agent
  │     │ • Format todo list (plain text + HTML)
  │     │ • Send via Gmail API
  │     │ • Store in state['email_sent']
  │     ↓
  └─→ [8] Aggregator Agent
        │ • Combine all results
        │ • Format final output
        │ • Store in state['final_summary']
        ↓
END
```

## State Management

```python
class MultiAgentState(TypedDict):
    # Configuration
    time_range_hours: int
    
    # Email data
    emails: List[Dict[str, str]]
    email_summary: str
    
    # Slack data
    slack_messages: List[Dict[str, str]]
    slack_summary: str
    
    # Task data
    tasks: List[Dict[str, str]]
    prioritized_tasks: List[Dict[str, str]]
    
    # Communication status
    email_sent: bool
    email_status: str
    email_message_id: str
    
    # Output
    final_summary: str
    errors: List[str]
```

## The Contract

### Application Must Provide
```python
# app/workflow.py
def build_workflow():
    """Returns a compiled LangGraph workflow"""
    workflow = ObservableStateGraph(MultiAgentState)
    # ... add nodes and edges
    return workflow.compile()
```

### Framework Provides
- `ObservableStateGraph` - Auto-instrumenting StateGraph
- `init_observability()` - OTEL initialization
- `init_durability()` - PostgreSQL checkpointing
- `load_and_run_app()` - Dynamic app loader with auto-checkpoint & resume

## Design Principles

### 1. Separation of Concerns
- **Framework**: Cross-cutting concerns (OTEL)
- **Application**: Business logic (agents, workflow)
- **Entry Point**: Orchestration only

### 2. Loose Coupling
- Framework doesn't know about agents
- Application doesn't know about OTEL internals
- Communication via well-defined contract (`build_workflow()`)

### 3. Dynamic Loading
- Application loaded at runtime via `importlib.import_module()`
- No extension-based tight coupling
- Easy to swap different applications

### 4. Auto-Instrumentation
- `ObservableStateGraph` automatically instruments all nodes
- Zero boilerplate in agent code
- Controlled by configuration

## Configuration

### Framework Configuration
```yaml
# config/observability_config.yaml
enabled: true
service_name: "daily-task-planner-agent"
exporters:
  console: false
  otlp: true
otlp_endpoint: "http://localhost:4317"
```

### Application Configuration
```python
# app/config.py
def get_app_config():
    return {
        'service_name': 'daily-task-planner-agent',
        'service_version': '1.0.0',
        'default_time_range': 24
    }
```

## Running the Application

### Standard Run
```bash
python main.py
```

### With Runner Script (includes Ollama setup)
```bash
./run_multi_agent.sh
```

### With Tracing
```bash
./start_with_tracing.sh
```

## Benefits of This Architecture

✅ **Modularity**: Framework and app are completely independent

✅ **Reusability**: Framework can load any LangGraph application

✅ **Maintainability**: Changes to agents don't affect framework

✅ **Testability**: Each layer can be tested independently

✅ **Extensibility**: Easy to add new apps or framework features

✅ **Clean Separation**: No extension-based tight coupling

## Creating a New Application

```python
# my_app/workflow.py
from framework import ObservableStateGraph
from langgraph.graph import START, END

def build_workflow():
    workflow = ObservableStateGraph(MyState)
    workflow.add_node("my_agent", my_agent_function)
    workflow.add_edge(START, "my_agent")
    workflow.add_edge("my_agent", END)
    return workflow.compile()
```

```python
# main.py (updated)
from framework.loader import load_and_run_app
result = load_and_run_app('my_app.workflow', initial_state)
```

That's it! The framework handles all observability automatically.

## Observability Features

- **Distributed Tracing**: Track workflow execution across agents
- **Metrics Collection**: Count calls, duration, errors
- **Auto-Instrumentation**: Zero code changes in agents
- **Multiple Exporters**: Console, OTLP (Jaeger, Grafana)
- **Configurable**: Enable/disable via YAML

View traces at: http://localhost:16686 (when using Jaeger)

## Durable Executions

The framework provides **production-grade durable executions** backed by PostgreSQL.

### Key Features

**Automatic Checkpointing:**
- State saved at each node execution
- Full workflow state persisted
- No application code changes needed

**Automatic Resumption:**
- Detects interrupted workflows on startup
- Resumes from last checkpoint automatically
- Configurable via `config/durability_config.yaml`

**Thread-Based Isolation:**
- Each execution gets unique `thread_id`
- Format: `{service}-{timestamp}-{uuid}`
- Enables concurrent executions

### How It Works

```
1. Framework compiles workflow with PostgresSaver
   └─> workflow.compile(checkpointer=postgresql_saver)

2. Each node execution:
   └─> State automatically saved to PostgreSQL

3. On interruption (crash, kill, etc.):
   └─> Last checkpoint remains in database

4. On next startup:
   └─> Framework detects interrupted workflow
   └─> Resumes from last checkpoint
   └─> Continues execution seamlessly
```

### Configuration

```yaml
# config/durability_config.yaml
enabled: true
connection_string: "postgresql://localhost:5432/langgraph"

resume:
  auto_resume: true        # Auto-resume on startup
  max_age_hours: 24        # Only resume recent workflows

checkpoint:
  frequency: "each_node"   # Checkpoint at every node
  mode: "full_state"       # Store complete state
```

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL (Docker)
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=langgraph \
  -e POSTGRES_PASSWORD=postgres \
  postgres:16

# 3. Initialize database
python framework/setup_postgres.py

# 4. Run application (durability automatic!)
python main.py
```

### Benefits

✅ **Zero Application Changes** - Framework handles everything  
✅ **Production-Grade** - PostgreSQL ensures reliability  
✅ **Automatic Recovery** - Resumes interrupted workflows  
✅ **Observable** - Checkpoint info in OTEL traces  
✅ **Configurable** - Enable/disable per environment

See [INSTALL_DURABILITY.md](INSTALL_DURABILITY.md) for detailed setup instructions.

## Future Enhancements

- **Workflow Viewer**: Web UI to see checkpoints and resume manually
- **Cleanup Jobs**: Archive/delete old checkpoints automatically
- **Multi-Backend**: Support Redis, MongoDB for checkpointing
- **Partial Resume**: Resume specific failed nodes, not full workflow
- **More Sources**: Teams, Discord, Calendar agents
- **Advanced Features**: Sentiment analysis, action tracking
- **Parallel Execution**: Optimize with conditional edges
