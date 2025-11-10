"""
Standalone Conversational Assistant - WITHOUT Framework

This is the same conversational assistant but built with:
- Plain LangGraph (no framework wrapper)
- Direct mem0 integration (manual setup)
- Manual message conversion
- Manual state management
- Manual error handling

Compare this to examples/conversational-assistant/ to see the framework's value!
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
import os

# Direct mem0 import (not abstracted)
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    print("⚠️  mem0 not installed. Memory features disabled.")
    Memory = None


# ============================================================================
# Manual mem0 Setup (Framework does this automatically)
# ============================================================================

class MemoryBackend:
    """
    Manual mem0 wrapper
    Framework abstracts all of this!
    """
    _instances = {}
    
    @staticmethod
    def initialize(user_id: str = "default"):
        """Initialize mem0 instance - manual setup required"""
        if not MEM0_AVAILABLE or user_id in MemoryBackend._instances:
            return None
        
        try:
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": f"conversations_{user_id}",
                        "host": "memory",
                    }
                }
            }
            MemoryBackend._instances[user_id] = Memory.from_config(config)
            print(f"   🧠 mem0 initialized for user: {user_id}")
            return MemoryBackend._instances[user_id]
        except Exception as e:
            print(f"   ⚠️  mem0 initialization failed: {e}")
            return None
    
    @staticmethod
    def get_instance(user_id: str = "default"):
        """Get mem0 instance"""
        return MemoryBackend._instances.get(user_id)
    
    @staticmethod
    def add_to_mem0(user_id: str, messages: List[Dict]):
        """Add messages to mem0 - manual conversion needed"""
        memory = MemoryBackend.get_instance(user_id)
        if not memory:
            return
        
        try:
            for msg in messages:
                memory.add(
                    messages=[{"role": msg['role'], "content": msg['content']}],
                    user_id=user_id,
                    metadata={"timestamp": str(msg.get('timestamp', ''))}
                )
        except Exception as e:
            # Silent failure - no framework error handling
            pass
    
    @staticmethod
    def search_memories(user_id: str, query: str, limit: int = 10):
        """Search memories - manual integration"""
        memory = MemoryBackend.get_instance(user_id)
        if not memory:
            return []
        
        try:
            return memory.search(query=query, user_id=user_id, limit=limit)
        except Exception as e:
            return []


# ============================================================================
# Manual Message Conversion (Framework does this automatically)
# ============================================================================

def langchain_to_internal(lc_messages: List) -> List[Dict]:
    """
    Convert LangChain messages to internal format
    Framework's to_langchain_messages() handles this automatically
    """
    internal = []
    for msg in lc_messages:
        if isinstance(msg, SystemMessage):
            internal.append({'role': 'system', 'content': msg.content})
        elif isinstance(msg, HumanMessage):
            internal.append({'role': 'user', 'content': msg.content})
        elif isinstance(msg, AIMessage):
            internal.append({'role': 'assistant', 'content': msg.content})
        else:
            internal.append({'role': 'user', 'content': str(msg)})
    return internal


def internal_to_langchain(internal_messages: List[Dict]) -> List:
    """
    Convert internal format to LangChain messages
    Framework's get_langchain_messages() handles this automatically
    """
    lc_messages = []
    for msg in internal_messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        if role == 'system':
            lc_messages.append(SystemMessage(content=content))
        elif role == 'user':
            lc_messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    
    return lc_messages


# ============================================================================
# Manual Memory Management (Framework's MemoryManager does this)
# ============================================================================

def add_message_to_history(state: Dict, role: str, content: str, user_id: str = "default"):
    """
    Manually add message to both state and mem0
    Framework's MemoryManager.add_user_message() does this in 1 line
    """
    message = {'role': role, 'content': content}
    
    # Add to state (LangGraph)
    if 'conversation_history' not in state:
        state['conversation_history'] = []
    state['conversation_history'].append(message)
    
    # Add to mem0 (manual sync)
    if MEM0_AVAILABLE:
        MemoryBackend.add_to_mem0(user_id, [message])
    
    # Manual pruning (framework has smart reducer for this)
    max_messages = state.get('max_messages', 50)
    if len(state['conversation_history']) > max_messages:
        # Keep system message if present
        system_msg = state['conversation_history'][0] if state['conversation_history'][0]['role'] == 'system' else None
        if system_msg:
            recent = state['conversation_history'][-(max_messages - 1):]
            state['conversation_history'] = [system_msg] + recent
        else:
            state['conversation_history'] = state['conversation_history'][-max_messages:]


def get_history_for_llm(state: Dict) -> List:
    """
    Get conversation history in LangChain format
    Framework's MemoryManager.get_langchain_messages() does this
    """
    internal_history = state.get('conversation_history', [])
    return internal_to_langchain(internal_history)


# ============================================================================
# State Definition (Manual - no framework mixin)
# ============================================================================

class ConversationalState(TypedDict):
    """
    Manual state definition
    Framework provides ConversationMemoryMixin with auto-reducer
    """
    # Conversation
    conversation_history: List[Dict[str, str]]
    user_query: str
    assistant_response: str
    
    # Data
    emails: List[Dict[str, str]]
    slack_messages: List[Dict[str, str]]
    context_messages: List[Dict[str, str]]
    
    # Control
    continue_chat: bool
    turn_count: int
    
    # Config (manual)
    max_messages: int
    user_id: str
    
    # Errors
    errors: List[str]


# ============================================================================
# Agents (Manual implementations - no framework decorators)
# ============================================================================

def init_conversation_agent(state: ConversationalState) -> ConversationalState:
    """
    Initialize conversation
    Manual setup - framework's init would be 1 line with YAML
    """
    num_emails = len(state.get('emails', []))
    num_slack = len(state.get('slack_messages', []))
    total = num_emails + num_slack
    
    system_prompt = f"""You are a helpful assistant that answers questions about the user's recent communications.

You have access to:
- {num_emails} emails from the last 24 hours
- {num_slack} Slack messages from the last 24 hours
- Total: {total} messages

When answering questions:
1. Reference specific messages when relevant
2. Cite sources clearly
3. If you don't find relevant information, say so clearly
4. Be conversational and helpful
5. You can answer follow-up questions based on previous context"""
    
    # Manual initialization
    state['conversation_history'] = [{'role': 'system', 'content': system_prompt}]
    state['turn_count'] = 0
    state['max_messages'] = 40  # Manual config
    state['user_id'] = state.get('user_id', 'default')
    
    # Initialize mem0 manually
    if MEM0_AVAILABLE:
        MemoryBackend.initialize(state['user_id'])
    
    print("=" * 70)
    print(f"💬 Standalone Conversational Assistant (No Framework)")
    print("=" * 70)
    print(f"📊 Loaded: {num_emails} emails, {num_slack} Slack messages")
    print(f"⚠️  Note: Manual mem0 setup, no framework abstraction")
    print("\nAsk me anything about your recent communications!")
    print("Type 'exit' to quit.\n")
    print("=" * 70)
    
    return state


def get_user_input_agent(state: ConversationalState) -> ConversationalState:
    """
    Get user input
    No framework's InteractiveCommandHandler - all manual
    """
    try:
        query = input("\n👤 You: ").strip()
        
        # Manual command handling (framework has InteractiveCommandHandler)
        if query.lower() in ['exit', 'quit', 'q']:
            print("\n👋 Goodbye!")
            state['continue_chat'] = False
            state['user_query'] = ''
            return state
        
        if query.lower() == 'status':
            # Manual status display (framework has MemoryInspector)
            history = state.get('conversation_history', [])
            max_msgs = state.get('max_messages', 50)
            fill_pct = (len(history) / max_msgs * 100) if max_msgs > 0 else 0
            
            print(f"\n📊 Memory Status:")
            print(f"   Messages: {len(history)}/{max_msgs} ({fill_pct:.1f}% full)")
            print(f"   Turns: {state.get('turn_count', 0)}")
            print(f"   mem0: {'✓ Enabled' if MEM0_AVAILABLE else '✗ Disabled'}")
            
            state['user_query'] = ''
            state['continue_chat'] = True
            return state
        
        if query.lower() in ['help', '?']:
            print("\n📖 Available commands:")
            print("   status  - Show memory status")
            print("   exit    - Exit the conversation")
            print("   help    - Show this message")
            state['user_query'] = ''
            state['continue_chat'] = True
            return state
        
        # Regular query
        state['user_query'] = query
        state['continue_chat'] = True
        state['turn_count'] = state.get('turn_count', 0) + 1
        
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Conversation interrupted. Goodbye!")
        state['continue_chat'] = False
        state['user_query'] = ''
    
    return state


def retrieve_context_agent(state: ConversationalState) -> ConversationalState:
    """
    Retrieve relevant messages
    Simple keyword search (same as framework version)
    """
    query = state.get('user_query', '').lower()
    
    if not query:
        state['context_messages'] = []
        return state
    
    print("   🔍 Searching messages...")
    
    keywords = query.split()
    relevant_messages = []
    
    # Search emails
    for email in state.get('emails', []):
        searchable_text = (
            f"{email.get('from', '')} "
            f"{email.get('subject', '')} "
            f"{email.get('body', '')}"
        ).lower()
        
        score = sum(1 for keyword in keywords if keyword in searchable_text)
        
        if score > 0:
            relevant_messages.append({
                'type': 'email',
                'from': email.get('from', 'Unknown'),
                'subject': email.get('subject', 'No Subject'),
                'preview': email.get('body', '')[:200],
                'date': email.get('date', ''),
                'score': score
            })
    
    # Search Slack
    for msg in state.get('slack_messages', []):
        searchable_text = (
            f"{msg.get('from', '')} "
            f"{msg.get('channel', '')} "
            f"{msg.get('text', '')}"
        ).lower()
        
        score = sum(1 for keyword in keywords if keyword in searchable_text)
        
        if score > 0:
            relevant_messages.append({
                'type': 'slack',
                'from': msg.get('from', 'Unknown'),
                'channel': msg.get('channel', 'Unknown'),
                'preview': msg.get('text', '')[:200],
                'timestamp': msg.get('timestamp', ''),
                'score': score
            })
    
    relevant_messages.sort(key=lambda x: x['score'], reverse=True)
    state['context_messages'] = relevant_messages[:5]
    
    print(f"   ✓ Found {len(state['context_messages'])} relevant message(s)")
    
    return state


def generate_response_agent(state: ConversationalState) -> ConversationalState:
    """
    Generate response with LLM
    Manual message handling - no framework auto-conversion
    """
    print("   🤖 Generating response...")
    
    query = state.get('user_query', '')
    context_messages = state.get('context_messages', [])
    
    if not query:
        return state
    
    # Build context string
    context_str = ""
    if context_messages:
        context_str = "Relevant messages found:\n\n"
        for i, msg in enumerate(context_messages, 1):
            if msg['type'] == 'email':
                context_str += (
                    f"{i}. EMAIL from {msg['from']}\n"
                    f"   Subject: {msg['subject']}\n"
                    f"   Date: {msg['date']}\n"
                    f"   Preview: {msg['preview']}...\n\n"
                )
            else:
                context_str += (
                    f"{i}. SLACK in #{msg['channel']} from {msg['from']}\n"
                    f"   Time: {msg['timestamp']}\n"
                    f"   Message: {msg['preview']}...\n\n"
                )
    else:
        context_str = "No directly relevant messages found in the last 24 hours."
    
    user_message_content = f"User question: {query}\n\n{context_str}"
    
    # Generate response
    try:
        llm = ChatOllama(model="llama3.2", temperature=0.7)
        
        # Manual conversion: internal → LangChain
        current_history = state.get('conversation_history', [])
        lc_messages = internal_to_langchain(current_history)
        
        # Add current user message
        lc_messages.append(HumanMessage(content=user_message_content))
        
        # Invoke LLM
        response = llm.invoke(lc_messages)
        assistant_response = response.content
        
        # Manual memory update (framework's smart reducer does this automatically)
        add_message_to_history(state, 'user', user_message_content, state.get('user_id', 'default'))
        add_message_to_history(state, 'assistant', assistant_response, state.get('user_id', 'default'))
        
        state['assistant_response'] = assistant_response
        
    except Exception as e:
        error_msg = f"LLM error: {str(e)}"
        print(f"   ✗ {error_msg}")
        if 'errors' not in state:
            state['errors'] = []
        state['errors'].append(error_msg)
        state['assistant_response'] = "Sorry, I encountered an error generating a response."
    
    return state


def display_and_check_agent(state: ConversationalState) -> ConversationalState:
    """Display response"""
    response = state.get('assistant_response', '')
    print(f"\n🤖 Assistant: {response}")
    return state


# ============================================================================
# Manual Mock Data (same as framework version)
# ============================================================================

def load_mock_data() -> Dict[str, List[Dict]]:
    """Load mock emails and Slack messages"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    mock_emails = [
        {
            'from': 'alice@company.com',
            'subject': 'Q4 Budget Review',
            'body': 'Hi team, please review the attached Q4 budget proposal. We need to finalize by Friday.',
            'date': (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
        },
        {
            'from': 'bob@company.com',
            'subject': 'Project Alpha Update',
            'body': 'Project Alpha is on track. Deployment scheduled for next week.',
            'date': (now - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M')
        },
        {
            'from': 'charlie@company.com',
            'subject': 'Team Meeting Tomorrow',
            'body': 'Reminder: Team standup tomorrow at 10am. Please come prepared with updates.',
            'date': (now - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
        }
    ]
    
    mock_slack_messages = [
        {
            'from': 'alice',
            'channel': 'engineering',
            'text': 'The new API endpoints are live. Documentation updated.',
            'timestamp': (now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
        },
        {
            'from': 'bob',
            'channel': 'general',
            'text': 'Great job everyone on the launch! 🎉',
            'timestamp': (now - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')
        },
        {
            'from': 'charlie',
            'channel': 'engineering',
            'text': 'Code review for PR #234 is complete. Approved!',
            'timestamp': (now - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')
        }
    ]
    
    return {
        'emails': mock_emails,
        'slack_messages': mock_slack_messages
    }


# ============================================================================
# Workflow Builder (Plain LangGraph - no framework wrapper)
# ============================================================================

def build_workflow():
    """
    Build workflow with plain LangGraph
    Compare to framework version with ObservableStateGraph
    """
    # Plain LangGraph StateGraph (no framework observability)
    workflow = StateGraph(ConversationalState)
    
    # Add nodes
    workflow.add_node("init_chat", init_conversation_agent)
    workflow.add_node("get_input", get_user_input_agent)
    workflow.add_node("retrieve", retrieve_context_agent)
    workflow.add_node("generate", generate_response_agent)
    workflow.add_node("display", display_and_check_agent)
    
    # Define flow
    workflow.add_edge(START, "init_chat")
    workflow.add_edge("init_chat", "get_input")
    workflow.add_edge("get_input", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "display")
    
    # Conditional: continue or end
    workflow.add_conditional_edges(
        "display",
        lambda state: "continue" if state.get('continue_chat', False) else "end",
        {
            "continue": "get_input",
            "end": END
        }
    )
    
    # Return compiled workflow (no framework checkpointer)
    return workflow.compile()

