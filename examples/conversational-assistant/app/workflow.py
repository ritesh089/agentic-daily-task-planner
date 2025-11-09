"""
Conversational Message Assistant Workflow
Ask questions about your emails and Slack messages in natural language

Uses framework's AUTOMATIC memory management - configure once, forget forever!
"""

from typing import TypedDict, List, Dict, Annotated
from langgraph.graph import START, END
from framework import (
    ObservableStateGraph, 
    ConversationMemoryMixin,
    create_memory_aware_reducer,
    MemoryConfig
)

from app.agents.collection_agents import collect_data_agent
from app.agents.chat_agents import (
    init_conversation_agent,
    get_user_input_agent,
    retrieve_context_agent,
    generate_response_agent,
    display_and_check_agent
)


# ============================================================================
# State Definition (Base - Memory configured at runtime)
# ============================================================================

class ConversationalStateBase(ConversationMemoryMixin):
    """
    Base state for conversational assistant workflow
    
    Note: conversation_history reducer is configured at runtime in build_workflow()
    to avoid import-time path issues and enable proper testing.
    """
    
    # Collected data (loaded once, stays in memory)
    emails: List[Dict[str, str]]
    slack_messages: List[Dict[str, str]]
    
    # Current conversation turn
    user_query: str
    context_messages: List[Dict[str, str]]  # Retrieved messages for current query
    assistant_response: str
    
    # Conversation control
    continue_chat: bool
    turn_count: int
    
    # Error tracking
    errors: List[str]


# ============================================================================
# Workflow Builder
# ============================================================================

def build_workflow():
    """
    Builds the conversational assistant workflow with short-term memory
    
    Flow:
    1. Collect data (emails + Slack) once
    2. Initialize conversation with system prompt
    3. Enter conversation loop:
       - Get user input
       - Retrieve relevant messages
       - Generate response with LLM
       - Display and check if continue
    
    Returns:
        Uncompiled workflow (framework adds checkpointer)
    """
    
    # Load memory configuration at BUILD TIME (not import time!)
    # This fixes path issues and enables proper testing
    import os
    config_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'config', 
        'memory_config.yaml'
    )
    
    try:
        if os.path.exists(config_path):
            memory_config_dict = MemoryConfig.load_from_yaml(config_path)
        else:
            # Fallback to defaults
            memory_config_dict = {
                'max_messages': 40,
                'prune_strategy': 'summarize_and_prune'
            }
    except Exception as e:
        print(f"⚠️  Error loading memory config: {e}, using defaults")
        memory_config_dict = {
            'max_messages': 40,
            'prune_strategy': 'summarize_and_prune'
        }
    
    # Create smart reducer with automatic pruning/summarization
    smart_memory_reducer = create_memory_aware_reducer(memory_config_dict)
    
    # Dynamically create state class with configured reducer
    # This is Python's way of creating a TypedDict subclass at runtime
    class ConversationalState(ConversationalStateBase):
        """
        Runtime-configured conversational state with automatic memory management
        
        Memory is configured at workflow build time, then:
        - Agents just return LangChain messages (HumanMessage, AIMessage)
        - Pruning happens automatically when limit is reached
        - Summarization preserves context (if enabled)
        - Zero explicit MemoryManager calls needed!
        """
        conversation_history: Annotated[list, smart_memory_reducer]
    
    # Create observable workflow with automatic instrumentation
    workflow = ObservableStateGraph(ConversationalState)
    
    # Setup phase (one-time)
    workflow.add_node("collect", collect_data_agent)
    workflow.add_node("init_chat", init_conversation_agent)
    
    # Conversation loop
    workflow.add_node("get_input", get_user_input_agent)
    workflow.add_node("retrieve", retrieve_context_agent)
    workflow.add_node("generate", generate_response_agent)
    workflow.add_node("display", display_and_check_agent)
    
    # Define flow
    workflow.add_edge(START, "collect")
    workflow.add_edge("collect", "init_chat")
    workflow.add_edge("init_chat", "get_input")
    
    # Conversation loop edges
    workflow.add_edge("get_input", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "display")
    
    # Conditional: continue conversation or end
    workflow.add_conditional_edges(
        "display",
        lambda state: "continue" if state.get('continue_chat', False) else "end",
        {
            "continue": "get_input",  # Loop back to get next query
            "end": END
        }
    )
    
    # Return uncompiled (framework adds checkpointer)
    return workflow

