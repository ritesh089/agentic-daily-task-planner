#!/usr/bin/env python3
"""
Mock Slack MCP Server
Provides simulated Slack operations for testing
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Mock configuration
class MockSlackConfig:
    """Configuration for mock Slack behavior"""
    COLLECTION_FAILS = False
    COLLECTION_DELAY = 0.1
    
    # Sample mock messages
    MOCK_MESSAGES = [
        {
            'from': 'Alice Johnson',
            'channel': 'DM',
            'type': 'dm',
            'text': 'Hey, did you see the latest sprint update?'
        },
        {
            'from': 'Bob Smith',
            'channel': 'engineering',
            'type': 'channel',
            'text': 'The new feature is ready for QA testing.'
        },
        {
            'from': 'Carol White',
            'channel': 'general',
            'type': 'mention',
            'text': '<@U123456> Can you review the PR when you get a chance?'
        }
    ]
    
    @classmethod
    def enable_collection_failure(cls):
        cls.COLLECTION_FAILS = True
    
    @classmethod
    def disable_collection_failure(cls):
        cls.COLLECTION_FAILS = False


class MockSlackMCPServer:
    """Mock MCP Server for Slack operations"""
    
    def __init__(self):
        self.server = Server("mock-slack-server")
        
        # Register tool handlers
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
    
    async def list_tools(self) -> List[Tool]:
        """List available MCP tools"""
        return [
            Tool(
                name="collect_messages",
                description="[MOCK] Collect Slack messages (DMs, channels, mentions) within a time range",
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
        """Mock message collection"""
        await asyncio.sleep(MockSlackConfig.COLLECTION_DELAY)
        
        if MockSlackConfig.COLLECTION_FAILS:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'success': False,
                    'error': '[MOCK] Slack message collection failed - simulated failure'
                }, indent=2)
            )]
        
        hours = args.get('hours', 24)
        include_dms = args.get('include_dms', True)
        include_channels = args.get('include_channels', True)
        include_mentions = args.get('include_mentions', True)
        
        # Filter mock messages based on settings
        messages = []
        for msg in MockSlackConfig.MOCK_MESSAGES:
            if (msg['type'] == 'dm' and include_dms) or \
               (msg['type'] == 'channel' and include_channels) or \
               (msg['type'] == 'mention' and include_mentions):
                msg_copy = msg.copy()
                msg_copy['timestamp'] = datetime.now().isoformat()
                messages.append(msg_copy)
        
        result = {
            'success': True,
            'count': len(messages),
            'messages': messages,
            'time_range_hours': hours,
            'filters': {
                'dms': include_dms,
                'channels': include_channels,
                'mentions': include_mentions
            },
            'mock': True
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    async def run(self):
        """Run the mock MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    server = MockSlackMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()

