#!/usr/bin/env python3
"""
Mock Email MCP Server
Provides simulated Gmail operations for testing
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Mock configuration
class MockEmailConfig:
    """Configuration for mock email behavior"""
    COLLECTION_FAILS = False
    SEND_FAILS = False
    COLLECTION_DELAY = 0.1
    SEND_DELAY = 0.1
    
    # Sample mock emails
    MOCK_EMAILS = [
        {
            'from': 'alice@example.com',
            'subject': 'Q4 Report Review',
            'body': 'Please review the attached Q4 financial report.',
            'date': 'Mon, 4 Nov 2024 09:30:00 -0800'
        },
        {
            'from': 'bob@example.com',
            'subject': 'Meeting Request',
            'body': 'Can we schedule a meeting to discuss the project timeline?',
            'date': 'Mon, 4 Nov 2024 10:15:00 -0800'
        },
        {
            'from': 'carol@example.com',
            'subject': 'Urgent: Server Issue',
            'body': 'The production server is experiencing high load. Please investigate.',
            'date': 'Mon, 4 Nov 2024 11:00:00 -0800'
        }
    ]
    
    @classmethod
    def enable_collection_failure(cls):
        cls.COLLECTION_FAILS = True
    
    @classmethod
    def disable_collection_failure(cls):
        cls.COLLECTION_FAILS = False
    
    @classmethod
    def enable_send_failure(cls):
        cls.SEND_FAILS = True
    
    @classmethod
    def disable_send_failure(cls):
        cls.SEND_FAILS = False


class MockEmailMCPServer:
    """Mock MCP Server for Gmail operations"""
    
    def __init__(self):
        self.server = Server("mock-email-server")
        
        # Register tool handlers
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
    
    async def list_tools(self) -> List[Tool]:
        """List available MCP tools"""
        return [
            Tool(
                name="collect_emails",
                description="[MOCK] Collect emails from Gmail within a specified time range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hours": {
                            "type": "number",
                            "description": "Number of hours to look back (default: 24)",
                            "default": 24
                        },
                        "max_results": {
                            "type": "number",
                            "description": "Maximum number of emails to retrieve (default: 50)",
                            "default": 50
                        }
                    }
                }
            ),
            Tool(
                name="send_email",
                description="[MOCK] Send an email via Gmail",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject"
                        },
                        "body_text": {
                            "type": "string",
                            "description": "Plain text email body"
                        },
                        "body_html": {
                            "type": "string",
                            "description": "HTML email body (optional)"
                        }
                    },
                    "required": ["to", "subject", "body_text"]
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a tool call"""
        if name == "collect_emails":
            return await self._collect_emails(arguments)
        elif name == "send_email":
            return await self._send_email(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def _collect_emails(self, args: Dict[str, Any]) -> List[TextContent]:
        """Mock email collection"""
        await asyncio.sleep(MockEmailConfig.COLLECTION_DELAY)
        
        if MockEmailConfig.COLLECTION_FAILS:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'success': False,
                    'error': '[MOCK] Email collection failed - simulated failure'
                }, indent=2)
            )]
        
        hours = args.get('hours', 24)
        max_results = args.get('max_results', 50)
        
        # Return mock emails with timestamps
        emails = []
        for email in MockEmailConfig.MOCK_EMAILS[:max_results]:
            email_copy = email.copy()
            email_copy['timestamp'] = datetime.now().isoformat()
            emails.append(email_copy)
        
        result = {
            'success': True,
            'count': len(emails),
            'emails': emails,
            'time_range_hours': hours,
            'mock': True
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    async def _send_email(self, args: Dict[str, Any]) -> List[TextContent]:
        """Mock email sending"""
        await asyncio.sleep(MockEmailConfig.SEND_DELAY)
        
        if MockEmailConfig.SEND_FAILS:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'success': False,
                    'error': '[MOCK] Email sending failed - simulated failure'
                }, indent=2)
            )]
        
        result = {
            'success': True,
            'message_id': f'mock-{datetime.now().timestamp()}',
            'to': args['to'],
            'subject': args['subject'],
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
    server = MockEmailMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()

