# Example Conversation Session

## Session Output

```
🚀 Starting Conversational Message Assistant (MCP Mode)...

🔧 Using MOCK MCP servers (testing mode)

💬 Conversational Assistant Ready
══════════════════════════════════════════════════════════════════
📊 Loaded: 5 emails, 8 Slack messages

🎯 Using memory profile: research
   Optimized for research and analysis workflows (context-heavy)

╔═══════════════════════════════════════════════════════════════╗
║               MEMORY STATUS                                   ║
╚═══════════════════════════════════════════════════════════════╝
📊 Messages: 1/40 (2.5% full)
🎯 Strategy: summarize_and_prune
🔧 Initialized: ✓ Yes

📋 Message Breakdown:
   ⚙️ System: 1
╚═══════════════════════════════════════════════════════════════╝

Ask me anything about your recent communications!
Type 'exit', 'quit', or 'status' to see memory status.

══════════════════════════════════════════════════════════════════

👤 You: What emails did I receive about Q4 planning?

   🔍 Searching messages...
   ✓ Found 2 relevant message(s)
   🤖 Generating response...

🤖 Assistant: Based on your recent emails, you received two messages about Q4 planning:

1. **From Alice Chen** - "Q4 Strategy Review"
   She's requesting your input on the Q4 roadmap and wants to schedule a 
   meeting next week to discuss priorities.

2. **From Bob Wilson** - "Budget Planning Q4"
   Bob sent the preliminary Q4 budget spreadsheet and is asking for your 
   department's resource requirements by Friday.

Would you like more details about either of these messages?

👤 You: What did Alice specifically say about the meeting?

   🔍 Searching messages...
   ✓ Found 1 relevant message(s)
   🤖 Generating response...

🤖 Assistant: Alice mentioned in her email that she'd like to schedule a 
1-hour meeting next Tuesday or Wednesday to review the Q4 roadmap. She 
specifically wants to discuss:
- New feature priorities
- Resource allocation
- Timeline adjustments for the delayed Q3 releases

She asked if Tuesday at 2 PM works for you, and if not, to suggest an 
alternative time that week.

👤 You: status

╔═══════════════════════════════════════════════════════════════╗
║               MEMORY STATUS                                   ║
╚═══════════════════════════════════════════════════════════════╝
📊 Messages: 5/40 (12.5% full)
🎯 Strategy: summarize_and_prune
🔧 Initialized: ✓ Yes

📋 Message Breakdown:
   ⚙️ System: 1
   👤 User: 2
   🤖 Assistant: 2
╚═══════════════════════════════════════════════════════════════╝
╔═══════════════════════════════════════════════════════════════╗
║            MEMORY RECOMMENDATIONS                             ║
╚═══════════════════════════════════════════════════════════════╝
⚠️  Too few messages to provide recommendations
   Continue the conversation and check again
╚═══════════════════════════════════════════════════════════════╝

👤 You: What about Slack messages? Anything urgent?

   🔍 Searching messages...
   ✓ Found 3 relevant message(s)
   🤖 Generating response...

🤖 Assistant: Yes, there are a couple of urgent items in Slack:

**#engineering channel:**
- **From Dev Team** - The production deployment is scheduled for tonight at 
  10 PM. They're asking all engineers to be on standby for the first hour 
  after deployment.

**#general channel:**
- **From Sarah** - She's blocked on the API integration and needs your help. 
  She mentioned it's holding up the entire feature and marked it as urgent.

The API integration issue seems to be the most time-sensitive item that 
requires your immediate attention.

👤 You: help

Available commands:
  exit/quit  - End the conversation
  status     - Show memory status and recommendations
  export     - Export conversation to JSON
  help/?     - Show this help message

👤 You: export

✓ Exported memory to conversation_20231107_143022.json

👤 You: exit

👋 Ending conversation. Goodbye!
Export conversation to JSON? (y/n): n

✅ Conversational assistant workflow completed!
```

## Key Features Demonstrated

### 1. Memory Profile Usage
- Automatically loads from `config/memory_config.yaml`
- Uses "research" profile (40 messages, summarize_and_prune)
- Shows configuration on startup

### 2. Memory Inspector
- **`status`** command shows:
  - Current memory usage (5/40 messages)
  - Strategy being used
  - Message breakdown by type
  - Recommendations when enough data

### 3. Context Awareness
- Second question builds on first ("What did Alice specifically say...")
- LLM has access to previous conversation via memory
- No need to repeat context

### 4. Interactive Commands
- **`status`** - Check memory at any time
- **`export`** - Save conversation for later analysis
- **`help`** - Show available commands
- **`exit`** - Clean exit with export option

### 5. Automatic Memory Management
- Framework handles conversation history
- No manual memory code in the application
- Automatic pruning when limit reached
- Summarization preserves old context

### 6. Visual Feedback
- Memory status shown on initialization
- Progress updates every 10 turns
- Clear command responses
- Emoji indicators for different actions

## Memory Evolution Example

As the conversation continues past 40 messages:

```
Turn 45: Adding messages...
   🧠 Creating summary from 20 messages...
   ✓ Summary created, keeping 40 messages

Summary: "User inquired about Q4 planning emails, specifically Alice's 
meeting request and Bob's budget. Also asked about Slack urgency, particularly 
the API integration issue. User exported conversation for reference."
```

The framework automatically:
1. Detects memory limit reached
2. Extracts old messages (turns 1-20)
3. Summarizes them with LLM
4. Keeps summary + recent messages
5. Total: Still 40 messages, but context preserved!

## Export Example

The exported JSON (`conversation_20231107_143022.json`) contains:

```json
{
  "conversation_history": [
    {
      "role": "system",
      "content": "You are a helpful assistant..."
    },
    {
      "role": "user",
      "content": "What emails did I receive about Q4 planning?"
    },
    {
      "role": "assistant",
      "content": "Based on your recent emails..."
    }
    // ... more messages
  ],
  "memory_config": {
    "max_messages": 40,
    "prune_strategy": "summarize_and_prune",
    "initialized": true
  },
  "metrics": {
    "total_messages": 5,
    "max_messages": 40,
    "fill_percentage": 12.5,
    "estimated_tokens": 450,
    "has_summaries": false,
    "strategy": "summarize_and_prune"
  }
}
```

This can be:
- Analyzed later
- Used for debugging
- Fed back into the system
- Processed for insights

## Benefits Demonstrated

✅ **Easy Configuration**: Just edit YAML file  
✅ **Visual Debugging**: `status` command shows everything  
✅ **Context Preservation**: Conversation flows naturally  
✅ **Automatic Management**: No memory code in app  
✅ **Export Capability**: Save conversations for analysis  
✅ **User-Friendly**: Clear commands and feedback  
✅ **Production-Ready**: Durable, observable, scalable  

