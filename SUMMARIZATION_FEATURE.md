
# 🧠 Summarization-Based Memory Pruning

## Overview

The framework now includes **intelligent conversation memory pruning** that uses LLM summarization to preserve context instead of discarding old messages.

## The Problem

Traditional memory management discards old messages when limits are reached:

```
Conversation with 30 messages, max=20:
[Msg1, Msg2, ..., Msg30]
      ↓ Prune (discard old)
[Msg11, Msg12, ..., Msg30]

❌ Lost: Messages 1-10 (context gone forever)
```

## The Solution

**Summarize-and-Prune Strategy**: Old messages are summarized by an LLM before removal:

```
Conversation with 30 messages, max=20:
[Msg1, Msg2, ..., Msg30]
      ↓ Summarize old + Prune
[Summary("User asked X, Y. Assistant provided Z..."), Msg11, ..., Msg30]

✅ Preserved: Context from messages 1-10 in summary
✅ Bounded: Still only 20 messages in memory
✅ Visible: LLM sees summary in future turns
```

## How It Works

### 1. Detection
When `conversation_history` exceeds `max_messages`, pruning is triggered.

### 2. Strategy Selection
Two strategies available:
- **`keep_recent`** (default): Discard old messages, keep recent ones
- **`summarize_and_prune`** (new): Summarize old messages before discarding

### 3. Summarization Process

```python
# Messages to be pruned are extracted
old_messages = history[1:10]  # e.g., messages 1-10

# LLM summarizes them
summary = llm.invoke("""Summarize these conversations:
USER: What's the project status?
ASSISTANT: On track, phase 1 complete...
...""")

# Summary result: "User asked about project status and deployment.
# Assistant confirmed on-track progress and Friday deployment."
```

### 4. History Reconstruction

```python
new_history = [
    system_message,
    {'role': 'summary', 'content': summary},
    ...recent_messages
]
```

### 5. LLM Integration

Summaries are converted to `SystemMessage` for LLM context:

```python
# In get_langchain_messages()
if msg['role'] == 'summary':
    messages.append(SystemMessage(
        content=f"[Previous Conversation Summary]\n{msg['content']}"
    ))
```

## Implementation

### Core Changes in `framework/memory.py`

#### 1. Summarization Prompt

```python
SUMMARIZATION_PROMPT = """You are a conversation summarizer. Summarize the following conversation turns into a concise paragraph that captures:
1. Main topics discussed
2. Key questions asked
3. Important answers/information provided
4. Any decisions or conclusions reached

Keep it brief but informative (max 3-4 sentences)."""
```

#### 2. Summarization Method

```python
@staticmethod
def _summarize_messages(messages: List[Dict], llm=None) -> str:
    """Use LLM to summarize a list of messages"""
    formatted = "\n\n".join([
        f"{msg['role'].upper()}: {msg['content'][:200]}..."
        for msg in messages
    ])
    
    if llm is None:
        llm = ChatOllama(model="llama3.2", temperature=0.3)
    
    response = llm.invoke([HumanMessage(
        content=SUMMARIZATION_PROMPT.format(messages=formatted)
    )])
    
    return response.content.strip()
```

#### 3. Enhanced Pruning Logic

```python
@staticmethod
def prune_if_needed(state, llm=None):
    strategy = state.get('_memory_config', {}).get('prune_strategy', 'keep_recent')
    
    if strategy == 'summarize_and_prune':
        # Check for existing summary
        if has_existing_summary:
            # Summarize gap between summary and recent messages
            # Append to existing summary (incremental)
        else:
            # First summarization
            # Create new summary from old messages
        
        # Rebuild: [system, summary, recent_messages]
    else:
        # Original keep_recent strategy
        # Rebuild: [system, recent_messages]
```

## Usage Examples

### Example 1: Basic Configuration

```python
from framework import MemoryManager

state = {}
MemoryManager.init_conversation(
    state,
    "You are a helpful assistant",
    max_messages=20,
    prune_strategy='summarize_and_prune'  # Enable summarization!
)

# Add messages normally
MemoryManager.add_user_message(state, "Question 1")
MemoryManager.add_assistant_message(state, "Answer 1")
# ... continue conversation ...
# When exceeds 20 messages, automatic summarization happens!
```

### Example 2: With Decorator

```python
from framework import with_conversation_memory, MemoryManager
from langchain_ollama import ChatOllama

@with_conversation_memory(
    system_prompt="You are helpful",
    max_messages=20,
    prune_strategy='summarize_and_prune',
    summarization_llm=ChatOllama(model="llama3.2", temperature=0.3)
)
def chat_agent(state):
    MemoryManager.add_user_message(state, state['query'])
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    state['assistant_response'] = response.content
    return state
```

### Example 3: Conversational Assistant

```bash
cd examples/conversational-assistant
python main.py --mock --summarize
```

## Memory Evolution Example

### Turn 1-10 (Under Limit)
```
History (21 messages, max=20):
[System, U1, A1, U2, A2, ..., U10, A10]
Status: Under limit, no pruning
```

### Turn 11 (Triggers First Summarization)
```
Before (23 messages):
[System, U1, A1, ..., U10, A10, U11, A11]

Summarization:
  Extract: [U1, A1, U2, A2, U3, A3, U4, A4]
  Summarize: "User asked about A, B, C. Assistant explained X, Y, Z."

After (20 messages):
[System, Summary(...), U5, A5, ..., U11, A11]
```

### Turn 20 (Multiple Summaries)
```
Before (23 messages):
[System, Summary1(...), U5, A5, ..., U20, A20]

Summarization:
  Extract: [U5, A5, U6, A6, U7, A7]
  Summarize: "User then asked about D, E. Assistant provided details."

After (20 messages):
[System, 
 Summary1("Earlier: asked A, B, C...") +
 Summary2("Then: asked D, E..."),
 U8, A8, ..., U20, A20]
```

## Key Features

✅ **Context Preservation**: Old messages aren't lost, they're compressed  
✅ **Bounded Memory**: Still respects `max_messages` limit  
✅ **LLM-Visible**: Summaries are visible to LLM as system messages  
✅ **Incremental**: New summaries append to existing summaries  
✅ **Automatic**: No manual intervention required  
✅ **Graceful Fallback**: Falls back to `keep_recent` if summarization fails  
✅ **Configurable**: Choose strategy per workflow  
✅ **Custom LLM**: Can provide custom summarization LLM  

## Benefits Over Discard-Based Pruning

| Feature | keep_recent | summarize_and_prune |
|---------|-------------|---------------------|
| Context preserved | ❌ Lost | ✅ Summarized |
| Memory bounded | ✅ Yes | ✅ Yes |
| Speed | ⚡ Fast | 🐢 Slower (LLM call) |
| LLM sees old context | ❌ No | ✅ Yes (summary) |
| Long conversations | ❌ Loses history | ✅ Preserves history |
| Best for | Short chats | Long sessions |

## Performance Considerations

### LLM Call Overhead

Each summarization triggers an LLM call:
- **Cost**: ~200-500 tokens per summarization
- **Time**: ~1-2 seconds (depends on LLM)
- **Frequency**: Only when exceeding `max_messages`

### Optimization Tips

1. **Set appropriate `max_messages`**: Higher = fewer summarizations
2. **Use fast LLM**: `llama3.2` with `temperature=0.3` is good balance
3. **Monitor turn count**: ~1 summarization per `max_messages` turns
4. **Consider use case**: 
   - Short sessions (< 20 turns): `keep_recent` is fine
   - Long sessions (> 50 turns): `summarize_and_prune` is worth it

## Use Cases

Perfect for:
- 🎧 **Customer support**: Long, multi-issue conversations
- 📚 **Research assistants**: Extended Q&A sessions
- 💻 **Code review**: Iterative feedback loops
- 📊 **Project management**: Multi-day status updates
- 🎓 **Tutoring**: Long educational sessions

Not needed for:
- ⚡ **Quick queries**: Single-turn interactions
- 🔍 **Search**: One question, one answer
- 📝 **Form filling**: Structured, short exchanges

## Demo

### Run Basic Demo

```bash
cd examples/summarization-demo
python demo.py
```

Output:
```
Turn 15: Adding messages...
   🧠 Creating summary from 12 messages...
   ✓ Summary created, keeping 20 messages

Summary: "The user inquired about project status,
deployment timeline, and team capacity..."
```

### Run Interactive Demo

```bash
python demo.py --interactive
```

Chat with the assistant and see summarization in action!

## Configuration Reference

### MemoryManager.init_conversation()

```python
MemoryManager.init_conversation(
    state,
    system_prompt: str,           # System prompt for LLM
    max_messages: int = 50,       # Maximum messages in history
    prune_strategy: str = 'keep_recent',  # 'keep_recent' or 'summarize_and_prune'
    summarization_llm = None      # Optional custom LLM for summarization
)
```

### @with_conversation_memory Decorator

```python
@with_conversation_memory(
    system_prompt: str = None,
    max_messages: int = 50,
    auto_add_response: bool = False,
    prune_strategy: str = 'keep_recent',
    summarization_llm = None
)
```

## Testing

To test summarization:

```python
# Set low max_messages for quick testing
state = {}
MemoryManager.init_conversation(
    state,
    "You are helpful",
    max_messages=6,  # Will trigger after just 3 exchanges!
    prune_strategy='summarize_and_prune'
)

# Add messages
for i in range(10):
    MemoryManager.add_user_message(state, f"Question {i}")
    MemoryManager.add_assistant_message(state, f"Answer {i}")
    
    # Check for summary
    history = MemoryManager.get_conversation_history(state)
    has_summary = any(msg['role'] == 'summary' for msg in history)
    if has_summary:
        print(f"✅ Summarization triggered at turn {i}")
```

## Future Enhancements

Possible improvements:
- 📊 **Hierarchical summaries**: Summary of summaries for very long conversations
- 🎯 **Selective summarization**: Keep important messages, summarize only routine ones
- 🔍 **Semantic chunking**: Group related topics before summarizing
- 📈 **Adaptive limits**: Adjust `max_messages` based on message lengths
- 💾 **Summary caching**: Cache summaries to avoid re-summarization

## Summary

Summarization-based pruning is a powerful feature for maintaining conversation context in long-running workflows. It balances the need for bounded memory with the requirement to preserve historical context, making it ideal for extended interactive sessions.

**When to use**: Long conversations where context matters  
**When not to use**: Short, transactional interactions  
**How to enable**: Set `prune_strategy='summarize_and_prune'`  
**Result**: Full context preservation with bounded memory! 🧠✨

