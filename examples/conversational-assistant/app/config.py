"""
Application Configuration
"""

from typing import Dict, Any


def get_initial_state() -> Dict[str, Any]:
    """
    Return initial state for conversational assistant workflow
    """
    return {
        # Data storage
        'emails': [],
        'slack_messages': [],
        
        # Conversation memory
        'conversation_history': [],
        
        # Current turn state
        'user_query': '',
        'context_messages': [],
        'assistant_response': '',
        
        # Control
        'continue_chat': True,
        'turn_count': 0,
        
        # Error tracking
        'errors': []
    }


def get_app_config() -> Dict[str, Any]:
    """
    App-specific configuration
    """
    return {
        'name': 'conversational-assistant',
        'version': '1.0.0',
        'description': 'Interactive conversational assistant for emails and Slack messages'
    }

