# Memory Management - Quick Start

## TL;DR - Just 3 Lines!

```python
from framework import MemoryConfig

# That's it! Config from YAML
MemoryConfig.init_from_yaml(state, "You are helpful", "config/memory_config.yaml")
```

## Setup for New Examples

### Step 1: Create `config/memory_config.yaml`

```yaml
memory:
  profile: "research"  # See profiles below
```

### Step 2: Load in Your Workflow

```python
from framework import MemoryConfig

def init_agent(state):
    MemoryConfig.init_from_yaml(
        state,
        "You are a helpful assistant",
        "config/memory_config.yaml"
    )
    return state
```

### Step 3: Done! 🎉

Memory is now automatically managed with:
- ✅ Automatic pruning
- ✅ Optional summarization
- ✅ Checkpointing (durable)
- ✅ LangChain conversion

## Available Profiles

Choose the profile that matches your use case:

```yaml
# Brief interactions (1-5 turns)
memory:
  profile: "quick_chat"

# Normal conversations (10-20 turns)
memory:
  profile: "standard"

# Extended conversations (20-50 turns) with summarization
memory:
  profile: "long_session"

# Research/Q&A (context-heavy) with summarization
memory:
  profile: "research"

# Customer support (60+ turns) with summarization
memory:
  profile: "support"

# Code review/technical discussions with summarization
memory:
  profile: "code_review"
```

## Even Simpler: One-Line Setup

Don't want YAML? Use one-line setup:

```python
from framework import MemoryManager

# One line!
MemoryManager.quick_setup(state, "You are helpful", use_case='research')
```

## Debugging Memory

Add a status command to your workflow:

```python
from framework import MemoryInspector

if user_input == 'status':
    MemoryInspector.print_status(state)
    MemoryInspector.print_recommendation(state)
```

## Complete Minimal Example

```python
#!/usr/bin/env python3
from framework import MemoryConfig, MemoryManager
from langchain_ollama import ChatOllama

def main():
    state = {}
    
    # Load memory config
    MemoryConfig.init_from_yaml(state, "You are helpful", "config/memory_config.yaml")
    
    llm = ChatOllama(model="llama3.2")
    
    while True:
        query = input("You: ").strip()
        if query.lower() == 'exit':
            break
        
        # Add user message
        MemoryManager.add_user_message(state, query)
        
        # Generate response
        messages = MemoryManager.get_langchain_messages(state)
        response = llm.invoke(messages)
        
        # Add assistant response
        MemoryManager.add_assistant_message(state, response.content)
        
        print(f"Assistant: {response.content}\n")

if __name__ == "__main__":
    main()
```

That's it! For more details, see `docs/MEMORY_MANAGEMENT_GUIDE.md`.

