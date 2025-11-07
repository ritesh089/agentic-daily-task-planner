"""
Application Configuration
Initial state for the conversational assistant workflow
"""

def get_initial_state(use_summarization: bool = False):
    """
    Return initial state for the workflow
    
    Args:
        use_summarization: If True, use 'summarize_and_prune' strategy
    """
    return {
        # Data collection
        'emails': [],
        'slack_messages': [],
        
        # Memory configuration
        'use_summarization': use_summarization,
        
        # Conversation state
        'user_query': '',
        'context_messages': [],
        'assistant_response': '',
        'continue_chat': True,
        'turn_count': 0,
        
        # Error tracking
        'errors': []
    }
