"""
Email Agent Module (MCP-based)
Agents that use MCP tools for Gmail operations
"""

from typing import Dict
from framework import run_async_tool_call


# ============================================================================
# Email Collector Agent (MCP-based)
# ============================================================================

def email_collector_agent(state: Dict) -> Dict:
    """
    Collects emails via MCP email server
    Uses the 'collect_emails' tool provided by the email MCP server
    """
    print("📧 Email Collector (MCP): Fetching emails...")
    
    time_range_hours = state.get('time_range_hours', 24)
    
    try:
        # Call MCP tool
        result = run_async_tool_call(
            server_name="email",
            tool_name="collect_emails",
            arguments={
                "hours": time_range_hours,
                "max_results": 50
            }
        )
        
        if result.get('success'):
            emails = result.get('emails', [])
            state['emails'] = emails
            
            is_mock = result.get('mock', False)
            mock_label = "[MOCK] " if is_mock else ""
            
            print(f"✓ {mock_label}Retrieved {len(emails)} email(s) from last {time_range_hours} hours")
            
            if len(emails) == 0:
                print("ℹ️  No emails found in the specified time range")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"✗ Email collection failed: {error_msg}")
            state.setdefault('errors', []).append(f"Email collection: {error_msg}")
            state['emails'] = []
    
    except Exception as e:
        error_msg = f"MCP tool call failed: {str(e)}"
        print(f"✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        state['emails'] = []
    
    return state


# ============================================================================
# Email Summarizer Agent
# ============================================================================

def email_summarizer_agent(state: Dict) -> Dict:
    """
    Summarizes collected emails
    This agent doesn't need MCP - it's a pure LLM task
    """
    print("🤖 Email Summarizer: Analyzing emails...")
    
    emails = state['emails']
    
    if not emails:
        state['email_summary'] = "No emails to summarize"
        print("ℹ️  No emails to summarize")
        return state
    
    # Create summary (in real app, this would use LLM)
    summary_lines = [
        f"Total Emails: {len(emails)}",
        "\nKey Communications:"
    ]
    
    for i, email in enumerate(emails[:5], 1):  # Summarize top 5
        from_addr = email.get('from', 'Unknown')
        subject = email.get('subject', 'No Subject')
        summary_lines.append(f"{i}. From {from_addr}: {subject}")
    
    if len(emails) > 5:
        summary_lines.append(f"... and {len(emails) - 5} more emails")
    
    state['email_summary'] = '\n'.join(summary_lines)
    print(f"✓ Summarized {len(emails)} email(s)")
    
    return state

