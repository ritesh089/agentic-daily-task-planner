"""
Mock Agents Package
Provides mock implementations for testing without real API calls
"""

from app.agents.mocks.email_agents import (
    email_collector_agent,
    email_summarizer_agent,
    MockEmailConfig,
    set_mock_emails,
    add_mock_email,
    clear_mock_emails,
    get_mock_email_count
)

from app.agents.mocks.slack_agents import (
    slack_collector_agent,
    slack_summarizer_agent,
    MockSlackConfig,
    set_mock_messages,
    add_mock_message,
    clear_mock_messages,
    get_mock_message_count
)

from app.agents.mocks.communication_agents import (
    email_sender_agent as mock_email_sender_agent,
    MockCommunicationConfig
)

__all__ = [
    # Email mocks
    'email_collector_agent',
    'email_summarizer_agent',
    'MockEmailConfig',
    'set_mock_emails',
    'add_mock_email',
    'clear_mock_emails',
    'get_mock_email_count',
    
    # Slack mocks
    'slack_collector_agent',
    'slack_summarizer_agent',
    'MockSlackConfig',
    'set_mock_messages',
    'add_mock_message',
    'clear_mock_messages',
    'get_mock_message_count',
    
    # Communication mocks
    'mock_email_sender_agent',
    'MockCommunicationConfig',
]

