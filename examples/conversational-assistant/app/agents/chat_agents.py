"""
Chat Agents
Handle conversational interaction with user

Uses framework's MemoryManager for automatic memory management!
"""

from typing import Dict, Any
from framework import MemoryManager


def init_conversation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize conversation with system prompt
    Uses framework's memory configuration (YAML or code)
    """
    import os
    from framework import MemoryConfig, MemoryInspector
    
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
2. Cite sources clearly (e.g., "In the email from Alice..." or "In the #engineering channel...")
3. If you don't find relevant information, say so clearly
4. Be conversational and helpful
5. You can answer follow-up questions based on previous context

The user will ask you questions, and relevant messages will be provided to you automatically."""
    
    # Try to load from YAML config first
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'config',
        'memory_config.yaml'
    )
    
    try:
        if os.path.exists(config_path):
            # Load from YAML - easy configuration!
            MemoryConfig.init_from_yaml(state, system_prompt, config_path)
        else:
            # Fallback to code-based config
            use_summarization = state.get('use_summarization', False)
            prune_strategy = 'summarize_and_prune' if use_summarization else 'keep_recent'
            MemoryManager.init_conversation(
                state, 
                system_prompt, 
                max_messages=20,
                prune_strategy=prune_strategy
            )
            print(f"⚠️  No memory_config.yaml found, using defaults")
    except Exception as e:
        print(f"⚠️  Error loading memory config: {e}")
        # Fallback to defaults
        MemoryManager.init_conversation(state, system_prompt)
    
    state['turn_count'] = 0
    
    print("=" * 70)
    print(f"💬 Conversational Assistant Ready")
    print("=" * 70)
    print(f"📊 Loaded: {num_emails} emails, {num_slack} Slack messages")
    
    # Show memory status
    print()
    MemoryInspector.print_status(state)
    
    print("\nAsk me anything about your recent communications!")
    print("Type 'exit', 'quit', or 'status' to see memory status.\n")
    print("=" * 70)
    
    return state


def get_user_input_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get user query interactively
    Handles input and conversation control
    """
    
    try:
        query = input("\n👤 You: ").strip()
        
        # Check for exit commands
        if query.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            print("\n👋 Ending conversation. Goodbye!")
            state['continue_chat'] = False
            state['user_query'] = ''
            return state
        
        # Empty query
        if not query:
            print("   (Please enter a question)")
            state['user_query'] = ''
            state['continue_chat'] = True  # Keep going
            return state
        
        # Valid query
        state['user_query'] = query
        state['continue_chat'] = True
        state['turn_count'] = state.get('turn_count', 0) + 1
        
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Conversation interrupted. Goodbye!")
        state['continue_chat'] = False
        state['user_query'] = ''
    
    return state


def retrieve_context_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant messages for current query
    Simple keyword-based search across emails and Slack
    """
    
    query = state.get('user_query', '').lower()
    
    if not query:
        state['context_messages'] = []
        return state
    
    print("   🔍 Searching messages...")
    
    # Extract keywords from query
    keywords = query.split()
    relevant_messages = []
    
    # Search through emails
    for email in state.get('emails', []):
        searchable_text = (
            f"{email.get('from', '')} "
            f"{email.get('subject', '')} "
            f"{email.get('body', '')}"
        ).lower()
        
        # Calculate relevance score
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
    
    # Search through Slack messages
    for msg in state.get('slack_messages', []):
        searchable_text = (
            f"{msg.get('from', '')} "
            f"{msg.get('channel', '')} "
            f"{msg.get('text', '')}"
        ).lower()
        
        # Calculate relevance score
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
    
    # Sort by relevance score and take top 5
    relevant_messages.sort(key=lambda x: x['score'], reverse=True)
    state['context_messages'] = relevant_messages[:5]
    
    num_found = len(state['context_messages'])
    print(f"   ✓ Found {num_found} relevant message(s)")
    
    return state


def generate_response_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate response using Ollama LLM
    Uses framework's MemoryManager - much simpler!
    """
    from langchain_ollama import ChatOllama
    
    print("   🤖 Generating response...")
    
    query = state.get('user_query', '')
    context_messages = state.get('context_messages', [])
    
    if not query:
        return state
    
    # Build context string from retrieved messages
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
            else:  # slack
                context_str += (
                    f"{i}. SLACK in #{msg['channel']} from {msg['from']}\n"
                    f"   Time: {msg['timestamp']}\n"
                    f"   Message: {msg['preview']}...\n\n"
                )
    else:
        context_str = "No directly relevant messages found in the last 24 hours."
    
    # Framework handles adding user message!
    user_message_content = f"User question: {query}\n\n{context_str}"
    MemoryManager.add_user_message(state, user_message_content)
    
    # Generate response with LLM
    try:
        llm = ChatOllama(model="llama3.2", temperature=0.7)
        
        # Framework converts to LangChain format!
        lc_messages = MemoryManager.get_langchain_messages(state)
        
        # Generate response
        response = llm.invoke(lc_messages)
        assistant_response = response.content
        
        # Framework handles adding assistant response!
        MemoryManager.add_assistant_message(state, assistant_response)
        
        state['assistant_response'] = assistant_response
        
        # Framework automatically prunes if needed!
        
    except Exception as e:
        error_msg = f"LLM error: {str(e)}"
        print(f"   ✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        state['assistant_response'] = "Sorry, I encountered an error generating a response. Please try again."
    
    return state


def display_and_check_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Display the assistant's response and check if conversation should continue
    """
    
    response = state.get('assistant_response', '')
    
    # Display response
    print(f"\n🤖 Assistant: {response}")
    
    # Conversation continues if we have a valid query
    # (continue_chat was already set in get_user_input_agent)
    
    return state

