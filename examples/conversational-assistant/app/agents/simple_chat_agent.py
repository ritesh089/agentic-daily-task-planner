"""
Simple Chat Agent Example
Demonstrates using framework's @with_conversation_memory decorator
"""

from typing import Dict, Any
from framework import with_conversation_memory, MemoryManager
from langchain_ollama import ChatOllama


@with_conversation_memory(
    system_prompt="You are a helpful assistant that answers questions about recent communications.",
    max_messages=50,
    auto_add_response=True  # Automatically adds assistant_response to history!
)
def simple_chat_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ultra-simple chat agent using decorator
    Memory is completely automatic!
    """
    print("   🤖 Simple Chat Agent (with auto-memory)...")
    
    query = state.get('user_query', '')
    if not query:
        return state
    
    # Add user message
    MemoryManager.add_user_message(state, query)
    
    # Get messages in LangChain format (framework handles conversion)
    messages = MemoryManager.get_langchain_messages(state)
    
    # Generate response
    llm = ChatOllama(model="llama3.2", temperature=0.7)
    response = llm.invoke(messages)
    
    # Just set the response - decorator auto-adds to history!
    state['assistant_response'] = response.content
    
    # Memory pruning is automatic!
    return state

