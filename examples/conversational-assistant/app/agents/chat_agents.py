"""
Chat Agents
Handle conversational interaction with user

Uses framework's AUTOMATIC memory management - zero explicit memory calls!
Agents just return LangChain messages, reducer handles the rest.
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage


def init_conversation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize conversation with system prompt
    
    With automatic memory management:
    - Just return a SystemMessage
    - No MemoryManager calls needed!
    - Config was loaded in workflow.py, reducer handles everything
    """
    import os
    from framework import MemoryInspector
    
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
    
    # Initialize turn count
    state['turn_count'] = 0
    
    print("=" * 70)
    print(f"💬 Conversational Assistant Ready")
    print("=" * 70)
    print(f"📊 Loaded: {num_emails} emails, {num_slack} Slack messages")
    
    # Show memory status (read-only operation, this is fine!)
    print()
    MemoryInspector.print_status(state)
    
    print("\nAsk me anything about your recent communications!")
    print("Type 'help' or '?' for available commands.\n")
    print("=" * 70)
    
    # AUTOMATIC MEMORY: Just return the SystemMessage!
    # The smart reducer handles adding it to conversation_history
    return {
        'conversation_history': [SystemMessage(content=system_prompt)]
    }


def get_user_input_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get user query interactively
    
    Uses framework's InteractiveCommandHandler for built-in commands:
    - status, export, help, exit are handled automatically
    - Only need to handle regular queries here!
    """
    from framework import InteractiveCommandHandler
    
    try:
        query = input("\n👤 You: ").strip()
        
        # Let framework handle built-in commands (status, export, help, exit)
        # Returns True if command was handled, False for regular queries
        if InteractiveCommandHandler.handle(query, state):
            # Command handled - maintain conversation state
            state.setdefault('user_query', '')
            state.setdefault('continue_chat', True)
            return state
        
        # Regular query - process it
        state['user_query'] = query
        state['continue_chat'] = True
        state['turn_count'] = state.get('turn_count', 0) + 1
        
        # Show automatic memory update every 10 turns
        if state['turn_count'] % 10 == 0:
            print(f"\n   💾 Memory: {len(state.get('conversation_history', []))} messages "
                  f"({state['turn_count']} turns)")
        
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
    
    AUTOMATIC MEMORY PATTERN:
    - Just work with LangChain messages directly
    - Return HumanMessage and AIMessage
    - Smart reducer handles pruning/summarization automatically!
    - Zero explicit MemoryManager calls!
    """
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage, AIMessage
    from framework import to_langchain_messages
    
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
    
    # Prepare user message content
    user_message_content = f"User question: {query}\n\n{context_str}"
    
    # Generate response with LLM
    try:
        llm = ChatOllama(model="llama3.2", temperature=0.7)
        
        # Get current conversation history (already in internal format)
        # Convert to LangChain format for LLM
        current_history = state.get('conversation_history', [])
        lc_messages = to_langchain_messages(current_history)
        
        # Add current user message for LLM invocation
        lc_messages.append(HumanMessage(content=user_message_content))
        
        # Generate response
        response = llm.invoke(lc_messages)
        assistant_response = response.content
        
        # AUTOMATIC MEMORY: Just return the new messages!
        # The smart reducer will:
        # 1. Add them to conversation_history
        # 2. Check if pruning is needed
        # 3. Apply summarization if configured
        # All automatically!
        return {
            'conversation_history': [
                HumanMessage(content=user_message_content),
                AIMessage(content=assistant_response)
            ],
            'assistant_response': assistant_response
        }
        
    except Exception as e:
        error_msg = f"LLM error: {str(e)}"
        print(f"   ✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        return {
            'assistant_response': "Sorry, I encountered an error generating a response. Please try again."
        }


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

