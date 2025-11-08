# Building Conversational AI Workflows

This guide shows you how to build **conversational AI workflows** using the framework - agents that interact with users through natural language, maintain context, and provide intelligent responses.

## What You'll Learn

- Creating conversational workflows with automatic memory management
- Using the framework's CLI and command handlers
- Integrating with MCP tools for data access
- Managing conversation state and flow
- Best practices for conversational AI

---

## Core Concepts

### Conversational Workflow Pattern

A conversational AI workflow typically has this structure:

1. **Initialization** - Set up conversation memory and system prompt
2. **Input Loop** - Get user queries interactively
3. **Context Retrieval** - Find relevant information (optional)
4. **Response Generation** - Use LLM to generate intelligent responses
5. **Display & Continue** - Show response and check if conversation continues

---

## Step 1: Create Your App Directory

```bash
# From project root
mkdir -p examples/my-conversational-agent/app/agents
mkdir -p examples/my-conversational-agent/config
cd examples/my-conversational-agent
```

---

## Step 2: Define Your Conversational State

Create `app/workflow.py`:

```python
"""
My Conversational Agent Workflow
"""

from typing import TypedDict, List, Dict, Annotated
from framework import (
    ObservableStateGraph,
    ConversationMemoryMixin,
    create_memory_aware_reducer,
    MemoryConfig
)

class MyConversationalState(ConversationMemoryMixin):
    """
    State for conversational workflow
    
    Inherits ConversationMemoryMixin which provides:
    - conversation_history: Managed automatically by framework
    - _memory_config: Configuration for memory management
    """
    
    # Your domain-specific data (loaded once, persists across conversation)
    # Examples: user_profile, documents, database_records, etc.
    domain_data: List[Dict[str, Any]]  # Your data here
    
    # Current conversation turn
    user_query: str
    assistant_response: str
    
    # Optional: Context/search results for current query
    relevant_context: List[Dict[str, Any]]
    
    # Conversation control
    continue_chat: bool
    turn_count: int
    
    # Error tracking
    errors: List[str]
```

**Key Points**:
- ✅ Inherit from `ConversationMemoryMixin` for automatic memory
- ✅ Add your domain-specific data fields
- ✅ Keep conversation state (query, response, continue flag)
- ✅ Always include `errors: List[str]`
- ✅ Memory is handled automatically by the framework!

---

## Step 3: Create Your Conversational Agents

Conversational workflows need 4 core agents. Create `app/agents/chat_agents.py`:

### 1. Initialization Agent

```python
"""
Conversational Chat Agents
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage


def init_conversation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize conversation with system prompt
    
    With automatic memory management:
    - Just return a SystemMessage
    - No MemoryManager calls needed!
    """
    
    # Create your system prompt - customize for your domain!
    system_prompt = """You are a helpful AI assistant.

Your capabilities:
- Answer questions clearly and helpfully
- Maintain context across the conversation
- Admit when you don't know something

Be conversational, helpful, and concise."""
    
    # Show startup message
    print("=" * 70)
    print("💬 Conversational Assistant Ready")
    print("=" * 70)
    print("\nAsk me anything! Type 'help' for available commands.\n")
    print("=" * 70)
    
    # AUTOMATIC MEMORY: Just return the SystemMessage!
    # The smart reducer handles adding it to conversation_history
    return {
        'conversation_history': [SystemMessage(content=system_prompt)]
    }
```

### 2. Input Handler Agent (with Framework Commands!)

```python
from framework import InteractiveCommandHandler

def get_user_input_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get user query interactively
    
    Uses framework's InteractiveCommandHandler for built-in commands:
    - status, export, help, exit are handled automatically!
    """
    
    try:
        query = input("\n👤 You: ").strip()
        
        # Let framework handle built-in commands automatically!
        if InteractiveCommandHandler.handle(query, state):
            return state  # Command handled
        
        # Regular query - process it
        state['user_query'] = query
        state['continue_chat'] = True
        state['turn_count'] = state.get('turn_count', 0) + 1
        
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Conversation interrupted. Goodbye!")
        state['continue_chat'] = False
        state['user_query'] = ''
    
    return state
```

### 3. Response Generation Agent

```python
from langchain_ollama import ChatOllama  # or any LLM
from langchain_core.messages import HumanMessage, AIMessage
from framework import to_langchain_messages

def generate_response_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate response using LLM
    
    AUTOMATIC MEMORY PATTERN:
    - Just work with LangChain messages directly
    - Return HumanMessage and AIMessage
    - Smart reducer handles pruning/summarization automatically!
    """
    
    print("   🤖 Generating response...")
    
    query = state.get('user_query', '')
    if not query:
        return state
    
    try:
        # Get current conversation history
        current_history = state.get('conversation_history', [])
        lc_messages = to_langchain_messages(current_history)
        
        # Add current user message
        lc_messages.append(HumanMessage(content=query))
        
        # Generate response with LLM
        llm = ChatOllama(model="llama3.2", temperature=0.7)
        response = llm.invoke(lc_messages)
        assistant_response = response.content
        
        # AUTOMATIC MEMORY: Just return the new messages!
        # The smart reducer will:
        # 1. Add them to conversation_history
        # 2. Check if pruning is needed
        # 3. Apply summarization if configured
        # All automatically!
        return {
            'conversation_history': [
                HumanMessage(content=query),
                AIMessage(content=assistant_response)
            ],
            'assistant_response': assistant_response
        }
        
    except Exception as e:
        error_msg = f"LLM error: {str(e)}"
        print(f"   ✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        return {
            'assistant_response': "Sorry, I encountered an error. Please try again."
        }
```

### 4. Display Agent

```python
def display_response_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Display the assistant's response
    """
    response = state.get('assistant_response', '')
    
    if response:
        print(f"\n🤖 Assistant: {response}")
    
    return state
```

**Key Benefits of This Pattern**:
- ✅ **Zero MemoryManager calls** - Framework handles everything
- ✅ **Built-in commands** - status, export, help, exit automatic
- ✅ **Automatic pruning** - Memory managed by smart reducer
- ✅ **Clean code** - Just pure LangChain message handling
- ✅ **10 lines instead of 80** for input handling!

---

## Optional: Add Data Loading Agent

If your conversational agent needs to access data (emails, documents, database, etc.), add a data loading agent:

```python
from framework import run_async_tool_call

def load_data_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load your domain data once at startup
    
    Examples:
    - Load user's emails via MCP
    - Load documents from database
    - Fetch user profile
    - Initialize search index
    """
    print("📥 Loading data...")
    
    try:
        # Example: Load via MCP
        result = run_async_tool_call(
            server_name="your-mcp-server",
            tool_name="fetch_data",
            arguments={"limit": 100}
        )
        
        if result.get('success'):
            data = result.get('data', [])
            state['domain_data'] = data
            print(f"✓ Loaded {len(data)} items")
        else:
            print(f"✗ Failed to load data")
            state['domain_data'] = []
    
    except Exception as e:
        print(f"✗ Error: {e}")
        state['domain_data'] = []
        state.setdefault('errors', []).append(str(e))
    
    return state
```

**Best Practices for All Agents**:
- Use `run_async_tool_call()` for MCP tools
- Always handle exceptions gracefully
- Add errors to `state['errors']`
- Print status messages for user feedback
- Provide fallback values
            state['digest_sent'] = False
            state['digest_status'] = f"Failed: {error_msg}"
            state.setdefault('errors', []).append(f"Email: {error_msg}")
            print(f"✗ Send failed: {error_msg}")
    
    except Exception as e:
        error_msg = f"Exception in sender: {str(e)}"
        state['digest_sent'] = False
        state['digest_status'] = error_msg
        state.setdefault('errors', []).append(error_msg)
        print(f"✗ {error_msg}")
    
    return state
```

---

## Step 4: Build the Workflow

Complete `app/workflow.py`:

```python
from framework import ObservableStateGraph
from langgraph.graph import START, END

from app.agents.news_agents import (
    news_collector_agent,
    news_summarizer_agent,
    digest_generator_agent
)
from app.agents.communication_agents import (
    email_sender_agent
)


def build_workflow():
    """
    Builds the news summarizer workflow
    
    Returns:
        Uncompiled workflow (framework will add checkpointer)
    """
    
    # Create workflow with automatic observability
    workflow = ObservableStateGraph(NewsSummarizerState)
    
    # Add nodes (each agent is auto-instrumented)
    workflow.add_node("collector", news_collector_agent)
    workflow.add_node("summarizer", news_summarizer_agent)
    workflow.add_node("digest", digest_generator_agent)
    workflow.add_node("sender", email_sender_agent)
    
    # Define flow
    workflow.add_edge(START, "collector")
    workflow.add_edge("collector", "summarizer")
    workflow.add_edge("summarizer", "digest")
    workflow.add_edge("digest", "sender")
    workflow.add_edge("sender", END)
    
    # Return UNCOMPILED (framework adds checkpointer)
    return workflow
```

**Workflow Graph**:
```
START → collector → summarizer → digest → sender → END
```

---

## Step 5: Create Configuration

### `app/config.py`

```python
"""
Application Configuration
"""

from typing import Dict, Any


def get_initial_state() -> Dict[str, Any]:
    """
    Initial state for news summarizer workflow
    """
    return {
        'num_articles': 10,
        'categories': ['tech', 'business'],
        'articles': [],
        'article_summaries': [],
        'daily_digest': '',
        'digest_sent': False,
        'digest_status': '',
        'errors': []
    }


def get_app_config() -> Dict[str, Any]:
    """
    App-specific configuration
    """
    return {
        'name': 'news-summarizer',
        'version': '1.0.0'
    }
```

### `config/observability_config.yaml`

```yaml
service_name: "news-summarizer"

exporters:
  console: true
  otlp:
    traces: true
    metrics: false
    endpoint: "http://localhost:4317"
```

### `config/durability_config.yaml`

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
  max_attempts: 3
```

### `config/mcp_config.yaml`

```yaml
use_mocks: false

servers:
  news:
    name: "news"
    tools:
      - name: "fetch_articles"
  
  email:
    name: "email"
    tools:
      - name: "send_email"
```

---

## Step 6: Create MCP Server (Optional)

If you need custom MCP tools, create `mcp-servers/news-server/`:

### `mcp-servers/news-server/server.py`

```python
#!/usr/bin/env python3
"""
News MCP Server
Provides news fetching tools
"""

import asyncio
import json
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


class NewsMCPServer:
    def __init__(self):
        self.server = Server("news-server")
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
    
    async def list_tools(self) -> List[Tool]:
        return [
            Tool(
                name="fetch_articles",
                description="Fetch news articles by category",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "News categories"
                        },
                        "limit": {
                            "type": "number",
                            "description": "Max articles to fetch"
                        }
                    }
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "fetch_articles":
            return await self._fetch_articles(arguments)
        raise ValueError(f"Unknown tool: {name}")
    
    async def _fetch_articles(self, args: Dict[str, Any]) -> List[TextContent]:
        # In real implementation, call news API
        # For now, return mock data
        articles = [
            {
                "title": "Breaking: New AI Model Released",
                "content": "A new state-of-the-art AI model...",
                "url": "https://example.com/article1",
                "source": "Tech News"
            }
        ]
        
        result = {
            "success": True,
            "articles": articles
        }
        
        return [TextContent(type="text", text=json.dumps(result))]
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    server = NewsMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
```

---

## Step 7: Create Entry Point (NEW! ⚡ FrameworkCLI)

### `main.py` - Simplified with FrameworkCLI

The framework now provides `FrameworkCLI` which eliminates boilerplate!

```python
#!/usr/bin/env python3
"""
News Summarizer - Main Entry Point
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework import FrameworkCLI
from app.config import get_initial_state


if __name__ == "__main__":
    # Create CLI - framework handles all boilerplate!
    cli = FrameworkCLI(
        title="News Summarizer",
        description="Collects news, summarizes articles, and sends daily digest",
        app_module='app.workflow'
    )
    
    # Add custom arguments
    cli.add_argument(
        '--categories',
        nargs='+',
        help='News categories (default: tech business)'
    )
    cli.add_argument(
        '--limit',
        type=int,
        help='Max articles (default: 10)'
    )
    
    # Custom initial state provider
    def initial_state_provider(args):
        state = get_initial_state()
        if args.categories:
            state['categories'] = args.categories
        if args.limit:
            state['num_articles'] = args.limit
        return state
    
    cli.add_initial_state_provider(initial_state_provider)
    
    # Run! Framework handles:
    # - Path setup
    # - Banner display  
    # - MCP initialization
    # - Error handling
    # - Session summary
    sys.exit(cli.run())
```

**What FrameworkCLI Provides:**
- ✅ Automatic `--mock` flag
- ✅ Automatic `--debug` flag
- ✅ Automatic `--resume` flag
- ✅ Pretty banner and summary
- ✅ Error handling
- ✅ Path setup
- ✅ Clean exit codes

**90 lines → 50 lines** and much cleaner!

### Alternative: Even Simpler (for basic cases)

```python
#!/usr/bin/env python3
from framework import run_framework_app
from app.config import get_initial_state

if __name__ == "__main__":
    exit(run_framework_app(
        title="News Summarizer",
        description="Collects and summarizes news",
        app_module='app.workflow',
        initial_state_provider=lambda args: get_initial_state()
    ))
```

**Just 10 lines!** Perfect for simple workflows.

---

## Step 8: Test Your Workflow

### Run with mocks

```bash
python main.py --mock
```

### Run with real servers

```bash
python main.py
```

### Custom parameters

```bash
python main.py --categories tech sports --limit 5
```

---

## Step 9: Add Tests

### `tests/test_workflow.py`

```python
import pytest
from app.config import get_initial_state
from app.agents.news_agents import news_collector_agent


def test_collector_with_mock_state():
    """Test collector handles empty results"""
    state = get_initial_state()
    
    # This would fail without MCP, but tests logic
    result = news_collector_agent(state)
    
    assert 'articles' in result
    assert isinstance(result['articles'], list)
    assert 'errors' in result


def test_initial_state_structure():
    """Test initial state has required fields"""
    state = get_initial_state()
    
    assert 'num_articles' in state
    assert 'categories' in state
    assert 'articles' in state
    assert 'errors' in state
    assert isinstance(state['errors'], list)
```

---

## For Conversational Workflows: InteractiveCommandHandler

If your workflow is conversational (interactive user input), use `InteractiveCommandHandler` to eliminate command boilerplate!

### Before (Manual Commands):

```python
def get_user_input_agent(state):
    query = input("\n👤 You: ").strip()
    
    # 60+ lines of command handling...
    if query.lower() == 'status':
        print("Status...")
        return state
    if query.lower() == 'export':
        print("Exporting...")
        return state
    if query.lower() in ['help', '?']:
        print("Help...")
        return state
    if query.lower() in ['exit', 'quit']:
        print("Goodbye...")
        state['continue_chat'] = False
        return state
    
    # Finally process query...
    state['user_query'] = query
    return state
```

### After (Automatic Commands):

```python
from framework import InteractiveCommandHandler

def get_user_input_agent(state):
    query = input("\n👤 You: ").strip()
    
    # Framework handles status, export, help, exit automatically!
    if InteractiveCommandHandler.handle(query, state):
        return state  # Command handled
    
    # Only handle regular queries
    state['user_query'] = query
    state['turn_count'] += 1
    return state
```

**Built-in Commands:**
- `status` - Show memory status
- `export` - Export conversation to JSON
- `help` / `?` - Show available commands
- `exit` / `quit` - End conversation with export option

**60+ lines → 10 lines!**

### Add Custom Commands

```python
# Register custom command globally
from framework import interactive_command

@interactive_command('debug')
def debug_handler(state):
    '''Show debug information'''
    print(f"State keys: {state.keys()}")
    print(f"Turn count: {state.get('turn_count', 0)}")

# Now 'debug' command is available in your conversational agent!
```

---

## Advanced Patterns

### Conditional Workflows

```python
def should_send_email(state):
    """Decide whether to send email"""
    return "send" if len(state['article_summaries']) > 0 else "skip"

workflow.add_conditional_edges(
    "digest",
    should_send_email,
    {
        "send": "sender",
        "skip": END
    }
)
```

### Parallel Processing

```python
# Collect from multiple sources in parallel
workflow.add_edge(START, "collector_tech")
workflow.add_edge(START, "collector_business")

# Join results
workflow.add_edge("collector_tech", "join")
workflow.add_edge("collector_business", "join")
workflow.add_edge("join", "summarizer")
```

### Error Handling

```python
def error_handler_agent(state):
    """Handle workflow errors"""
    if state.get('errors'):
        print(f"⚠️  {len(state['errors'])} error(s) occurred")
        for error in state['errors']:
            print(f"  • {error}")
        
        # Send error report
        state['error_reported'] = True
    
    return state

# Add at end of workflow
workflow.add_edge("sender", "error_handler")
workflow.add_edge("error_handler", END)
```

---

## Deployment Checklist

- [ ] All agents handle errors gracefully
- [ ] State type is complete and typed
- [ ] Configuration files are provided
- [ ] MCP servers are implemented (if custom)
- [ ] Tests are written
- [ ] README.md documents your workflow
- [ ] Entry point (`main.py`) is created
- [ ] Docker configurations are updated (if needed)

---

## Next Steps

1. **Add more agents** - Expand functionality
2. **Improve prompts** - Use LLMs for better summaries
3. **Add persistence** - Store results in database
4. **Create dashboard** - Visualize workflow execution
5. **Deploy** - Use docker-compose for production

## Getting Help

- Framework docs: `docs/FRAMEWORK_GUIDE.md`
- MCP architecture: `docs/MCP_ARCHITECTURE.md`
- Examples: `examples/` directory
- Issues: GitHub issues

---

**Congratulations!** You've built a complete multi-agent workflow using the framework! 🎉

