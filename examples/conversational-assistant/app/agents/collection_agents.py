"""
Collection Agents
Collect emails and Slack messages via MCP
"""

from typing import Dict, Any
from framework import run_async_tool_call


def collect_data_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect emails and Slack messages via MCP tool servers
    This runs once at the start to load all messages into memory
    """
    print("📥 Collecting your recent messages...\n")
    
    # Collect emails via MCP
    try:
        email_result = run_async_tool_call(
            server_name="email",
            tool_name="collect_emails",
            arguments={
                "hours": 24,
                "max_results": 50
            }
        )
        
        if email_result.get('success'):
            emails = email_result.get('emails', [])
            state['emails'] = emails
            is_mock = email_result.get('mock', False)
            mock_label = "[MOCK] " if is_mock else ""
            print(f"✓ {mock_label}Collected {len(emails)} emails")
        else:
            error_msg = email_result.get('error', 'Unknown error')
            print(f"⚠️  Email collection failed: {error_msg}")
            state['emails'] = []
            state.setdefault('errors', []).append(f"Email: {error_msg}")
    
    except Exception as e:
        error_msg = f"Email MCP error: {str(e)}"
        print(f"⚠️  {error_msg}")
        state['emails'] = []
        state.setdefault('errors', []).append(error_msg)
    
    # Collect Slack messages via MCP
    try:
        slack_result = run_async_tool_call(
            server_name="slack",
            tool_name="collect_messages",
            arguments={
                "hours": 24,
                "include_dms": True,
                "include_channels": True,
                "include_mentions": True
            }
        )
        
        if slack_result.get('success'):
            messages = slack_result.get('messages', [])
            state['slack_messages'] = messages
            is_mock = slack_result.get('mock', False)
            mock_label = "[MOCK] " if is_mock else ""
            print(f"✓ {mock_label}Collected {len(messages)} Slack messages")
        else:
            error_msg = slack_result.get('error', 'Unknown error')
            print(f"⚠️  Slack collection failed: {error_msg}")
            state['slack_messages'] = []
            state.setdefault('errors', []).append(f"Slack: {error_msg}")
    
    except Exception as e:
        error_msg = f"Slack MCP error: {str(e)}"
        print(f"⚠️  {error_msg}")
        state['slack_messages'] = []
        state.setdefault('errors', []).append(error_msg)
    
    total_messages = len(state.get('emails', [])) + len(state.get('slack_messages', []))
    print(f"\n✓ Total: {total_messages} messages loaded into memory\n")
    
    return state

