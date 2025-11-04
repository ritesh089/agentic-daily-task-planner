# Daily Task Planner Agent

A LangGraph-based multi-agent system that collects and summarizes your emails and Slack messages, extracts actionable tasks, prioritizes them, and sends you a daily todo list using local LLM (Ollama).

## ✨ Key Features

- **Task Extraction & Prioritization**: Automatically extracts actionable tasks and assigns priorities (P0-P3)
- **Email Todo List Delivery**: Sends prioritized todo list via email with HTML formatting
- **Durable Executions**: PostgreSQL-backed checkpointing with automatic resumption
- **Mock Agents**: Test without real APIs, simulate failures for checkpoint testing ([Guide](MOCK_AGENTS_GUIDE.md))
- **OpenTelemetry Observability**: Distributed tracing and metrics with auto-instrumentation
- **Framework/App Architecture**: Clean separation of concerns with dynamic loading
- **Modular Design**: Easy to extend with new agents or applications

See [ARCHITECTURE.md](ARCHITECTURE.md) for architectural details.

## 🏗️ Architecture

This application uses a **framework/application architecture** that separates cross-cutting concerns (observability) from business logic (agents and workflow):

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│                      (Entry Point)                          │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ↓                 ↓
┌──────────────┐    ┌──────────────┐
│  framework/  │    │     app/     │
│              │    │              │
│• observ.py   │    │• workflow.py │
│  (OTEL)      │    │• config.py   │
│• loader.py   │    │• agents/     │
│  (Dynamic)   │    │  - email     │
└──────────────┘    │  - slack     │
                    │  - task      │
                    │  - comm      │
                    └──────────────┘
```

**Framework Layer**: Cross-cutting concerns (OpenTelemetry)
**Application Layer**: Business logic (agents + workflow)
**Entry Point**: Uses framework to dynamically load app

### Module Structure

```
daily-task-planner-agent/
├── main.py                       # Entry point
├── framework/                    # Cross-cutting concerns
│   ├── observability.py          # OTEL instrumentation
│   └── loader.py                 # Dynamic app loading
├── app/                          # Business logic
│   ├── workflow.py               # LangGraph workflow
│   ├── config.py                 # App configuration
│   └── agents/                   # Agent implementations
│       ├── email_agents.py       # Email collection & summarization
│       ├── slack_agents.py       # Slack collection & summarization
│       ├── task_agents.py        # Task extraction & prioritization
│       └── communication_agents.py  # Email sending
├── config/                       # Configuration files
│   └── observability_config.yaml # OTEL configuration
├── run_multi_agent.sh            # Multi-agent runner script
├── start_with_tracing.sh         # Run with tracing enabled
├── requirements.txt              # Python dependencies
├── credentials.json              # Gmail OAuth credentials (git-ignored)
├── slack_credentials.json        # Slack OAuth token (git-ignored)
├── ARCHITECTURE.md               # Architecture details
├── SETUP.md                      # Setup guide
└── SLACK_SETUP.md                # Slack setup guide
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.13+** with venv
2. **Ollama** with llama3.2 model
   ```bash
   brew install ollama
   ollama pull llama3.2
   ```
3. **PostgreSQL** (for durable executions) - See [INSTALL_DURABILITY.md](INSTALL_DURABILITY.md)
4. **Gmail API credentials** - See [Google Cloud Console](https://console.cloud.google.com/)
5. **Slack User Token** (optional) - See [SLACK_SETUP.md](SLACK_SETUP.md)

### Installation

```bash
# Clone/navigate to project
cd daily-task-planner-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup credentials
cp slack_credentials.json.example slack_credentials.json
# Edit slack_credentials.json with your token
```

### Running

#### Standard Run

```bash
python main.py
```

Or use the runner script (handles Ollama setup automatically):

```bash
./run_multi_agent.sh
```

This will:
- ✅ Start Ollama (if not running)
- ✅ Collect emails from last 24 hours
- ✅ Collect Slack messages (DMs, channels, mentions)
- ✅ Extract and prioritize tasks
- ✅ Send todo list via email
- ✅ Display formatted output
- ✅ Clean up automatically

#### With Distributed Tracing

```bash
./start_with_tracing.sh
```

Starts Jaeger and enables OpenTelemetry tracing. View traces at http://localhost:16686

## 📦 Modules

### Framework Layer

#### `framework/observability.py`
**Purpose**: OpenTelemetry instrumentation  
**Provides**: Tracing, metrics, auto-instrumentation via `ObservableStateGraph`

#### `framework/loader.py`
**Purpose**: Dynamic application loading  
**Provides**: `load_and_run_app()` - loads apps via `importlib`

### Application Layer

#### `app/workflow.py`
**Purpose**: LangGraph workflow definition  
**Provides**: `build_workflow()` - returns compiled workflow  
**Contains**: `MultiAgentState`, `aggregator_agent()`

#### `app/config.py`
**Purpose**: Application configuration  
**Provides**: `get_app_config()`, `get_initial_state()`

#### `app/agents/email_agents.py`

**Purpose**: Email operations

**Agents**:
1. **`email_collector_agent`**
   - Connects to Gmail API
   - Fetches emails within time range
   - Extracts sender, subject, body
   - Updates state with collected emails

2. **`email_summarizer_agent`**
   - Takes collected emails from state
   - Formats for LLM prompt
   - Generates concise summary
   - Updates state with summary

#### `app/agents/slack_agents.py`

**Purpose**: Slack operations

**Agents**:
1. **`slack_collector_agent`**
   - Connects to Slack API
   - Fetches DMs, channel messages, mentions
   - Handles multiple message types
   - Updates state with collected messages

2. **`slack_summarizer_agent`**
   - Takes collected messages from state
   - Formats for LLM prompt
   - Generates concise summary
   - Updates state with summary

#### `app/agents/task_agents.py`

**Purpose**: Task extraction and prioritization

**Agents**:
1. **`task_extractor_agent`**
   - Reads both emails and Slack messages from state
   - Uses LLM to identify actionable tasks
   - Extracts who requested each task
   - Identifies urgency indicators (deadlines, "urgent", "ASAP")
   - Returns structured JSON of tasks
   - Updates state with extracted tasks

2. **`task_prioritizer_agent`**
   - Takes extracted tasks from state
   - Uses LLM to assign priority levels:
     - **P0 (Critical)**: Urgent deadlines, blocks others, executive requests
     - **P1 (High)**: Important with deadlines this week
     - **P2 (Medium)**: Important but not urgent
     - **P3 (Low)**: Nice to have, no deadline
   - Estimates effort (Quick/Medium/Large)
   - Provides recommended actions
   - Updates state with prioritized tasks

#### `app/agents/communication_agents.py`

**Purpose**: Communication and notification delivery

**Agents**:
1. **`email_sender_agent`**
   - Takes prioritized tasks from state
   - Formats todo list in both plain text and HTML
   - Uses Gmail API to send email to your address
   - Creates beautiful, color-coded priority sections
   - Includes all task details (requester, action, effort, reasoning)
   - Updates state with send status
   - Handles errors gracefully (skips if no tasks)

## 🔧 Configuration

### Time Range

Edit `slack_credentials.json`:
```json
{
  "time_range_hours": 24   // Default: 24 hours
}
```

### Slack Channels

Add specific channels to monitor:
```json
{
  "user_token": "xoxp-...",
  "channels": [
    "C01234567",  // Channel ID
    "C98765432"
  ]
}
```

## 🔐 Security

All credentials are:
- ✅ **Git-ignored** (listed in `.gitignore`)
- ✅ **Local only** (never committed)
- ✅ **File-based** (no environment variables needed)

Protected files:
- `credentials.json` - Gmail OAuth credentials
- `slack_credentials.json` - Slack user token
- `token.json` - Gmail token cache

## 🎯 Extending the System

### Adding New Agents

1. **Create agent file** (e.g., `discord_agents.py`):
   ```python
   def discord_collector_agent(state: Dict) -> Dict:
       # Your logic here
       return state
   ```

2. **Update `multi_agent_summarizer.py`**:
   ```python
   from discord_agents import discord_collector_agent
   
   # Add to workflow
   workflow.add_node("discord_collector", discord_collector_agent)
   workflow.add_edge("slack_collector", "discord_collector")
   ```

3. **Update state definition**:
   ```python
   class MultiAgentState(TypedDict):
       # ... existing fields ...
       discord_messages: List[Dict[str, str]]
       discord_summary: str
   ```

### Parallel Execution

To run collectors in parallel, use conditional edges:
```python
from langgraph.graph import StateGraph, START, END

def route_to_summarizers(state):
    return ["email_summarizer", "slack_summarizer"]

workflow.add_conditional_edges(
    "collectors_done",
    route_to_summarizers
)
```

## 🐛 Troubleshooting

### No emails/messages found
- Check time range configuration
- Verify OAuth permissions
- Ensure credentials are valid

### LLM errors
```bash
# Check Ollama is running
ollama list

# Restart Ollama
killall ollama
ollama serve
```

### Import errors
```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## 📊 Output Format

```
================================================================================
📊 MULTI-AGENT COMMUNICATION SUMMARY
================================================================================

Time Range: Last 24 hours
Generated: 2025-11-03 14:30:00

================================================================================
🎯 PRIORITIZED TODO LIST (8 tasks)
================================================================================

🔴 CRITICAL (2 tasks):

  1. Review and approve Q4 budget proposal before EOD
     👤 Requested by: Sarah Chen (Email)
     📝 Action: Review attached spreadsheet and provide approval by 5 PM
     ⏱️  Effort: Medium (1-4h)
     💡 Why: Executive request with today's deadline

  2. Fix production bug causing checkout failures
     👤 Requested by: John Smith (Slack)
     📝 Action: Investigate error logs and deploy hotfix
     ⏱️  Effort: Large (> 4h)
     💡 Why: Blocking customer transactions, urgent priority

🟠 HIGH (3 tasks):

  1. Prepare presentation for Friday's client meeting
     👤 Requested by: Marketing Team (Email)
     📝 Action: Create slide deck with Q3 results
     ⏱️  Effort: Medium (1-4h)
     💡 Why: Important client meeting this week

  2. Code review for authentication feature PR
     👤 Requested by: Alice Johnson (Slack)
     📝 Action: Review pull request #1234 and provide feedback
     ⏱️  Effort: Quick (< 1h)
     💡 Why: Blocks team member's work

🟡 MEDIUM (2 tasks):

  1. Update documentation for API v2
     👤 Requested by: DevRel Team (Email)
     📝 Action: Add examples and update changelog
     ⏱️  Effort: Medium (1-4h)
     💡 Why: Important for developer experience

🟢 LOW (1 task):

  1. Review team building activity proposals
     👤 Requested by: HR (Slack)
     📝 Action: Vote on options by next week
     ⏱️  Effort: Quick (< 1h)
     💡 Why: No immediate deadline

================================================================================
📧 EMAIL SUMMARY (5 emails)
================================================================================

• Urgent budget approval needed from leadership
• Client meeting prep materials shared by marketing
• Documentation updates requested for API changes
• Financial notifications and account updates
• Promotional offers and subscription renewals

================================================================================
💬 SLACK SUMMARY (12 messages)
================================================================================

• Production bug reported by engineering team
• Code review requests pending in #dev-team
• Team standup updates in #engineering
• Client feedback discussion in #product
• Team building poll from HR

================================================================================
📨 COMMUNICATION STATUS
================================================================================

✓ Successfully sent to your-email@example.com

================================================================================
```

## 📊 Observability

The application includes full OpenTelemetry instrumentation for traces, metrics, and logs.

### View Traces in Jaeger (3 minutes)

```bash
# 1. Start Jaeger
docker-compose up -d

# 2. Enable OTLP in observability_config.yaml
#    Set: exporters.otlp = true

# 3. Run application
python multi_agent_summarizer.py

# 4. View traces at http://localhost:16686
```

See [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md) for details.

### Features
- ✅ **Automatic instrumentation** - Zero code changes needed
- ✅ **Distributed tracing** - See full workflow execution
- ✅ **Performance metrics** - Agent duration, message counts
- ✅ **Error tracking** - Detailed failure information
- ✅ **Configuration-driven** - Enable/disable without code changes

Full guide: [OBSERVABILITY_SETUP.md](OBSERVABILITY_SETUP.md)

## 📚 Additional Documentation

- [SLACK_SETUP.md](SLACK_SETUP.md) - Detailed Slack configuration guide
- [OBSERVABILITY_SETUP.md](OBSERVABILITY_SETUP.md) - Complete observability guide
- [QUICK_START_OBSERVABILITY.md](QUICK_START_OBSERVABILITY.md) - 3-minute trace viewing
- [AUTO_INSTRUMENTATION.md](AUTO_INSTRUMENTATION.md) - Auto-instrumentation details

## 🤝 Contributing

This is a personal project, but feel free to fork and customize for your needs!

## 📄 License

MIT License - Use freely!

