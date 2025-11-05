# Create Your First Agentic Workflow

This guide walks you through creating a complete multi-agent workflow from scratch using the framework.

## Example: News Summarizer

We'll build a "News Summarizer" that:
1. Collects news articles via MCP
2. Summarizes each article
3. Generates a daily digest
4. Sends the digest via email

---

## Step 1: Create Your App Directory

```bash
# From project root
mkdir -p examples/news-summarizer/app/agents
mkdir -p examples/news-summarizer/config
cd examples/news-summarizer
```

---

## Step 2: Define Your State

Create `app/workflow.py`:

```python
"""
News Summarizer Workflow
"""

from typing import TypedDict, List, Dict
from datetime import datetime

class NewsSummarizerState(TypedDict):
    """State for news summarizer workflow"""
    
    # Configuration
    num_articles: int
    categories: List[str]  # e.g., ["tech", "business"]
    
    # Collected data
    articles: List[Dict[str, str]]  # [{title, content, url, source}]
    
    # Processed data
    article_summaries: List[Dict[str, str]]  # [{title, summary, url}]
    daily_digest: str
    
    # Communication
    digest_sent: bool
    digest_status: str
    
    # Error tracking
    errors: List[str]
```

**Key Points**:
- Use `TypedDict` for type safety
- Separate input, processing, and output fields
- Always include `errors: List[str]`

---

## Step 3: Create Your Agents

### News Collector Agent

Create `app/agents/news_agents.py`:

```python
"""
News Collection and Summarization Agents
"""

from typing import Dict, Any
from framework import run_async_tool_call


def news_collector_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collects news articles via MCP news server
    """
    print("📰 News Collector: Fetching articles...")
    
    try:
        result = run_async_tool_call(
            server_name="news",
            tool_name="fetch_articles",
            arguments={
                "categories": state.get('categories', ['tech']),
                "limit": state.get('num_articles', 10)
            }
        )
        
        if result.get('success'):
            articles = result.get('articles', [])
            state['articles'] = articles
            print(f"✓ Collected {len(articles)} articles")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"✗ Collection failed: {error_msg}")
            state.setdefault('errors', []).append(f"Collection: {error_msg}")
            state['articles'] = []
    
    except Exception as e:
        error_msg = f"Exception in collector: {str(e)}"
        print(f"✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        state['articles'] = []
    
    return state


def news_summarizer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarizes each collected article
    """
    print("🤖 News Summarizer: Processing articles...")
    
    articles = state.get('articles', [])
    
    if not articles:
        print("ℹ️  No articles to summarize")
        state['article_summaries'] = []
        return state
    
    summaries = []
    for article in articles:
        # In real implementation, use LLM to summarize
        # For now, simple truncation
        summary = {
            'title': article.get('title', 'Untitled'),
            'summary': article.get('content', '')[:200] + '...',
            'url': article.get('url', ''),
            'source': article.get('source', 'Unknown')
        }
        summaries.append(summary)
    
    state['article_summaries'] = summaries
    print(f"✓ Summarized {len(summaries)} articles")
    
    return state
```

**Best Practices**:
- Use `run_async_tool_call()` for MCP tools
- Always handle exceptions
- Add errors to `state['errors']`
- Print status messages
- Provide fallback values

### Digest Generator Agent

Add to `app/agents/news_agents.py`:

```python
def digest_generator_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates formatted daily digest
    """
    print("📝 Digest Generator: Creating daily digest...")
    
    summaries = state.get('article_summaries', [])
    
    if not summaries:
        state['daily_digest'] = "No articles found for today."
        return state
    
    # Format digest
    digest_lines = [
        "=" * 70,
        "📰 YOUR DAILY NEWS DIGEST",
        "=" * 70,
        f"\nDate: {datetime.now().strftime('%B %d, %Y')}",
        f"Articles: {len(summaries)}\n",
        "=" * 70
    ]
    
    for i, summary in enumerate(summaries, 1):
        digest_lines.append(f"\n{i}. {summary['title']}")
        digest_lines.append(f"   Source: {summary['source']}")
        digest_lines.append(f"   {summary['summary']}")
        digest_lines.append(f"   Read more: {summary['url']}\n")
    
    digest_lines.append("=" * 70)
    
    state['daily_digest'] = '\n'.join(digest_lines)
    print(f"✓ Digest created with {len(summaries)} articles")
    
    return state
```

### Email Sender Agent

Create `app/agents/communication_agents.py`:

```python
"""
Communication Agents
"""

from typing import Dict, Any
from framework import run_async_tool_call


def email_sender_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends digest via email using MCP
    """
    print("📨 Email Sender: Sending digest...")
    
    digest = state.get('daily_digest', '')
    
    if not digest:
        print("ℹ️  No digest to send")
        state['digest_sent'] = False
        state['digest_status'] = "No digest available"
        return state
    
    try:
        result = run_async_tool_call(
            server_name="email",
            tool_name="send_email",
            arguments={
                "to": "you@example.com",
                "subject": "📰 Your Daily News Digest",
                "body_text": digest
            }
        )
        
        if result.get('success'):
            state['digest_sent'] = True
            state['digest_status'] = "Digest sent successfully"
            print("✓ Digest sent")
        else:
            error_msg = result.get('error', 'Unknown error')
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

## Step 7: Create Entry Point

### `main.py`

```python
#!/usr/bin/env python3
"""
News Summarizer - Main Entry Point
"""

import argparse
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from framework.loader import load_and_run_app
from app.config import get_initial_state


def main():
    parser = argparse.ArgumentParser(description='News Summarizer with MCP')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock MCP servers')
    parser.add_argument('--categories', nargs='+',
                       help='News categories (default: tech business)')
    parser.add_argument('--limit', type=int,
                       help='Max articles (default: 10)')
    
    args = parser.parse_args()
    
    print("\n📰 Starting News Summarizer...\n")
    
    # Get initial state
    initial_state = get_initial_state()
    
    # Override with CLI args
    if args.categories:
        initial_state['categories'] = args.categories
    if args.limit:
        initial_state['num_articles'] = args.limit
    
    print(f"⚙️  Categories: {', '.join(initial_state['categories'])}")
    print(f"⚙️  Max articles: {initial_state['num_articles']}\n")
    
    # Run workflow
    result = load_and_run_app(
        'app.workflow',
        initial_state,
        use_mcp_mocks=args.mock
    )
    
    # Display results
    print("\n" + result['daily_digest'])
    
    if result['digest_sent']:
        print(f"\n✅ {result['digest_status']}\n")
    else:
        print(f"\n⚠️  {result['digest_status']}\n")
    
    if result.get('errors'):
        print("Errors:")
        for error in result['errors']:
            print(f"  • {error}")


if __name__ == "__main__":
    main()
```

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

