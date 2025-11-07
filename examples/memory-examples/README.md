# Framework Memory Management Examples

This directory contains examples demonstrating the framework's built-in memory management capabilities.

## Overview

The framework provides **conversation memory as a first-class feature**, so your workflows don't need to manage it manually.

## Three Approaches

### 1. Manual with MemoryManager (Full Control)

```python
from framework import MemoryManager

def my_agent(state):
    # Initialize (if not already)
    if not MemoryManager.is_initialized(state):
        MemoryManager.init_conversation(state, "System prompt")
    
    # Add messages manually
    MemoryManager.add_user_message(state, "Query")
    
    # Get messages for LLM
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    
    # Add response
    MemoryManager.add_assistant_message(state, response.content)
    
    # Pruning happens automatically
    return state
```

**Use when**: You need fine-grained control

### 2. State Mixin (Semi-Automatic)

```python
from framework import ConversationMemoryMixin, MemoryManager

class MyState(ConversationMemoryMixin):
    # conversation_history automatically included!
    my_field: str

def my_agent(state):
    # Memory field exists automatically
    MemoryManager.add_user_message(state, "Query")
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    MemoryManager.add_assistant_message(state, response.content)
    return state
```

**Use when**: You want memory in state but manual message handling

### 3. @with_conversation_memory Decorator (Fully Automatic)

```python
from framework import with_conversation_memory, MemoryManager

@with_conversation_memory(
    system_prompt="You are helpful",
    max_messages=50,
    auto_add_response=True
)
def my_agent(state):
    # Memory initialization - automatic!
    # Pruning - automatic!
    # Response adding - automatic!
    
    MemoryManager.add_user_message(state, state['query'])
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    state['assistant_response'] = response.content
    return state  # Framework handles everything!
```

**Use when**: You want zero memory management code (recommended)

## Complete Examples

### Example 1: Simple Q&A Bot

```python
# examples/memory-examples/simple_qa_bot.py

from typing import Dict, Any
from framework import (
    ObservableStateGraph,
    ConversationMemoryMixin,
    with_conversation_memory,
    MemoryManager
)
from langchain_ollama import ChatOllama
from langgraph.graph import START, END

class QAState(ConversationMemoryMixin):
    user_query: str
    assistant_response: str
    continue_chat: bool

@with_conversation_memory(
    system_prompt="You are a helpful Q&A assistant.",
    max_messages=20,
    auto_add_response=True
)
def qa_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    MemoryManager.add_user_message(state, state['user_query'])
    
    llm = ChatOllama(model="llama3.2")
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    
    state['assistant_response'] = response.content
    return state

def build_workflow():
    workflow = ObservableStateGraph(QAState)
    workflow.add_node("qa", qa_agent)
    workflow.add_edge(START, "qa")
    workflow.add_edge("qa", END)
    return workflow
```

### Example 2: Multi-Agent with Shared Memory

```python
# Each agent shares the same conversation history

@with_conversation_memory(system_prompt="You summarize")
def summarizer_agent(state):
    # Has access to full conversation
    history = MemoryManager.get_conversation_history(state)
    # ... summarize ...
    return state

@with_conversation_memory(system_prompt="You analyze")
def analyzer_agent(state):
    # Same conversation history!
    history = MemoryManager.get_conversation_history(state)
    # ... analyze ...
    return state

# Both agents see the same conversation context
```

### Example 3: Memory Inspection

```python
from framework import MemoryManager

def debug_agent(state):
    # Check if memory is initialized
    if MemoryManager.is_initialized(state):
        print(f"Memory initialized: {MemoryManager.get_conversation_length(state)} messages")
    
    # Get last N messages
    recent = MemoryManager.get_last_n_messages(state, 5)
    
    # Get full history
    full = MemoryManager.get_conversation_history(state)
    
    return state
```

### Example 4: Memory Pruning Control

```python
# Initialize with custom max_messages
MemoryManager.init_conversation(
    state,
    "You are helpful",
    max_messages=100  # Keep more history
)

# Manual pruning if needed
MemoryManager.prune_if_needed(state)

# Clear history (keep system message)
MemoryManager.clear_history(state, keep_system=True)
```

## Memory Benefits

### Automatic Checkpointing

The framework **automatically checkpoints** conversation history:

```python
# After each agent execution
conversation_history = [
    {'role': 'system', 'content': '...'},
    {'role': 'user', 'content': 'Turn 1'},
    {'role': 'assistant', 'content': '...'},
    # ... checkpointed by framework!
]
```

**Benefits**:
- Conversation survives interruptions
- Can resume mid-conversation
- Full durability for free

### Automatic Pruning

Prevents context overflow:

```python
@with_conversation_memory(max_messages=50)
def agent(state):
    # When conversation exceeds 50 messages:
    # - System message kept
    # - Most recent 49 messages kept
    # - Older messages pruned
    # All automatic!
    return state
```

### Standard Interface

All workflows use the same memory format:

```python
{
    'role': 'system|user|assistant',
    'content': 'message content'
}
```

LangChain conversion is built-in:
```python
messages = MemoryManager.get_langchain_messages(state)
# Returns: [SystemMessage(...), HumanMessage(...), AIMessage(...)]
```

## Real-World Examples

### Conversational Assistant

See `examples/conversational-assistant/` for a complete working example using framework memory.

**Try with summarization**:
```bash
cd examples/conversational-assistant
python main.py --mock --summarize
```

### Summarization Demo

See `examples/summarization-demo/` for a focused demonstration of the summarization feature.

**Run the demo**:
```bash
cd examples/summarization-demo
python demo.py              # Basic demo
python demo.py --interactive  # Interactive chat
```

**Before (manual)**:
```python
# 50+ lines of memory management code
state['conversation_history'] = [{'role': 'system', ...}]
state['conversation_history'].append({'role': 'user', ...})
# ... manual pruning ...
# ... manual LangChain conversion ...
```

**After (framework memory)**:
```python
# 5 lines with decorator
@with_conversation_memory("You are helpful")
def agent(state):
    MemoryManager.add_user_message(state, query)
    messages = MemoryManager.get_langchain_messages(state)
    return state
```

## Best Practices

1. **Use decorators** for simple cases
2. **Use MemoryManager** for complex logic
3. **Use Mixin** to ensure memory in state
4. **Set max_messages** appropriate to your use case
5. **Let framework handle pruning** - don't do it manually

## Testing Memory

```python
def test_memory():
    state = {'conversation_history': []}
    
    # Initialize
    MemoryManager.init_conversation(state, "System")
    assert MemoryManager.is_initialized(state)
    assert MemoryManager.get_conversation_length(state) == 1
    
    # Add messages
    MemoryManager.add_user_message(state, "Hi")
    MemoryManager.add_assistant_message(state, "Hello")
    assert MemoryManager.get_conversation_length(state) == 3
    
    # Test pruning
    state['_memory_config']['max_messages'] = 2
    MemoryManager.prune_if_needed(state)
    assert MemoryManager.get_conversation_length(state) == 2
```

## API Reference

See `framework/memory.py` for complete API documentation.

**Key Methods**:
- `MemoryManager.init_conversation()`
- `MemoryManager.add_user_message()`
- `MemoryManager.add_assistant_message()`
- `MemoryManager.get_langchain_messages()`
- `MemoryManager.get_conversation_history()`
- `MemoryManager.get_conversation_length()`
- `MemoryManager.prune_if_needed()`
- `MemoryManager.clear_history()`
- `MemoryManager.is_initialized()`

**Decorators**:
- `@with_conversation_memory()` - Auto-memory management
- `@requires_conversation_memory` - Validation decorator

**Mixins**:
- `ConversationMemoryMixin` - Adds memory to state

---

**Memory management is now a framework feature - your workflows can focus on business logic!** 🧠

