# Agentic Workflow Framework

A **production-ready framework** for building multi-agent workflows with built-in **observability**, **durability**, and **MCP (Model Context Protocol)** integration.

## ✨ Framework Features

### Core Features
- **🔍 Dual Observability** ⭐ NEW: OTEL + LangFuse for complete visibility (zero code!)
  - **OTEL**: Application-level tracing (agents, workflows, state transitions)
  - **LangFuse**: LLM-specific tracing (prompts, responses, tokens, costs)
  - **Fully Automatic**: Global instrumentation - NO manual callbacks!
- **🧠 Conversation Memory** ⭐ Powered by [mem0](https://mem0.ai): Semantic search & smart management
- **🔧 MCP Architecture**: Clean agent/tool separation via Model Context Protocol
- **💾 Durable Executions**: PostgreSQL-backed checkpointing with auto-resumption
- **🎯 Observable State Graph**: Drop-in replacement for LangGraph with instrumentation
- **🧪 Mock MCP Servers**: Test without real APIs
- **🔌 Dynamic Loading**: Framework dynamically loads and executes your workflows
- **📦 Modular Design**: Reusable framework, multiple example workflows

### 🎉 NEW: Enhanced Framework (v2.0)
- **⚙️ Unified Configuration**: Single `FrameworkConfig` class with auto-detection
- **🛡️ Rich Error Handling**: Comprehensive error hierarchy with recovery hints
- **🔄 Resilience Patterns**: Built-in retry and circuit breaker decorators
- **♻️ Lifecycle Management**: Automatic component initialization and cleanup
- **🏥 Health Checks**: Comprehensive diagnostics for all framework components
- **🔧 CLI Tool**: Command-line interface for project management
- **✅ Unit Tests**: 60%+ test coverage with comprehensive test suite
- **📚 Enhanced Documentation**: API reference and troubleshooting guide

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Application                             │
│                   (examples/your-app/)                          │
│                                                                 │
│  app/workflow.py     - build_workflow() function               │
│  app/agents/         - Your agent implementations               │
│  config/             - App-specific configuration               │
│  main.py             - Entry point                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Framework (Reusable)                         │
│                                                                 │
│  Observability  │  Durability   │  MCP Client   │  Loader     │
│  • OTEL         │  • PostgreSQL │  • Servers    │  • Dynamic  │
│  • Tracing      │  • Checkpoints│  • Tools      │  • Execute  │
│  • Metrics      │  • Resume     │  • Discovery  │  • Cleanup  │
└─────────────────────────────────────────────────────────────────┘
```

## 📚 Documentation

### 🚀 Quick Start

- **[User Guide](docs/USER_GUIDE.md)** - Complete guide for building workflows with the framework
- **[Examples](examples/)** - Working examples for different use cases

### 📖 Reference Documentation

- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation with code examples
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### 🛠️ For Framework Developers

- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Architecture, design principles, and contribution guide

### 🔧 Tools

- **CLI Tool**: Run `bin/framework --help` for available commands
- **Health Check**: `bin/framework health` to verify your setup
- **Config Validation**: `bin/framework config --validate` to check configuration

## 🚀 Quick Start

### 🧠 New: Framework Memory Management (Powered by mem0)

The framework provides **conversation memory as a built-in feature**, powered by [mem0](https://mem0.ai) for semantic search and smart memory management:

```python
from framework import with_conversation_memory, MemoryManager

@with_conversation_memory(
    system_prompt="You are a helpful assistant",
    max_messages=50,
    auto_add_response=True  # Automatically adds responses!
)
def my_chat_agent(state):
    MemoryManager.add_user_message(state, state['user_query'])
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    state['assistant_response'] = response.content
    return state  # Framework handles memory, pruning, checkpointing!
```

**NEW: Semantic Memory Search**
```python
# Search past conversations semantically (powered by mem0)
relevant_memories = MemoryManager.search_memories(
    state, 
    query="user preferences about email summaries",
    limit=5
)
```

See `examples/conversational-assistant/` and `examples/memory-examples/` for complete examples.

### Prerequisites

1. **Python 3.13+** with venv
2. **Docker & Docker Compose** (for PostgreSQL and observability)
3. **Ollama** (if using LLM-based agents)

### Installation

```bash
# Clone repo
git clone <repo-url>
cd agentic-daily-task-planner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install framework dependencies
pip install -r requirements.txt

# Setup LangFuse environment (optional - for LLM observability)
# Generate secrets
openssl rand -base64 32  # Copy this for NEXTAUTH_SECRET
openssl rand -base64 32  # Copy this for SALT

# Create .env file
cp env.example .env
# Edit .env and paste the generated secrets

# Start infrastructure (PostgreSQL, Jaeger, LangFuse)
docker-compose up -d

# Wait for services to be healthy (takes ~30 seconds)
docker-compose ps

# Setup LangFuse API Keys (first time only):
# 1. Open http://localhost:3000
# 2. Create an account (any email/password works locally)
# 3. Go to Settings → API Keys → Create new key
# 4. Copy Public Key (pk-lf-...) and Secret Key (sk-lf-...)
# 5. Update .env file with your keys:
#    LANGFUSE_PUBLIC_KEY=pk-lf-...
#    LANGFUSE_SECRET_KEY=sk-lf-...
# 6. Export environment variables:
export $(cat .env | xargs)
```

### Verify Setup

```bash
# Check all services are running
docker-compose ps

# You should see (all healthy):
# ✅ daily-task-planner-postgres   - Database
# ✅ daily-task-planner-jaeger     - OTEL traces
# ✅ daily-task-planner-langfuse   - LLM observability

# Access UIs:
# - Jaeger (OTEL):   http://localhost:16686
# - LangFuse (LLM):  http://localhost:3000
# - pgAdmin (optional): http://localhost:5050
```

### Run an Example

```bash
# Daily Task Planner example
cd examples/daily-task-planner

# With mock servers (no real API calls)
python main.py --mock

# With real servers (requires credentials)
python main.py
```

## 📂 Project Structure

```
agentic-daily-task-planner/
├── framework/                   # Reusable framework
│   ├── observability.py         # OTEL integration
│   ├── durability.py            # PostgreSQL checkpointing
│   ├── mcp_client.py            # MCP client
│   ├── loader.py                # Dynamic app loading
│   └── observable_state_graph.py
│
├── mcp-servers/                 # Shared MCP tool servers
│   ├── email-server/            # Gmail MCP server
│   │   ├── server.py            # Real Gmail API
│   │   └── mock_server.py       # Mock for testing
│   └── slack-server/            # Slack MCP server
│       ├── server.py            # Real Slack API
│       └── mock_server.py       # Mock for testing
│
├── examples/                    # Example workflows
│   ├── daily-task-planner/      # Email/Slack task planner
│   │   ├── app/
│   │   │   ├── workflow.py
│   │   │   ├── config.py
│   │   │   └── agents/
│   │   ├── config/
│   │   ├── main.py
│   │   └── README.md
│   │
│   └── [your-workflow]/         # Add your own!
│
├── docs/                        # Documentation
│   ├── FRAMEWORK_GUIDE.md       # Framework usage
│   ├── CREATE_WORKFLOW.md       # Workflow creation tutorial
│   ├── MCP_ARCHITECTURE.md      # MCP details
│   ├── ARCHITECTURE.md          # Framework architecture
│   └── DURABILITY.md            # Checkpointing details
│
├── config/                      # Shared config templates
├── docker-compose.yml           # Infrastructure (PostgreSQL, Jaeger)
├── requirements.txt             # Framework dependencies
└── README.md                    # This file
```

## 🎯 Creating Your Own Workflow

### Option 1: Follow the Tutorial

See **[CREATE_WORKFLOW.md](docs/CREATE_WORKFLOW.md)** for a complete step-by-step guide to building a news summarizer workflow from scratch.

### Option 2: Quick Template

```bash
# Create your app structure
mkdir -p examples/your-workflow/app/agents
mkdir -p examples/your-workflow/config
cd examples/your-workflow
```

**1. Define your state** (`app/workflow.py`):

```python
from typing import TypedDict, List

class YourState(TypedDict):
    input_data: str
    result: str
    errors: List[str]
```

**2. Create agents** (`app/agents/your_agents.py`):

```python
def your_agent(state):
    print("🤖 Agent: Working...")
    state['result'] = process(state['input_data'])
    return state
```

**3. Build workflow** (`app/workflow.py`):

```python
from framework import ObservableStateGraph
from langgraph.graph import START, END

def build_workflow():
    workflow = ObservableStateGraph(YourState)
    workflow.add_node("agent", your_agent)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    return workflow
```

**4. Create entry point** (`main.py`):

```python
import os, sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework.loader import load_and_run_app
from app.config import get_initial_state

def main():
    result = load_and_run_app('app.workflow', get_initial_state())
    print(result['result'])

if __name__ == "__main__":
    main()
```

**5. Run it!**

```bash
python main.py
```

See full tutorial: **[CREATE_WORKFLOW.md](docs/CREATE_WORKFLOW.md)**

## 🔧 Framework API

### Core Components

#### 1. Observable State Graph

```python
from framework import ObservableStateGraph

# Drop-in replacement for StateGraph
# Automatically instruments all nodes with tracing
workflow = ObservableStateGraph(YourStateType)
```

#### 2. MCP Tool Calls

```python
from framework import run_async_tool_call

# Call MCP tools from your agents
result = run_async_tool_call(
    server_name="email",
    tool_name="send_email",
    arguments={"to": "user@example.com", "subject": "Hello"}
)
```

#### 3. Dynamic Loading

```python
from framework.loader import load_and_run_app

# Framework loads and executes your workflow
result = load_and_run_app(
    'app.workflow',           # Your module path
    initial_state,            # Your starting state
    use_mcp_mocks=False       # Use real or mock servers
)
```

### Framework Services

The framework automatically provides:

✅ **OpenTelemetry** - Every agent is traced  
✅ **PostgreSQL Checkpointing** - State saved after each node  
✅ **MCP Client** - Connected to tool servers  
✅ **Auto-resumption** - Interrupted workflows resume automatically  
✅ **Error Handling** - Graceful degradation  

## 📦 Example Workflows

### Daily Task Planner

**Location**: `examples/daily-task-planner/`

**Description**: Collects emails and Slack messages, extracts tasks, prioritizes them, and sends a daily todo list.

**Features**:
- Email collection via MCP
- Slack message collection via MCP  
- LLM-based task extraction
- Priority assignment (P0-P3)
- HTML email delivery
- Full durability support

**Run**:
```bash
cd examples/daily-task-planner
python main.py --mock
```

### [Add Your Workflow Here!]

See `docs/CREATE_WORKFLOW.md` to build your own.

## 🧪 Testing

### Test with Mock Servers

```bash
# Any workflow can use mocks
python main.py --mock
```

### Test Durability

```bash
# Framework provides durability testing
./test_durability.sh
```

### Unit Tests

```python
import pytest
from app.agents.your_agents import your_agent

def test_agent():
    state = {'input': 'test', 'errors': []}
    result = your_agent(state)
    assert result['output'] == 'expected'
```

## 🐳 Deployment

### Docker Compose

The framework includes PostgreSQL and Jaeger:

```bash
# Start infrastructure
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f jaeger
```

### Environment Variables

```bash
# PostgreSQL
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/langgraph

# OpenTelemetry
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=your-workflow
```

## 📊 Observability

### View Traces

1. Start Jaeger: `docker-compose up -d jaeger`
2. Run your workflow
3. Open: http://localhost:16686
4. Select your service
5. View traces with all agent spans!

### View Database

1. Start pgAdmin: `docker-compose up -d pgadmin`  
2. Open: http://localhost:5050
3. Login: `admin@admin.com` / `admin`
4. View checkpoints table

## 🛠️ MCP Tool Servers

The framework uses MCP for external service integration:

- **Email Server** (`mcp-servers/email-server/`) - Gmail operations
- **Slack Server** (`mcp-servers/slack-server/`) - Slack operations

### Create Your Own MCP Server

See `docs/MCP_ARCHITECTURE.md` for details on creating custom tool servers.

### Managing Servers

```bash
./mcp status         # Check server status
./mcp logs email     # View email server logs
./mcp logs slack     # View slack server logs
```

## 🤝 Contributing

We welcome contributions!

1. **New Examples** - Add workflows to `examples/`
2. **Framework Features** - Enhance `framework/`
3. **MCP Servers** - Add tool servers to `mcp-servers/`
4. **Documentation** - Improve guides in `docs/`

## 📖 Learn More

- **[Framework Guide](docs/FRAMEWORK_GUIDE.md)** - Complete framework reference
- **[Create Workflow](docs/CREATE_WORKFLOW.md)** - Step-by-step tutorial
- **[MCP Architecture](docs/MCP_ARCHITECTURE.md)** - MCP integration details
- **[Architecture](docs/ARCHITECTURE.md)** - Framework internals
- **[Durability](docs/DURABILITY.md)** - Checkpointing & resumption

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Workflow orchestration
- [Model Context Protocol](https://modelcontextprotocol.io/) - Tool server protocol
- [OpenTelemetry](https://opentelemetry.io/) - Observability
- [PostgreSQL](https://www.postgresql.org/) - Durable storage

---

**Ready to build your own agentic workflow?**  
Start with the tutorial: **[CREATE_WORKFLOW.md](docs/CREATE_WORKFLOW.md)** 🚀
