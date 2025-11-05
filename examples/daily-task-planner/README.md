# Daily Task Planner Agent

A multi-agent workflow built with the agentic framework that collects and summarizes your emails and Slack messages, extracts actionable tasks, prioritizes them, and sends you a daily todo list.

## Features

- **Email & Slack Collection**: Collects emails and Slack messages via MCP tool servers
- **Task Extraction**: Automatically extracts actionable tasks from communications
- **Priority Assignment**: Assigns priorities (P0-P3) based on urgency and content
- **Email Delivery**: Sends HTML-formatted prioritized todo list via email
- **Durable Executions**: PostgreSQL-backed checkpointing with automatic resumption

## Prerequisites

1. **Python 3.13+** with venv
2. **Ollama** with llama3.2 model
3. **Docker & Docker Compose** (for PostgreSQL and observability)
4. **Gmail API credentials** - See [Google Cloud Console](https://console.cloud.google.com/)
5. **Slack User Token** (optional) - See root `SLACK_SETUP.md`

## Quick Start

```bash
# Navigate to this example
cd examples/daily-task-planner

# Install dependencies (from project root)
pip install -r ../../requirements.txt

# Setup credentials
cp ../../slack_credentials.json.example slack_credentials.json
# Edit slack_credentials.json with your token

# Run with mock MCP servers (testing)
python main.py --mock

# Run with real MCP servers (production)
python main.py
```

## Configuration

All configuration files are in `config/`:

- `observability_config.yaml` - OpenTelemetry settings
- `durability_config.yaml` - PostgreSQL checkpointing settings  
- `mcp_config.yaml` - MCP server configuration
- `mock_config.yaml` - Mock agent configuration for testing

## Architecture

This example uses the following agents:

1. **Email Collector** (`email_agents.py`) - Collects emails via MCP
2. **Email Summarizer** (`email_agents.py`) - Summarizes collected emails
3. **Slack Collector** (`slack_agents.py`) - Collects Slack messages via MCP
4. **Slack Summarizer** (`slack_agents.py`) - Summarizes Slack messages
5. **Task Extractor** (`task_agents.py`) - Extracts actionable tasks
6. **Task Prioritizer** (`task_agents.py`) - Assigns priorities
7. **Email Sender** (`communication_agents.py`) - Sends todo list via MCP
8. **Aggregator** (`workflow.py`) - Compiles final output

## Workflow Graph

```
START
  ├─> email_collector
  ├─> slack_collector
  │   ├─> email_summarizer
  │   └─> slack_summarizer
  │       └─> task_extractor
  │           └─> task_prioritizer
  │               └─> email_sender
  │                   └─> aggregator
  │                       └─> END
```

## Custom Agents

See the framework documentation for creating custom agents:
- `../../docs/CREATE_WORKFLOW.md` - Step-by-step workflow creation guide
- `../../docs/FRAMEWORK_GUIDE.md` - Framework API reference

## Testing with Mocks

```bash
# Use mock MCP servers (no real API calls)
python main.py --mock

# Run durability tests
../../test_durability.sh
```

## Extending

To add new agents:

1. Create agent function in `app/agents/`
2. Add node to workflow in `app/workflow.py`
3. Update state definition if needed

See `../../docs/CREATE_WORKFLOW.md` for detailed instructions.

