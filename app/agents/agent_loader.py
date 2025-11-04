"""
Agent Loader
Dynamically loads real or mock agents based on configuration
"""

import os
import yaml
from typing import Callable, Tuple


def load_mock_config() -> dict:
    """Load mock configuration from YAML file"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'config',
        'mock_config.yaml'
    )
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    # Default: mocks disabled
    return {'enabled': False, 'active_scenario': 'default'}


def get_email_agents() -> Tuple[Callable, Callable]:
    """
    Get email agents (real or mock based on config)
    
    Returns:
        (email_collector_agent, email_summarizer_agent)
    """
    config = load_mock_config()
    
    if config.get('enabled', False) and config.get('mocks', {}).get('email', {}).get('enabled', False):
        # Use mock agents
        print("🎭 Loading MOCK email agents")
        from app.agents.mocks.email_agents import (
            email_collector_agent,
            email_summarizer_agent,
            MockEmailConfig
        )
        
        # Apply scenario-based failures
        scenario_name = config.get('active_scenario', 'default')
        scenario = config.get('scenarios', {}).get(scenario_name, {})
        
        if scenario.get('email_collection_fails', False):
            MockEmailConfig.enable_collection_failure()
            print("   ⚠️  Email collection failure ENABLED (testing mode)")
        
        if scenario.get('email_summarization_fails', False):
            MockEmailConfig.enable_summarization_failure()
            print("   ⚠️  Email summarization failure ENABLED (testing mode)")
        
        # Apply timing configuration
        email_config = config.get('mocks', {}).get('email', {})
        MockEmailConfig.COLLECTION_DELAY = email_config.get('collection_delay', 0.5)
        MockEmailConfig.SUMMARIZATION_DELAY = email_config.get('summarization_delay', 1.0)
        MockEmailConfig.EMAIL_COUNT = email_config.get('email_count', 5)
        
        return email_collector_agent, email_summarizer_agent
    else:
        # Use real agents
        print("🔌 Loading REAL email agents (requires Gmail API credentials)")
        from app.agents.email_agents import (
            email_collector_agent,
            email_summarizer_agent
        )
        return email_collector_agent, email_summarizer_agent


def get_slack_agents() -> Tuple[Callable, Callable]:
    """
    Get slack agents (real or mock based on config)
    
    Returns:
        (slack_collector_agent, slack_summarizer_agent)
    """
    config = load_mock_config()
    
    if config.get('enabled', False) and config.get('mocks', {}).get('slack', {}).get('enabled', False):
        # Use mock agents
        print("🎭 Loading MOCK slack agents")
        from app.agents.mocks.slack_agents import (
            slack_collector_agent,
            slack_summarizer_agent,
            MockSlackConfig
        )
        
        # Apply scenario-based failures
        scenario_name = config.get('active_scenario', 'default')
        scenario = config.get('scenarios', {}).get(scenario_name, {})
        
        if scenario.get('slack_collection_fails', False):
            MockSlackConfig.enable_collection_failure()
            print("   ⚠️  Slack collection failure ENABLED (testing mode)")
        
        if scenario.get('slack_summarization_fails', False):
            MockSlackConfig.enable_summarization_failure()
            print("   ⚠️  Slack summarization failure ENABLED (testing mode)")
        
        # Apply timing configuration
        slack_config = config.get('mocks', {}).get('slack', {})
        MockSlackConfig.COLLECTION_DELAY = slack_config.get('collection_delay', 0.8)
        MockSlackConfig.SUMMARIZATION_DELAY = slack_config.get('summarization_delay', 1.2)
        MockSlackConfig.MESSAGE_COUNT = slack_config.get('message_count', 6)
        MockSlackConfig.INCLUDE_DMS = slack_config.get('include_dms', True)
        MockSlackConfig.INCLUDE_CHANNELS = slack_config.get('include_channels', True)
        MockSlackConfig.INCLUDE_MENTIONS = slack_config.get('include_mentions', True)
        
        return slack_collector_agent, slack_summarizer_agent
    else:
        # Use real agents
        print("🔌 Loading REAL slack agents (requires Slack token)")
        from app.agents.slack_agents import (
            slack_collector_agent,
            slack_summarizer_agent
        )
        return slack_collector_agent, slack_summarizer_agent

