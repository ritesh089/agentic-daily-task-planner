# Memory Management Guide

## Overview

The framework provides powerful conversation memory management with **two approaches**:

### 🌟 **Automatic Memory (RECOMMENDED)**
- **Zero explicit memory calls** in agents
- Configure once in `workflow.py`, forget forever
- Agents just return LangChain messages
- Pruning/summarization happens automatically

### 🔧 **Manual Memory (Advanced)**
- Explicit `MemoryManager` calls for fine-grained control
- Full control over when/how memory is updated
- Useful for complex scenarios

---

## Approach 1: Automatic Memory (Smart Reducer) 🌟

**This is the RECOMMENDED approach for 90% of use cases!**

### How It Works

1. **Configure once** in `workflow.py` using `create_memory_aware_reducer()`
2. **Agents return LangChain messages** - no MemoryManager calls!
3. **Reducer handles everything** - pruning, summarization, checkpointing

### Complete Example

#### Step 1: Load Config (workflow.py)

```python
from typing import Annotated
from framework import (
    ObservableStateGraph,
    ConversationMemoryMixin,
    create_memory_aware_reducer,
    MemoryConfig
)

# Load memory config from YAML
memory_config = MemoryConfig.load_from_yaml('config/memory_config.yaml')

# Create smart reducer
smart_reducer = create_memory_aware_reducer(memory_config)

# Define state with smart reducer
class MyState(ConversationMemoryMixin):
    conversation_history: Annotated[list, smart_reducer]  # ← Automatic memory!
    user_query: str
    assistant_response: str
    # ... other fields
```

#### Step 2: Create Memory Config (config/memory_config.yaml)

```yaml
memory:
  profile: "research"  # or: quick_chat, standard, long_session, support, code_review
```

Or custom settings:

```yaml
memory:
  custom:
    max_messages: 40
    prune_strategy: "summarize_and_prune"
```

#### Step 3: Agents Return Messages (No MemoryManager!)

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from framework import to_langchain_messages

def init_agent(state):
    """Initialize with system message - no MemoryManager!"""
    return {
        'conversation_history': [
            SystemMessage(content="You are a helpful assistant")
        ]
    }

def chat_agent(state):
    """Generate response - no MemoryManager calls!"""
    
    # Get current history and convert to LangChain format
    lc_messages = to_langchain_messages(state['conversation_history'])
    
    # Add user message
    lc_messages.append(HumanMessage(content=state['user_query']))
    
    # Generate response
    llm = ChatOllama(model="llama3.2")
    response = llm.invoke(lc_messages)
    
    # Just return new messages - reducer does the rest!
    return {
        'conversation_history': [
            HumanMessage(content=state['user_query']),
            AIMessage(content=response.content)
        ],
        'assistant_response': response.content
    }
    # Pruning? Automatic!
    # Summarization? Automatic!
    # Checkpointing? Automatic!
```

### Benefits of Automatic Approach

- ✅ **Configure once, forget forever** - Zero memory management in agents
- ✅ **Idiomatic LangGraph** - Standard reducer pattern, no framework magic
- ✅ **Clean code** - Agents focus on business logic, not memory
- ✅ **Still debuggable** - Use `MemoryInspector` for status/export
- ✅ **Production-ready** - Works with checkpointing, streaming, all LangGraph features

### Interactive Commands (Optional)

You can still use `MemoryInspector` for debugging:

```python
from framework import MemoryInspector

def special_command_agent(state):
    if state['user_query'] == 'status':
        MemoryInspector.print_status(state)
        MemoryInspector.print_recommendation(state)
    
    if state['user_query'] == 'export':
        MemoryInspector.export_to_json(state, "conversation.json")
    
    return state
```

### See It in Action

The `conversational-assistant` example uses this pattern exclusively:

```bash
cd examples/conversational-assistant
python main.py --mock

# Try these commands:
# You: status    # Show memory status
# You: export    # Export conversation
# You: help      # Show commands
```

---

## Approach 2: Manual Memory (MemoryManager) 🔧

**Use this for advanced scenarios where you need fine-grained control.**

### When to Use Manual Approach

- Complex memory manipulation (e.g., editing/removing specific messages)
- Multiple memory streams in one workflow
- Custom memory patterns not supported by smart reducer
- Migrating existing code

### Memory Profiles

Pre-configured memory profiles eliminate guesswork. Just pick a profile that matches your use case!

### Available Profiles

| Profile       | Max Messages | Strategy            | Best For                    |
|---------------|--------------|---------------------|-----------------------------|
| QUICK_CHAT    | 10           | keep_recent         | Brief interactions (1-5 turns) |
| STANDARD      | 30           | keep_recent         | Normal conversations (10-20 turns) |
| LONG_SESSION  | 50           | summarize_and_prune | Extended conversations (20-50 turns) |
| RESEARCH      | 40           | summarize_and_prune | Research, analysis workflows |
| SUPPORT       | 60           | summarize_and_prune | Customer support, help desk |
| CODE_REVIEW   | 35           | summarize_and_prune | Technical discussions |

### Usage

#### Option 1: Use a Profile Directly

```python
from framework import MemoryManager, MemoryProfile

# Initialize with a profile
MemoryManager.init_conversation_with_profile(
    state,
    "You are a helpful assistant",
    MemoryProfile.RESEARCH  # Choose the profile that fits!
)
```

#### Option 2: One-Line Setup

```python
from framework import MemoryManager

# Super simple!
MemoryManager.quick_setup(
    state,
    "You are a helpful assistant",
    use_case='research'  # quick_chat, standard, long_session, research, support, code_review
)
```

### When to Use Each Profile

**QUICK_CHAT**: Command-line tools, single Q&A, chatbots with brief interactions
```python
MemoryManager.quick_setup(state, "System", use_case='quick_chat')
```

**STANDARD**: Most conversational agents, general-purpose chatbots
```python
MemoryManager.quick_setup(state, "System", use_case='standard')
```

**LONG_SESSION**: Extended customer conversations, tutoring, coaching
```python
MemoryManager.quick_setup(state, "System", use_case='long_session')
```

**RESEARCH**: Research assistants, Q&A systems, knowledge exploration
```python
MemoryManager.quick_setup(state, "System", use_case='research')
```

**SUPPORT**: Help desk, technical support, multi-issue conversations
```python
MemoryManager.quick_setup(state, "System", use_case='support')
```

**CODE_REVIEW**: Code review bots, technical discussions, pair programming
```python
MemoryManager.quick_setup(state, "System", use_case='code_review')
```

## YAML Configuration

For production workflows, use YAML configuration files. This separates configuration from code.

### Creating a Memory Config File

Create `config/memory_config.yaml`:

```yaml
# Option 1: Use a profile (recommended)
memory:
  profile: "research"

# Option 2: Custom configuration
# memory:
#   custom:
#     max_messages: 45
#     prune_strategy: "summarize_and_prune"
```

### Loading from YAML

```python
from framework import MemoryConfig

# Load memory configuration from YAML
MemoryConfig.init_from_yaml(
    state,
    "You are a helpful assistant",
    "config/memory_config.yaml"
)
```

### Example: Dynamic Configuration

Allow users to choose profiles via CLI:

```python
import argparse
from framework import MemoryConfig, MemoryProfile

parser = argparse.ArgumentParser()
parser.add_argument('--memory-profile', default='standard',
                   choices=['quick_chat', 'standard', 'long_session', 
                           'research', 'support', 'code_review'])
args = parser.parse_args()

# Use profile from CLI
profile = MemoryProfile.get_profile(args.memory_profile)
MemoryManager.init_conversation_with_profile(state, "System", profile)
```

## Memory Inspector

Debug and monitor memory usage with built-in inspector tools.

### Basic Status

```python
from framework import MemoryInspector

# Print current memory status
MemoryInspector.print_status(state)
```

Output:
```
╔═══════════════════════════════════════════════════════════╗
║               MEMORY STATUS                               ║
╚═══════════════════════════════════════════════════════════╝
📊 Messages: 15/40 (37.5% full)
🎯 Strategy: summarize_and_prune
🔧 Initialized: ✓ Yes

📋 Message Breakdown:
   ⚙️ System: 1
   👤 User: 7
   🤖 Assistant: 7
╚═══════════════════════════════════════════════════════════╝
```

### Detailed View

```python
# Show full conversation with message previews
MemoryInspector.print_status(state, detailed=True)
```

### Get Metrics Programmatically

```python
metrics = MemoryInspector.get_metrics(state)

print(f"Messages: {metrics['total_messages']}/{metrics['max_messages']}")
print(f"Fill: {metrics['fill_percentage']:.1f}%")
print(f"Tokens: ~{metrics['estimated_tokens']}")
print(f"Has summaries: {metrics['has_summaries']}")
print(f"Strategy: {metrics['strategy']}")
```

### Get Recommendations

```python
# Get automatic recommendations for optimization
MemoryInspector.print_recommendation(state)
```

Output:
```
╔═══════════════════════════════════════════════════════════╗
║            MEMORY RECOMMENDATIONS                         ║
╚═══════════════════════════════════════════════════════════╝

💡 Recommendations:

   STRATEGY:
   Current: keep_recent
   Suggested: summarize_and_prune
   Reason: Memory is filling up, consider summarization to preserve context

╚═══════════════════════════════════════════════════════════╝
```

### Export for Analysis

```python
# Export conversation to JSON for analysis
MemoryInspector.export_to_json(state, "conversation_export.json")
```

## Complete Example

```python
#!/usr/bin/env python3
"""
Complete example using all memory management features
"""

from framework import (
    MemoryConfig, 
    MemoryInspector,
    MemoryManager
)
from langchain_ollama import ChatOllama

def main():
    state = {}
    
    # Load memory from YAML
    MemoryConfig.init_from_yaml(
        state,
        "You are a helpful research assistant",
        "config/memory_config.yaml"
    )
    
    llm = ChatOllama(model="llama3.2")
    
    print("Chat with the assistant. Type 'status' to see memory, 'exit' to quit.\n")
    
    while True:
        # Get input
        query = input("You: ").strip()
        
        # Handle commands
        if query.lower() in ['exit', 'quit']:
            break
        
        if query.lower() == 'status':
            MemoryInspector.print_status(state)
            MemoryInspector.print_recommendation(state)
            continue
        
        # Add user message
        MemoryManager.add_user_message(state, query)
        
        # Generate response
        messages = MemoryManager.get_langchain_messages(state)
        response = llm.invoke(messages)
        
        # Add assistant response
        MemoryManager.add_assistant_message(state, response.content)
        
        print(f"Assistant: {response.content}\n")
    
    # Export conversation
    MemoryInspector.export_to_json(state, "chat_export.json")
    print("✓ Conversation exported to chat_export.json")

if __name__ == "__main__":
    main()
```

## Integration Examples

### Example 1: Daily Task Planner

```python
# examples/daily-task-planner/app/workflow.py
from framework import MemoryManager

# No memory needed for batch processing
# (This workflow processes data once, no conversation)
```

### Example 2: Conversational Assistant

```python
# examples/conversational-assistant/app/agents/chat_agents.py
from framework import MemoryConfig, MemoryInspector

def init_conversation_agent(state):
    # Load from YAML
    MemoryConfig.init_from_yaml(
        state,
        "You are helpful",
        "config/memory_config.yaml"
    )
    
    # Show status
    MemoryInspector.print_status(state)
    
    return state
```

### Example 3: Custom Research Agent

```python
# app/workflow.py
from framework import MemoryManager, MemoryProfile

def build_workflow():
    workflow = ObservableStateGraph(ResearchState)
    
    # Use RESEARCH profile for context-heavy workflows
    def init_memory(state):
        MemoryManager.init_conversation_with_profile(
            state,
            "You are a research assistant",
            MemoryProfile.RESEARCH
        )
        return state
    
    workflow.add_node("init", init_memory)
    # ... rest of workflow
```

## Best Practices

### 1. Choose the Right Profile

Match your profile to your use case:
- Short interactions → QUICK_CHAT or STANDARD
- Long sessions → LONG_SESSION, RESEARCH, SUPPORT
- Context matters → Use profiles with `summarize_and_prune`

### 2. Use YAML for Production

Development:
```python
# Quick testing
MemoryManager.quick_setup(state, "System", use_case='research')
```

Production:
```yaml
# config/memory_config.yaml
memory:
  profile: "research"
```

```python
# Load from config
MemoryConfig.init_from_yaml(state, "System", "config/memory_config.yaml")
```

### 3. Monitor Memory Usage

Add status commands to your workflows:

```python
if user_input == 'status':
    MemoryInspector.print_status(state)
    MemoryInspector.print_recommendation(state)
```

### 4. Test with Different Profiles

```bash
# Try different profiles to find the best fit
python main.py --memory-profile quick_chat    # Test with minimal memory
python main.py --memory-profile standard      # Test with standard config
python main.py --memory-profile research      # Test with context preservation
```

### 5. Export for Analysis

```python
# At end of workflow
MemoryInspector.export_to_json(state, f"conversation_{timestamp}.json")
```

## Migration from Manual Configuration

### Before

```python
# Old way - manual configuration
state['conversation_history'] = [{'role': 'system', 'content': '...'}]
state['_memory_config'] = {
    'max_messages': 40,
    'prune_strategy': 'summarize_and_prune',
    'initialized': True
}

# Manual message handling
state['conversation_history'].append({'role': 'user', 'content': query})
# ... manual pruning logic ...
```

### After

```python
# New way - one line!
MemoryManager.quick_setup(state, "You are helpful", use_case='research')

# Or with YAML
MemoryConfig.init_from_yaml(state, "You are helpful", "config/memory_config.yaml")

# Messages handled automatically
MemoryManager.add_user_message(state, query)
```

## Troubleshooting

### Profile Not Found

```python
# Error: Unknown profile 'custom'
# Solution: Use one of the available profiles
profiles = MemoryProfile.list_profiles()
print(profiles.keys())  # See available profiles
```

### YAML Config Not Loading

```python
# Check if file exists
import os
if not os.path.exists("config/memory_config.yaml"):
    print("Config file not found!")
    
# Check YAML syntax
import yaml
with open("config/memory_config.yaml") as f:
    config = yaml.safe_load(f)
    print(config)
```

### Memory Filling Up Too Fast

```python
# Check metrics
metrics = MemoryInspector.get_metrics(state)
print(f"Fill: {metrics['fill_percentage']:.1f}%")
print(f"Avg message length: {metrics['avg_message_length']}")

# Get recommendations
MemoryInspector.print_recommendation(state)
```

## API Reference

See `framework/memory.py` for complete API documentation:

- `MemoryProfile` - Profile constants and utilities
- `MemoryManager` - Core memory management
- `MemoryInspector` - Debugging and visualization
- `MemoryConfig` - YAML configuration loader

## Summary

Three easy ways to configure memory:

1. **Profiles**: `MemoryManager.quick_setup(state, "System", use_case='research')`
2. **YAML**: `MemoryConfig.init_from_yaml(state, "System", "config.yaml")`
3. **Manual**: `MemoryManager.init_conversation(state, "System", max_messages=40, ...)`

Choose what works best for your workflow! 🚀

