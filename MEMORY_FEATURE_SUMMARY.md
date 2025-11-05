
# 🧠 Framework Memory Management Feature

## Overview

The framework now includes **built-in conversation memory management** as a first-class feature, eliminating the need for workflows to manually manage conversation history.

## What Was Added

### 1. Core Memory System (`framework/memory.py`)

A comprehensive memory management system with three usage levels:

#### Level 1: Fully Automatic (Decorator) ⭐ RECOMMENDED

```python
@with_conversation_memory(
    system_prompt="You are helpful",
    max_messages=50,
    auto_add_response=True
)
def agent(state):
    MemoryManager.add_user_message(state, query)
    messages = MemoryManager.get_langchain_messages(state)
    response = llm.invoke(messages)
    state['assistant_response'] = response.content
    return state
```

**Benefits**: Zero manual memory management. Framework handles everything.

#### Level 2: Semi-Automatic (Mixin + Manager)

```python
class MyState(ConversationMemoryMixin):
    my_field: str  # conversation_history auto-included!

def agent(state):
    MemoryManager.add_user_message(state, query)
    messages = MemoryManager.get_langchain_messages(state)
    return state
```

**Benefits**: Type-safe state with memory, manual control of messages.

#### Level 3: Manual (Full Control)

```python
MemoryManager.init_conversation(state, "System")
MemoryManager.add_user_message(state, query)
messages = MemoryManager.get_conversation_history(state)
```

**Benefits**: Complete control for advanced use cases.

### 2. Complete API (`MemoryManager`)

```python
# Initialization
MemoryManager.init_conversation(state, prompt, max_messages=50)

# Adding messages
MemoryManager.add_user_message(state, content)
MemoryManager.add_assistant_message(state, content)
MemoryManager.add_message(state, role, content)

# Retrieval
MemoryManager.get_conversation_history(state)
MemoryManager.get_langchain_messages(state)  # Auto-converts!
MemoryManager.get_last_n_messages(state, n)
MemoryManager.get_conversation_length(state)

# Maintenance
MemoryManager.prune_if_needed(state)  # Auto-called by framework
MemoryManager.clear_history(state, keep_system=True)
MemoryManager.is_initialized(state)
```

### 3. Framework Integration

- **Exports**: All memory utilities exported from `framework/__init__.py`
- **Checkpointing**: Memory automatically checkpointed (durable conversations!)
- **Observability**: Memory operations traced by OTEL
- **Durability**: Conversations survive interruptions

### 4. Updated Examples

#### Conversational Assistant (Simplified)

- **Before**: 50+ lines of manual memory management
- **After**: Uses `ConversationMemoryMixin` and `MemoryManager` (~10 lines)
- **Reduction**: 70% less memory-related code

Location: `examples/conversational-assistant/`

#### Memory Examples

Comprehensive guide with multiple patterns and use cases.

Location: `examples/memory-examples/README.md`

### 5. Documentation

- **Framework Guide**: Updated with memory section
- **Memory Examples**: Complete usage patterns
- **README**: Quick start with memory feature
- **API Reference**: Full docstrings in `framework/memory.py`

## Key Features

### Automatic Pruning

```python
# When conversation exceeds max_messages:
# - System message kept
# - Most recent N-1 messages kept
# - Older messages pruned
# All automatic!
```

### Automatic Checkpointing

```python
# Framework checkpoints conversation at each node
# Conversation survives interruptions
# Can resume mid-conversation
```

### LangChain Conversion

```python
# Standard message format
{'role': 'user', 'content': '...'}

# Converts to LangChain messages
messages = MemoryManager.get_langchain_messages(state)
# Returns: [HumanMessage(...), AIMessage(...), ...]
```

### Standard Interface

All workflows use the same memory format and API:
- Consistent across examples
- Easy to understand
- Portable between workflows

## Benefits

1. **Zero Boilerplate**: Decorator handles all memory management
2. **Type Safety**: Mixin ensures memory in state
3. **Automatic Durability**: Framework checkpoints memory
4. **Prevents Overflow**: Automatic pruning prevents context limits
5. **LangChain Ready**: Built-in conversion to LangChain messages
6. **Framework Feature**: Not application code anymore

## Migration Guide

### Before (Manual Memory)

```python
class State(TypedDict):
    conversation_history: Annotated[list, add_messages]
    # ... 50+ lines of memory logic

def add_messages(left, right):
    # Manual reducer logic

def agent(state):
    state['conversation_history'].append({'role': 'user', ...})
    # Manual LangChain conversion
    messages = []
    for msg in state['conversation_history']:
        if msg['role'] == 'user':
            messages.append(HumanMessage(...))
    # Manual pruning
    if len(state['conversation_history']) > 50:
        # ... pruning logic
```

### After (Framework Memory)

```python
from framework import ConversationMemoryMixin, MemoryManager

class State(ConversationMemoryMixin):
    # conversation_history included automatically!
    pass

@with_conversation_memory("System prompt")
def agent(state):
    MemoryManager.add_user_message(state, query)
    messages = MemoryManager.get_langchain_messages(state)
    return state
```

## Files Added/Modified

### New Files

1. `framework/memory.py` - Complete memory system (450+ lines)
2. `examples/memory-examples/README.md` - Usage patterns
3. `examples/conversational-assistant/app/agents/simple_chat_agent.py` - Decorator example

### Modified Files

1. `framework/__init__.py` - Exports memory utilities
2. `examples/conversational-assistant/app/workflow.py` - Uses `ConversationMemoryMixin`
3. `examples/conversational-assistant/app/agents/chat_agents.py` - Uses `MemoryManager`
4. `docs/FRAMEWORK_GUIDE.md` - Added memory documentation
5. `README.md` - Added memory feature highlights

## Testing

Memory can be tested like any other state component:

```python
def test_memory():
    state = {}
    MemoryManager.init_conversation(state, "System")
    assert MemoryManager.is_initialized(state)
    
    MemoryManager.add_user_message(state, "Hi")
    assert MemoryManager.get_conversation_length(state) == 2
    
    state['_memory_config']['max_messages'] = 2
    MemoryManager.prune_if_needed(state)
    assert MemoryManager.get_conversation_length(state) == 2
```

## Next Steps

1. **Try the decorator**: `@with_conversation_memory` for new agents
2. **Explore examples**: See `examples/conversational-assistant/`
3. **Read patterns**: Check `examples/memory-examples/README.md`
4. **Migrate workflows**: Use `ConversationMemoryMixin` in existing workflows

## Summary

Memory management is now a **framework feature**, not application code. Workflows can focus entirely on business logic while the framework handles:

- ✅ Memory initialization
- ✅ Message storage
- ✅ Automatic pruning
- ✅ LangChain conversion
- ✅ Checkpointing (durability)
- ✅ Resumption after interruptions

**Your agents just add messages and use them. The framework does the rest.** 🧠🎉

