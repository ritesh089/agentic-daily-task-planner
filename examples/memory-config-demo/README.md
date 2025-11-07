# Memory Configuration Demo

This example demonstrates the framework's easy memory configuration system using Memory Profiles and YAML configuration.

## Features Demonstrated

1. **Memory Profiles**: Pre-configured presets for common use cases
2. **YAML Configuration**: Simple config file-based setup
3. **Memory Inspector**: Debugging and visualization tools

## Quick Start

### Using Memory Profiles (Easiest)

```python
from framework import MemoryManager, MemoryProfile

# Option 1: Use a preset profile
MemoryManager.init_conversation_with_profile(
    state,
    "You are helpful",
    MemoryProfile.RESEARCH  # Choose: QUICK_CHAT, STANDARD, LONG_SESSION, etc.
)

# Option 2: One-line setup
MemoryManager.quick_setup(state, "You are helpful", use_case='research')
```

### Using YAML Configuration (Recommended)

```yaml
# config/memory_config.yaml
memory:
  profile: "research"  # or: quick_chat, standard, long_session, support, code_review
```

```python
from framework import MemoryConfig

# Load from YAML
MemoryConfig.init_from_yaml(
    state,
    "You are helpful",
    "config/memory_config.yaml"
)
```

### Using Memory Inspector (Debugging)

```python
from framework import MemoryInspector

# Print memory status
MemoryInspector.print_status(state)

# Get metrics
metrics = MemoryInspector.get_metrics(state)
print(f"Memory: {metrics['fill_percentage']:.1f}% full")

# Get recommendations
MemoryInspector.print_recommendation(state)

# Export for analysis
MemoryInspector.export_to_json(state, "memory_export.json")
```

## Available Profiles

| Profile       | Max Messages | Strategy            | Best For                    |
|---------------|--------------|---------------------|-----------------------------|
| QUICK_CHAT    | 10           | keep_recent         | Brief interactions          |
| STANDARD      | 30           | keep_recent         | Normal conversations        |
| LONG_SESSION  | 50           | summarize_and_prune | Extended conversations      |
| RESEARCH      | 40           | summarize_and_prune | Research, analysis          |
| SUPPORT       | 60           | summarize_and_prune | Customer support            |
| CODE_REVIEW   | 35           | summarize_and_prune | Technical discussions       |

## Example: Choosing the Right Profile

### Quick Q&A Bot
```python
# Users ask single questions
MemoryManager.quick_setup(state, "You are helpful", use_case='quick_chat')
# → 10 messages, keep_recent (fast, minimal memory)
```

### Research Assistant
```python
# Users ask many questions, context matters
MemoryManager.quick_setup(state, "You are helpful", use_case='research')
# → 40 messages, summarize_and_prune (preserves context)
```

### Customer Support
```python
# Multi-issue conversations, long sessions
MemoryManager.quick_setup(state, "You are helpful", use_case='support')
# → 60 messages, summarize_and_prune (full context retention)
```

## YAML Configuration Examples

### Example 1: Using a Profile

```yaml
# config/memory_config.yaml
memory:
  profile: "research"
```

### Example 2: Custom Configuration

```yaml
# config/memory_config.yaml
memory:
  custom:
    max_messages: 45
    prune_strategy: "summarize_and_prune"
```

### Example 3: Profile with CLI Override

```python
# Allow CLI to override config
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', default='standard')
    args = parser.parse_args()
    
    profile = MemoryProfile.get_profile(args.profile)
    MemoryManager.init_conversation_with_profile(state, "System", profile)
```

## Memory Inspector Examples

### Basic Status

```python
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

### Detailed Status

```python
MemoryInspector.print_status(state, detailed=True)
```

Shows full conversation with message previews.

### Get Metrics Programmatically

```python
metrics = MemoryInspector.get_metrics(state)

print(f"Messages: {metrics['total_messages']}/{metrics['max_messages']}")
print(f"Fill: {metrics['fill_percentage']:.1f}%")
print(f"Estimated tokens: {metrics['estimated_tokens']}")
print(f"Has summaries: {metrics['has_summaries']}")
```

### Get Recommendations

```python
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

## Integration with Existing Workflows

### Before (Manual Configuration)

```python
# Old way - manual configuration
state = {}
state['conversation_history'] = [{'role': 'system', 'content': '...'}]
state['_memory_config'] = {
    'max_messages': 40,
    'prune_strategy': 'summarize_and_prune',
    'initialized': True
}
```

### After (Profile-Based)

```python
# New way - one line!
MemoryManager.quick_setup(state, "You are helpful", use_case='research')
```

### After (YAML-Based)

```yaml
# config/memory_config.yaml
memory:
  profile: "research"
```

```python
# Load from config
MemoryConfig.init_from_yaml(state, "You are helpful", "config/memory_config.yaml")
```

## Benefits

✅ **No more guessing**: Pre-configured profiles for common use cases  
✅ **Easy configuration**: YAML files instead of code  
✅ **Visual debugging**: Inspector shows memory status  
✅ **Recommendations**: Get suggestions for optimization  
✅ **Metrics**: Track memory usage programmatically  
✅ **Export**: Save conversations for analysis  

## Complete Example

```python
#!/usr/bin/env python3
from framework import MemoryConfig, MemoryInspector, ObservableStateGraph
from langchain_ollama import ChatOllama

def chat_agent(state):
    from framework import MemoryManager
    
    query = state['user_query']
    MemoryManager.add_user_message(state, query)
    
    messages = MemoryManager.get_langchain_messages(state)
    llm = ChatOllama(model="llama3.2")
    response = llm.invoke(messages)
    
    MemoryManager.add_assistant_message(state, response.content)
    
    return state

def main():
    state = {}
    
    # Load from YAML
    MemoryConfig.init_from_yaml(
        state,
        "You are a helpful assistant",
        "config/memory_config.yaml"
    )
    
    # Chat loop
    while True:
        query = input("You: ").strip()
        
        if query.lower() in ['exit', 'quit']:
            break
        
        if query.lower() == 'status':
            MemoryInspector.print_status(state)
            MemoryInspector.print_recommendation(state)
            continue
        
        state['user_query'] = query
        state = chat_agent(state)
        
        print(f"Assistant: {state.get('assistant_response', '')}")
    
    # Export conversation
    MemoryInspector.export_to_json(state, "conversation.json")

if __name__ == "__main__":
    main()
```

## Summary

The framework now provides three easy ways to configure memory:

1. **Profiles**: `MemoryManager.quick_setup(state, "System", use_case='research')`
2. **YAML**: `MemoryConfig.init_from_yaml(state, "System", "config.yaml")`
3. **Manual**: `MemoryManager.init_conversation(state, "System", max_messages=40, ...)`

Choose what works best for your workflow! 🚀

