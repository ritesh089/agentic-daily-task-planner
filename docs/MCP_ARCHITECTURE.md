# MCP Architecture

## Overview

The Daily Task Planner Agent is built entirely on **Model Context Protocol (MCP)**, providing a clean separation between agents and external APIs. All agents communicate with Gmail and Slack exclusively through MCP tool servers.

## What is MCP?

MCP (Model Context Protocol) is a protocol for exposing external services as **tools** that AI agents can discover and use. Instead of agents directly calling APIs, they request tools from MCP servers, which handle the actual API interactions.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │ Email Agent   │  │ Slack Agent   │  │ Sender Agent     │   │
│  │ (Collector)   │  │ (Collector)   │  │ (Email Sender)   │   │
│  └───────┬───────┘  └───────┬───────┘  └────────┬─────────┘   │
│          │                  │                    │             │
│          └──────────────────┴────────────────────┘             │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  MCP Client     │
                    │  (Framework)    │
                    └────────┬────────┘
                             │
            ┌────────────────┴────────────────┐
            │                                 │
    ┌───────▼────────┐            ┌──────────▼─────────┐
    │ Email MCP      │            │ Slack MCP          │
    │ Server         │            │ Server             │
    │                │            │                    │
    │ Tools:         │            │ Tools:             │
    │ - collect_     │            │ - collect_         │
    │   emails       │            │   messages         │
    │ - send_email   │            │                    │
    └────────┬───────┘            └──────────┬─────────┘
             │                               │
    ┌────────▼────────┐            ┌─────────▼────────┐
    │  Gmail API      │            │  Slack API       │
    └─────────────────┘            └──────────────────┘
```

## Key Components

### 1. MCP Servers

Located in `mcp-servers/`, each server exposes specific tools:

#### Email Server (`mcp-servers/email-server/`)
- **Tool: `collect_emails`** - Fetches emails from Gmail
- **Tool: `send_email`** - Sends emails via Gmail
- **Runs as:** Standalone Python process (stdio protocol)

#### Slack Server (`mcp-servers/slack-server/`)
- **Tool: `collect_messages`** - Collects Slack DMs, channels, mentions
- **Runs as:** Standalone Python process (stdio protocol)

Each server has both a **real** (`server.py`) and **mock** (`mock_server.py`) version for testing.

### 2. MCP Client (Framework)

Located in `framework/mcp_client.py`, provides:

- **Connection Management** - Connects to MCP servers via stdio
- **Tool Discovery** - Lists available tools from each server
- **Tool Execution** - Calls tools with parameters and returns results
- **Session Management** - Maintains sessions for each server
- **Lifecycle Management** - Starts/stops connections automatically

### 3. MCP-Based Agents

Located in `app/agents/*_mcp.py`, these are refactored agents that use MCP tools instead of direct API calls:

```python
# Old approach (direct API call)
def email_collector_agent(state):
    service = authenticate_gmail()
    results = service.users().messages().list(...).execute()
    # ...

# New approach (MCP tool call)
def email_collector_agent(state):
    result = run_async_tool_call(
        server_name="email",
        tool_name="collect_emails",
        arguments={"hours": 24}
    )
    # ...
```

## How It Works

### 1. Framework Initialization

When `main.py` starts, MCP is always initialized:

```python
# main.py
result = load_and_run_app(
    'app.workflow',
    initial_state,
    use_mcp_mocks=False  # True for testing, False for production
)
```

### 2. MCP Client Startup

The framework loader always initializes the MCP client:

```python
# framework/loader.py
mcp_client = asyncio.run(init_mcp_client(use_mocks=use_mcp_mocks))
```

This:
1. Creates an `MCPClient` instance
2. Spawns MCP server processes (email and slack)
3. Establishes stdio connections
4. Lists available tools from each server

### 3. Agent Tool Calls

When an agent needs data:

```python
# app/agents/email_agents_mcp.py
result = run_async_tool_call(
    server_name="email",
    tool_name="collect_emails",
    arguments={"hours": 24, "max_results": 50}
)

if result.get('success'):
    emails = result.get('emails', [])
```

The `run_async_tool_call` helper:
1. Gets the MCP client from the manager
2. Calls `client.call_tool(server_name, tool_name, arguments)`
3. Returns the parsed JSON result

### 4. MCP Server Processing

The MCP server (e.g., `email-server/server.py`):
1. Receives the tool call via stdio
2. Executes the Gmail API calls
3. Returns results as JSON via stdio

### 5. Framework Cleanup

After workflow completes, the framework:
1. Shuts down all MCP client connections
2. Terminates MCP server processes

## Configuration

### MCP Configuration (`config/mcp_config.yaml`)

```yaml
use_mocks: false        # Use mock servers (for testing)

servers:
  email:
    name: "email"
    tools:
      - name: "collect_emails"
      - name: "send_email"
  
  slack:
    name: "slack"
    tools:
      - name: "collect_messages"
```

### CLI Usage

```bash
# Production: Use real MCP servers
python main.py

# Testing: Use mock MCP servers
python main.py --mock
```

### MCP CLI Tool

The `./mcp` script provides server management:

```bash
./mcp start          # Start real MCP servers
./mcp start --mock   # Start mock MCP servers
./mcp status         # Check server status
./mcp stop           # Stop all servers
./mcp logs email     # View email server logs
./mcp config         # Show MCP configuration
```

## Benefits of MCP Architecture

### 1. **Decoupling**
- Agents don't know about API authentication, rate limits, etc.
- API logic is centralized in MCP servers
- Easy to swap implementations (real vs mock)

### 2. **Testability**
- Mock servers simulate API responses without real API calls
- Fast, deterministic tests
- No need for API credentials in CI/CD

### 3. **Flexibility**
- Switch between direct and MCP mode with a flag
- Add new tools without changing agent code
- Tools can be reused across multiple agents

### 4. **Security**
- Credentials stay in MCP server processes
- Framework and agents never see raw credentials
- Better secrets management

### 5. **Observability**
- MCP tool calls are traced independently
- Clear separation of concerns in traces
- Tool performance can be monitored separately

## Architecture Benefits

This is an **MCP-only** architecture - no dual-mode switching:

- Simpler codebase - one way to do things
- Always get MCP benefits (security, testability, observability)
- Mock vs real is controlled at the MCP server level, not agent level

## File Structure

```
mcp-servers/
├── email-server/
│   ├── server.py           # Real Gmail MCP server
│   ├── mock_server.py      # Mock Gmail MCP server
│   ├── requirements.txt    # MCP + Gmail dependencies
│   └── Dockerfile          # Container for MCP server
├── slack-server/
│   ├── server.py           # Real Slack MCP server
│   ├── mock_server.py      # Mock Slack MCP server
│   ├── requirements.txt    # MCP + Slack dependencies
│   └── Dockerfile          # Container for MCP server

framework/
├── mcp_client.py           # MCP client implementation

app/agents/
├── email_agents.py         # MCP-based email agents
├── slack_agents.py         # MCP-based slack agents
├── communication_agents.py # MCP-based email sender
├── task_agents.py          # Task extraction & prioritization

config/
├── mcp_config.yaml         # MCP configuration

mcp                         # CLI tool for managing MCP servers
```

## Debugging MCP

### View Server Logs

```bash
# Email server logs
tail -f logs/mcp-email.log

# Slack server logs
tail -f logs/mcp-slack.log
```

### Check Server Status

```bash
./mcp status
```

### Test with Mocks

```bash
# Use mock servers for testing
python main.py --mcp-mocks
```

### Manual Server Start (for debugging)

```bash
# Start email server manually (real)
python mcp-servers/email-server/server.py

# Start email server manually (mock)
python mcp-servers/email-server/mock_server.py
```

## Future Enhancements

1. **Tool Discovery UI** - Web UI to browse available tools
2. **Tool Versioning** - Version MCP tools independently
3. **Multi-tenancy** - Multiple MCP clients with different credentials
4. **Rate Limiting** - Built-in rate limiting at MCP server level
5. **Caching** - Cache tool results in MCP servers
6. **Observability** - Dedicated MCP tool metrics and traces

## References

- [MCP Specification](https://github.com/anthropics/mcp)
- [MCP Python SDK](https://github.com/anthropics/mcp-python-sdk)
- Framework documentation: `ARCHITECTURE.md`
- Durability documentation: `DURABILITY.md`

