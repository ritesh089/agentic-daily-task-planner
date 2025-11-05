"""
Application Configuration
Provides app-specific configuration settings
"""

import json
import os
from typing import Dict, Any


def get_app_config() -> Dict[str, Any]:
    """
    Returns application configuration
    
    This is used by the framework to configure observability and other settings
    """
    return {
        'service_name': 'daily-task-planner-agent',
        'service_version': '1.0.0',
        'default_time_range': 24  # Default hours to look back
    }


def get_time_range() -> int:
    """
    Get the time range configuration from slack_credentials.json
    
    Returns:
        Time range in hours (default: 24)
    """
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'slack_credentials.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                slack_config = json.load(f)
            return slack_config.get('time_range_hours', 24)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    return 24  # Default to 24 hours


def get_initial_state() -> Dict[str, Any]:
    """
    Creates the initial state for the workflow
    
    Returns:
        Initial MultiAgentState dictionary
    """
    time_range = get_time_range()
    
    return {
        'time_range_hours': time_range,
        'gmail_service': None,
        'gmail_credentials': None,
        'emails': [],
        'email_summary': '',
        'slack_messages': [],
        'slack_summary': '',
        'tasks': [],
        'prioritized_tasks': [],
        'email_sent': False,
        'email_status': '',
        'email_message_id': '',
        'final_summary': '',
        'errors': []
    }

