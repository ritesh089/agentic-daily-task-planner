# Summarization-Based Memory Pruning Demo

This demo showcases the framework's **summarize-and-prune** strategy for conversation memory management.

## What It Does

Instead of discarding old messages when memory limit is reached, the framework:

1. **Extracts** messages that would be pruned
2. **Summarizes** them using an LLM
3. **Replaces** old messages with the summary
4. **Preserves** context while maintaining bounded memory

## Memory Evolution

### Turn 1-10 (Under Limit)
```
[System, User1, AI1, User2, AI2, ..., User10, AI10]
Total: 21 messages (below 20 max)
```

### Turn 11 (Triggers Summarization)
```
Old: [System, User1, AI1, ..., User10, AI10, User11]
     ↓ Summarization triggered
New: [System, Summary("User discussed A, B, C..."), User6, AI6, ..., User11, AI11]
Total: 20 messages (at limit, but context preserved!)
```

### Turn 20 (Multiple Summaries)
```
[System, 
 Summary("Earlier: discussed A, B, C..."),
 Summary("Then: asked about D, E..."),
 User18, AI18, User19, AI19, User20, AI20]
Total: 20 messages (still at limit, full context preserved!)
```

## Run the Demo

```bash
cd examples/summarization-demo

# Basic demo (shows summarization in action)
python demo.py

# Interactive mode
python demo.py --interactive
```

## Example Output

```
🧠 Turn 15: Adding message...
   History length before: 30 messages
   🧠 Creating summary from 12 messages...
   ✓ Summary created, keeping 20 messages

Summary content:
"The user asked about project status, deployment issues, and team
 availability. The assistant provided updates on CI/CD pipeline,
 explained Docker configuration, and confirmed team capacity for Q4."

🧠 Turn 16: Adding message...
   History length: 20 messages (includes summary)
   Memory bounded, context preserved! ✓
```

## Compare Strategies

### Without Summarization (keep_recent)
```python
# After 30 turns, only last ~20 messages remain
# Context from turns 1-10: LOST ❌
```

### With Summarization (summarize_and_prune)
```python
# After 30 turns:
# - Summary of turns 1-10 ✓
# - Summary of turns 11-15 ✓  
# - Full messages for turns 16-30 ✓
# Context preserved across all turns! ✅
```

## Configuration

```python
from framework import MemoryManager

# Enable summarization
MemoryManager.init_conversation(
    state,
    "You are helpful",
    max_messages=20,
    prune_strategy='summarize_and_prune'  # The magic flag!
)
```

## Benefits

✅ **Preserves context**: Old conversations aren't lost  
✅ **Bounded memory**: Still respects max_messages  
✅ **LLM-visible**: Summaries are in conversation history  
✅ **Automatic**: No manual intervention  
✅ **Graceful fallback**: Falls back to keep_recent if summarization fails  

## Implementation

See `framework/memory.py` for the full implementation:
- `MemoryManager._summarize_messages()` - LLM summarization
- `MemoryManager.prune_if_needed()` - Strategy selection
- `MemoryManager.get_langchain_messages()` - Summary handling

## Use Cases

Perfect for:
- **Long conversations**: Multi-turn customer support
- **Research sessions**: Extended Q&A interactions
- **Iterative tasks**: Code review, document editing
- **Ongoing projects**: Project management bots

## Try It

Run the conversational assistant with summarization:

```bash
cd examples/conversational-assistant
python main.py --mock --summarize
```

Ask 15+ questions to see summarization in action!

