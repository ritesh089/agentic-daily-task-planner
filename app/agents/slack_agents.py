"""
Slack Agent Module
Handles Slack message collection and summarization using Slack SDK and LLM
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langchain_ollama import ChatOllama

# ============================================================================
# Slack Collector Agent
# ============================================================================

def slack_collector_agent(state: Dict) -> Dict:
    """Collects messages from Slack (DMs, channels, mentions)"""
    print(f"💬 Slack Collector: Fetching messages from last {state['time_range_hours']} hours...")
    
    try:
        # Load Slack credentials
        with open('slack_credentials.json', 'r') as f:
            slack_config = json.load(f)
        
        client = WebClient(token=slack_config['user_token'])
        cutoff_timestamp = (datetime.now(timezone.utc) - timedelta(hours=state['time_range_hours'])).timestamp()
        
        collected_messages = []
        
        # 1. Fetch Direct Messages
        try:
            im_list = client.conversations_list(types="im")
            for channel in im_list['channels']:
                history = client.conversations_history(
                    channel=channel['id'],
                    oldest=str(cutoff_timestamp)
                )
                for message in history.get('messages', []):
                    if 'text' in message and 'user' in message:
                        user_info = client.users_info(user=message['user'])
                        collected_messages.append({
                            'type': 'DM',
                            'from': user_info['user']['real_name'],
                            'text': message['text'][:500],
                            'timestamp': message['ts']
                        })
        except SlackApiError as e:
            state['errors'].append(f"DM fetch error: {e.response['error']}")
        
        # 2. Fetch from specified channels
        for channel_id in slack_config.get('channels', []):
            try:
                channel_info = client.conversations_info(channel=channel_id)
                history = client.conversations_history(
                    channel=channel_id,
                    oldest=str(cutoff_timestamp)
                )
                for message in history.get('messages', []):
                    if 'text' in message and 'user' in message:
                        user_info = client.users_info(user=message['user'])
                        collected_messages.append({
                            'type': 'Channel',
                            'channel': channel_info['channel']['name'],
                            'from': user_info['user']['real_name'],
                            'text': message['text'][:500],
                            'timestamp': message['ts']
                        })
            except SlackApiError as e:
                state['errors'].append(f"Channel {channel_id} fetch error: {e.response['error']}")
        
        # 3. Fetch mentions (search for @mentions)
        # Note: search.messages requires a different token type (not user tokens)
        # Skipping mentions for user tokens to avoid errors
        try:
            # Get current user ID
            auth_test = client.auth_test()
            user_id = auth_test['user_id']
            
            # Try to search for mentions (may not work with user tokens)
            search_result = client.search_messages(
                query=f"<@{user_id}>",
                sort='timestamp',
                count=100
            )
            for match in search_result.get('messages', {}).get('matches', []):
                if float(match['ts']) >= cutoff_timestamp:
                    collected_messages.append({
                        'type': 'Mention',
                        'channel': match.get('channel', {}).get('name', 'Unknown'),
                        'from': match.get('username', 'Unknown'),
                        'text': match['text'][:500],
                        'timestamp': match['ts']
                    })
        except SlackApiError as e:
            # Don't treat as error - search.messages often not available for user tokens
            if e.response['error'] == 'not_allowed_token_type':
                print(f"   ℹ️  Mentions search not available with this token type (skipping)")
            else:
                state['errors'].append(f"Mentions fetch error: {e.response['error']}")
        
        state['slack_messages'] = collected_messages
        print(f"✓ Collected {len(collected_messages)} Slack messages")
        
    except FileNotFoundError:
        error_msg = "slack_credentials.json not found. Skipping Slack collection."
        state['errors'].append(error_msg)
        state['slack_messages'] = []
        print(f"⚠ {error_msg}")
    except Exception as e:
        error_msg = f"Slack collection error: {str(e)}"
        state['errors'].append(error_msg)
        state['slack_messages'] = []
        print(f"✗ {error_msg}")
    
    return state

# ============================================================================
# Slack Summarizer Agent
# ============================================================================

def slack_summarizer_agent(state: Dict) -> Dict:
    """Summarizes collected Slack messages using LLM"""
    print("🤖 Slack Summarizer: Generating Slack summary...")
    
    messages = state['slack_messages']
    
    if not messages:
        state['slack_summary'] = "No Slack messages found in the specified time range."
        print("✓ No Slack messages to summarize")
        return state
    
    # Format Slack messages for LLM
    slack_text = ""
    for i, msg in enumerate(messages, 1):
        slack_text += f"\n{i}. [{msg['type']}] From: {msg['from']}\n"
        if 'channel' in msg:
            slack_text += f"   Channel: {msg['channel']}\n"
        slack_text += f"   Message: {msg['text'][:300]}...\n"
    
    prompt = f"""You are a Slack assistant. Provide a concise summary of these Slack messages in 3-4 bullet points.
Focus on the most important conversations, requests, and actionable items.

Slack messages from last {state['time_range_hours']} hours ({len(messages)} total):
{slack_text}

Provide a clear, actionable summary:"""
    
    try:
        llm = ChatOllama(model="llama3.2", temperature=0.7)
        response = llm.invoke(prompt)
        state['slack_summary'] = response.content
        print("✓ Slack summary generated")
    except Exception as e:
        error_msg = f"Slack summarization error: {str(e)}"
        state['errors'].append(error_msg)
        state['slack_summary'] = f"Error generating summary: {str(e)}"
        print(f"✗ {error_msg}")
    
    return state

