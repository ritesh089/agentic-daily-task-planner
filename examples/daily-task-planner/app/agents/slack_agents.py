"""
Slack Agent Module (MCP-based)
Agents that use MCP tools for Slack operations
"""

from typing import Dict
from framework import run_async_tool_call


# ============================================================================
# Slack Collector Agent (MCP-based)
# ============================================================================

def slack_collector_agent(state: Dict) -> Dict:
    """
    Collects Slack messages via MCP slack server
    Uses the 'collect_messages' tool provided by the slack MCP server
    """
    print("💬 Slack Collector (MCP): Fetching messages...")
    
    time_range_hours = state.get('time_range_hours', 24)
    
    try:
        # Call MCP tool
        result = run_async_tool_call(
            server_name="slack",
            tool_name="collect_messages",
            arguments={
                "hours": time_range_hours,
                "include_dms": True,
                "include_channels": True,
                "include_mentions": True
            }
        )
        
        if result.get('success'):
            messages = result.get('messages', [])
            state['slack_messages'] = messages
            
            is_mock = result.get('mock', False)
            mock_label = "[MOCK] " if is_mock else ""
            
            print(f"✓ {mock_label}Retrieved {len(messages)} message(s) from last {time_range_hours} hours")
            
            if len(messages) == 0:
                print("ℹ️  No Slack messages found in the specified time range")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"✗ Slack collection failed: {error_msg}")
            state.setdefault('errors', []).append(f"Slack collection: {error_msg}")
            state['slack_messages'] = []
    
    except Exception as e:
        error_msg = f"MCP tool call failed: {str(e)}"
        print(f"✗ {error_msg}")
        state.setdefault('errors', []).append(error_msg)
        state['slack_messages'] = []
    
    return state


# ============================================================================
# Slack Summarizer Agent
# ============================================================================

def slack_summarizer_agent(state: Dict) -> Dict:
    """
    Summarizes collected Slack messages
    This agent doesn't need MCP - it's a pure LLM task
    """
    print("🤖 Slack Summarizer: Analyzing messages...")
    
    messages = state['slack_messages']
    
    if not messages:
        state['slack_summary'] = "No messages to summarize"
        print("ℹ️  No messages to summarize")
        return state
    
    # Create summary (in real app, this would use LLM)
    summary_lines = [
        f"Total Messages: {len(messages)}",
        "\nKey Messages:"
    ]
    
    # Group by type
    dms = [m for m in messages if m.get('type') == 'dm']
    mentions = [m for m in messages if m.get('type') == 'mention']
    channels = [m for m in messages if m.get('type') == 'channel']
    
    if dms:
        summary_lines.append(f"\nDirect Messages ({len(dms)}):")
        for msg in dms[:3]:
            from_user = msg.get('from', 'Unknown')
            text = msg.get('text', '')[:50]
            summary_lines.append(f"  • {from_user}: {text}...")
    
    if mentions:
        summary_lines.append(f"\nMentions ({len(mentions)}):")
        for msg in mentions[:3]:
            from_user = msg.get('from', 'Unknown')
            channel = msg.get('channel', 'Unknown')
            text = msg.get('text', '')[:50]
            summary_lines.append(f"  • {from_user} in #{channel}: {text}...")
    
    if channels:
        summary_lines.append(f"\nChannel Messages ({len(channels)}):")
        for msg in channels[:3]:
            from_user = msg.get('from', 'Unknown')
            channel = msg.get('channel', 'Unknown')
            text = msg.get('text', '')[:50]
            summary_lines.append(f"  • {from_user} in #{channel}: {text}...")
    
    state['slack_summary'] = '\n'.join(summary_lines)
    print(f"✓ Summarized {len(messages)} message(s)")
    
    return state

