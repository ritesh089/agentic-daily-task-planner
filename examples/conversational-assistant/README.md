# Conversational Message Assistant

An **interactive conversational agent** that lets you ask questions about your recent emails and Slack messages in natural language.

## Features

- 💬 **Natural Language Queries**: Ask questions in plain English
- 🧠 **Short-term Memory**: Maintains conversation context across turns
- 🔍 **Smart Retrieval**: Automatically finds relevant messages
- 🤖 **LLM-Powered**: Uses Ollama for intelligent responses
- 💾 **Durable**: Conversation can resume if interrupted (checkpointing)
- 🎯 **Framework-Powered**: Uses all framework features (observability, MCP, durability)

## What Makes This Different

Unlike the `daily-task-planner` which runs once and produces a report, this assistant:
- **Interactive**: You ask questions, it answers
- **Conversational**: Remembers previous questions and answers
- **On-demand retrieval**: Only searches for relevant messages when needed
- **Natural interaction**: Chat interface instead of batch processing

## Quick Start

```bash
# Navigate to this example
cd examples/conversational-assistant

# Run with mock data (for testing)
python main.py --mock

# Run with real data
python main.py
```

## Example Conversation

```
💬 Conversational Assistant Ready
📊 Loaded: 15 emails, 23 Slack messages

Ask me anything about your recent communications!

👤 You: What emails did I receive about the Q4 report?

🤖 Assistant: Based on your emails, you received 2 messages about the Q4 report:

1. From Alice Johnson on Nov 4th: She sent you the draft Q4 financial 
   report and asked for your review by end of week.

2. From Bob Smith on Nov 5th: He followed up asking if you had any 
   questions about the Q4 numbers.

👤 You: What did Alice say specifically about the deadline?

🤖 Assistant: Alice mentioned in her email that she needs your feedback 
"by end of week" and specifically asked you to focus on the revenue 
projections section.

👤 You: Were there any Slack messages about this?

🤖 Assistant: Yes, Carol mentioned the Q4 report in the #finance channel 
yesterday, asking if everyone had reviewed it yet.

👤 You: exit

✅ Session completed!
```

## Architecture

### Workflow

```
Collect Data (once)
    ↓
Initialize Conversation
    ↓
┌──> Get User Input
│       ↓
│   Retrieve Relevant Messages
│       ↓
│   Generate Response (LLM)
│       ↓
│   Display Response
│       ↓
└─── Loop if continue
```

### Memory Management

**Short-term Conversation Memory:**
```python
conversation_history: [
    {'role': 'system', 'content': 'You are a helpful assistant...'},
    {'role': 'user', 'content': 'What emails about Q4?'},
    {'role': 'assistant', 'content': 'You received 2 emails...'},
    {'role': 'user', 'content': 'What did Alice say?'},
    {'role': 'assistant', 'content': 'Alice mentioned...'},
    # ... continues
]
```

**Benefits:**
- LLM sees full conversation context
- Can answer follow-up questions
- Framework automatically checkpoints this
- Can resume if interrupted

**Message Corpus:**
- All emails and Slack messages loaded once
- Kept in state throughout conversation
- Searched dynamically based on queries

## Key Components

### 1. Collection Agent (`collection_agents.py`)
- Collects emails via MCP
- Collects Slack messages via MCP
- Runs once at startup
- Loads everything into memory

### 2. Chat Agents (`chat_agents.py`)

**Init Conversation**: Sets up system prompt with context

**Get User Input**: Interactive input handling
- Reads user query
- Handles exit commands
- Manages conversation flow

**Retrieve Context**: Smart message search
- Keyword-based search
- Searches emails and Slack
- Returns top 5 most relevant
- Scores by relevance

**Generate Response**: LLM-powered answers
- Uses Ollama (llama3.2)
- Includes conversation history (memory!)
- Includes retrieved messages as context
- Returns natural language response

**Display**: Shows response and continues loop

### 3. State Definition (`workflow.py`)

```python
class ConversationalState(TypedDict):
    emails: List[Dict]              # Collected emails
    slack_messages: List[Dict]      # Collected Slack
    conversation_history: list      # SHORT-TERM MEMORY
    user_query: str                 # Current question
    context_messages: List[Dict]    # Retrieved messages
    assistant_response: str         # Current answer
    continue_chat: bool             # Loop control
```

## How Short-term Memory Works

The framework manages conversation memory through:

1. **State Field**: `conversation_history` with `add_messages` reducer
2. **Automatic Checkpointing**: Framework saves after each node
3. **LLM Context**: Full history passed to LLM each turn
4. **Resumable**: If interrupted, can resume conversation

```python
# Example of memory in action:
Turn 1: "What emails about Q4?"
  → conversation_history: [system, user1, assistant1]

Turn 2: "What did Alice say?" (refers to previous context)
  → conversation_history: [system, user1, assistant1, user2, assistant2]
  → LLM sees full history, knows "Alice" from Turn 1
```

## Configuration

### Observability (`config/observability_config.yaml`)
- Service name: `conversational-assistant`
- Traces enabled
- View in Jaeger: http://localhost:16686

### Durability (`config/durability_config.yaml`)
- Checkpoints after each agent
- Auto-resume enabled
- **Conversation can be interrupted and resumed!**

### MCP (`config/mcp_config.yaml`)
- Uses email and slack MCP servers
- Set `use_mocks: true` for testing

## Advanced Usage

### With Tracing

```bash
# Start Jaeger first
docker-compose up -d jaeger

# Run assistant
python main.py

# View traces at http://localhost:16686
# See every agent execution, retrieval, LLM call
```

### Test Interrupted Workflow

```bash
# Start conversation
python main.py --mock

# Ask a question
You: What emails are there?

# Kill process (Ctrl+C)

# Restart - it resumes!
python main.py --mock
# Conversation continues from where you left off
```

### View Checkpoints

```bash
# Query PostgreSQL to see saved conversation state
psql postgresql://postgres:postgres@localhost:5432/langgraph

# View checkpoints
SELECT thread_id, checkpoint_id, checkpoint_ns 
FROM checkpoints 
WHERE checkpoint_ns LIKE '%conversational%'
ORDER BY checkpoint_id DESC;
```

## Extending This Example

### Add Semantic Search

Replace keyword search with embeddings:

```python
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

def retrieve_context_agent_with_embeddings(state):
    # Create embeddings for query
    embeddings = OllamaEmbeddings(model="llama3.2")
    
    # Search using vector similarity
    docs = vectorstore.similarity_search(
        state['user_query'],
        k=5
    )
    
    return docs
```

### Add Multi-turn Actions

```python
def handle_action_agent(state):
    """Execute actions based on conversation"""
    
    if "send email" in state['user_query'].lower():
        # Extract recipient and content from conversation
        # Use MCP to send email
        result = run_async_tool_call(
            server_name="email",
            tool_name="send_email",
            arguments={...}
        )
```

### Add Memory Pruning

```python
MAX_HISTORY = 20

def prune_memory_agent(state):
    """Keep conversation history manageable"""
    
    history = state['conversation_history']
    
    if len(history) > MAX_HISTORY:
        # Keep system message + recent history
        system_msg = history[0]
        recent = history[-(MAX_HISTORY-1):]
        state['conversation_history'] = [system_msg] + recent
    
    return state

# Add to workflow after display
workflow.add_node("prune", prune_memory_agent)
workflow.add_edge("display", "prune")
```

## Troubleshooting

### LLM Not Available

```bash
# Make sure Ollama is running
ollama serve

# Pull model if needed
ollama pull llama3.2
```

### No Messages Loaded

```bash
# Check MCP servers
../../mcp status

# Try mock mode
python main.py --mock
```

### Conversation Not Resuming

```bash
# Check PostgreSQL
docker-compose ps postgres

# Check durability config
cat config/durability_config.yaml
```

## Comparison with Other Examples

| Feature | Daily Task Planner | Simple Processor | **Conversational** |
|---------|-------------------|------------------|-------------------|
| Mode | Batch | Batch | **Interactive** |
| Memory | N/A | N/A | **Short-term** |
| MCP | Yes | No | **Yes** |
| LLM | Yes | No | **Yes** |
| Loop | No | No | **Yes** |
| User Input | No | No | **Yes** |

## Next Steps

1. **Enhance retrieval** - Add vector embeddings
2. **Add actions** - Send emails, create tasks from conversation
3. **Multi-modal** - Add document Q&A
4. **Export conversations** - Save chat history
5. **Web UI** - Build a chat interface

---

**This example demonstrates:**
- ✅ Interactive workflow loops
- ✅ Short-term memory management
- ✅ Dynamic context retrieval
- ✅ LLM integration
- ✅ Full framework benefits (MCP, durability, observability)

**Chat with your messages naturally!** 💬

