#!/usr/bin/env python3
"""
Slack MCP Server
Provides Slack operations as MCP tools
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Slack SDK
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackMCPServer:
    """MCP Server for Slack operations"""
    
    def __init__(self):
        self.server = Server("slack-server")
        self.slack_client = None
        
        # Register tool handlers
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
    
    def _get_slack_client(self):
        """Initialize Slack client"""
        if self.slack_client:
            return self.slack_client
        
        # Load Slack credentials
        creds_path = os.path.join(os.path.dirname(__file__), '../../slack_credentials.json')
        
        if os.path.exists(creds_path):
            with open(creds_path, 'r') as f:
                creds = json.load(f)
                token = creds.get('user_token')
                if token:
                    self.slack_client = WebClient(token=token)
                    return self.slack_client
        
        raise ValueError("Slack credentials not found or invalid")
    
    async def list_tools(self) -> List[Tool]:
        """List available MCP tools"""
        return [
            Tool(
                name="collect_messages",
                description="Collect Slack messages (DMs, channels, mentions) within a time range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hours": {
                            "type": "number",
                            "description": "Number of hours to look back (default: 24)",
                            "default": 24
                        },
                        "include_dms": {
                            "type": "boolean",
                            "description": "Include direct messages",
                            "default": True
                        },
                        "include_channels": {
                            "type": "boolean",
                            "description": "Include channel messages",
                            "default": True
                        },
                        "include_mentions": {
                            "type": "boolean",
                            "description": "Include mentions",
                            "default": True
                        },
                        "channels": {
                            "type": "array",
                            "description": "Specific channel IDs to monitor (optional)",
                            "items": {"type": "string"}
                        }
                    }
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a tool call"""
        if name == "collect_messages":
            return await self._collect_messages(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def _collect_messages(self, args: Dict[str, Any]) -> List[TextContent]:
        """Collect messages from Slack"""
        try:
            client = self._get_slack_client()
            hours = args.get('hours', 24)
            include_dms = args.get('include_dms', True)
            include_channels = args.get('include_channels', True)
            include_mentions = args.get('include_mentions', True)
            specific_channels = args.get('channels', [])
            
            # Calculate time range
            oldest = (datetime.now() - timedelta(hours=hours)).timestamp()
            
            messages = []
            
            # Get user ID for filtering mentions
            auth_response = client.auth_test()
            user_id = auth_response['user_id']
            
            # Collect DMs
            if include_dms:
                try:
                    conversations = client.conversations_list(
                        types='im',
                        limit=100
                    )
                    
                    for conv in conversations['channels']:
                        history = client.conversations_history(
                            channel=conv['id'],
                            oldest=oldest,
                            limit=100
                        )
                        
                        for msg in history.get('messages', []):
                            if msg.get('type') == 'message' and 'subtype' not in msg:
                                # Get user info
                                user_info = client.users_info(user=msg.get('user', ''))
                                user_name = user_info['user']['real_name'] if user_info['ok'] else 'Unknown'
                                
                                messages.append({
                                    'from': user_name,
                                    'channel': 'DM',
                                    'type': 'dm',
                                    'text': msg.get('text', ''),
                                    'timestamp': datetime.fromtimestamp(
                                        float(msg['ts'])
                                    ).isoformat()
                                })
                except SlackApiError as e:
                    print(f"Error fetching DMs: {e}")
            
            # Collect channel messages and mentions
            if include_channels or include_mentions:
                try:
                    # Get all channels or specific ones
                    if specific_channels:
                        channels_to_check = specific_channels
                    else:
                        conversations = client.conversations_list(
                            types='public_channel,private_channel',
                            limit=100
                        )
                        channels_to_check = [c['id'] for c in conversations['channels']]
                    
                    for channel_id in channels_to_check:
                        try:
                            # Get channel info
                            channel_info = client.conversations_info(channel=channel_id)
                            channel_name = channel_info['channel']['name']
                            
                            # Get messages
                            history = client.conversations_history(
                                channel=channel_id,
                                oldest=oldest,
                                limit=100
                            )
                            
                            for msg in history.get('messages', []):
                                if msg.get('type') == 'message' and 'subtype' not in msg:
                                    text = msg.get('text', '')
                                    is_mention = f'<@{user_id}>' in text
                                    
                                    # Filter based on settings
                                    if (include_mentions and is_mention) or \
                                       (include_channels and not is_mention):
                                        
                                        # Get user info
                                        user_info = client.users_info(user=msg.get('user', ''))
                                        user_name = user_info['user']['real_name'] if user_info['ok'] else 'Unknown'
                                        
                                        messages.append({
                                            'from': user_name,
                                            'channel': channel_name,
                                            'type': 'mention' if is_mention else 'channel',
                                            'text': text,
                                            'timestamp': datetime.fromtimestamp(
                                                float(msg['ts'])
                                            ).isoformat()
                                        })
                        except SlackApiError:
                            continue  # Skip channels we can't access
                            
                except SlackApiError as e:
                    print(f"Error fetching channels: {e}")
            
            result = {
                'success': True,
                'count': len(messages),
                'messages': messages,
                'time_range_hours': hours,
                'filters': {
                    'dms': include_dms,
                    'channels': include_channels,
                    'mentions': include_mentions
                }
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'success': False,
                    'error': str(e)
                }, indent=2)
            )]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    server = SlackMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()

