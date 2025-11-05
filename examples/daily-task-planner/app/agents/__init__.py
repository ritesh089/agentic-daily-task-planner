"""
Agent Module
Contains all agent implementations for the daily task planner
"""

from app.agents.email_agents import email_collector_agent, email_summarizer_agent
from app.agents.slack_agents import slack_collector_agent, slack_summarizer_agent
from app.agents.task_agents import task_extractor_agent, task_prioritizer_agent
from app.agents.communication_agents import email_sender_agent

__all__ = [
    'email_collector_agent',
    'email_summarizer_agent',
    'slack_collector_agent',
    'slack_summarizer_agent',
    'task_extractor_agent',
    'task_prioritizer_agent',
    'email_sender_agent'
]

