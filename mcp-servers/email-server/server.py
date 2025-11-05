#!/usr/bin/env python3
"""
Email MCP Server
Provides Gmail operations as MCP tools
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Gmail API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64


# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send']


class EmailMCPServer:
    """MCP Server for Gmail operations"""
    
    def __init__(self):
        self.server = Server("email-server")
        self.gmail_service = None
        self.credentials = None
        
        # Register tool handlers
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
    
    def _get_gmail_service(self):
        """Initialize Gmail service"""
        if self.gmail_service:
            return self.gmail_service
        
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), '../../token.json')
        creds_path = os.path.join(os.path.dirname(__file__), '../../credentials.json')
        
        # Load existing token
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.gmail_service = build('gmail', 'v1', credentials=creds)
        self.credentials = creds
        return self.gmail_service
    
    async def list_tools(self) -> List[Tool]:
        """List available MCP tools"""
        return [
            Tool(
                name="collect_emails",
                description="Collect emails from Gmail within a specified time range",
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
                description="Send an email via Gmail",
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
        """Collect emails from Gmail"""
        try:
            service = self._get_gmail_service()
            hours = args.get('hours', 24)
            max_results = args.get('max_results', 50)
            
            # Calculate time range
            after_date = datetime.now() - timedelta(hours=hours)
            query = f'after:{int(after_date.timestamp())}'
            
            # Fetch email list
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch email details
            emails = []
            for msg in messages[:max_results]:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                # Extract headers
                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Extract body
                body = ''
                if 'parts' in msg_data['payload']:
                    for part in msg_data['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(
                                part['body'].get('data', '')
                            ).decode('utf-8')
                            break
                elif 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
                    body = base64.urlsafe_b64decode(
                        msg_data['payload']['body']['data']
                    ).decode('utf-8')
                
                emails.append({
                    'from': from_addr,
                    'subject': subject,
                    'body': body[:500],  # Truncate long bodies
                    'date': date,
                    'timestamp': datetime.now().isoformat()
                })
            
            result = {
                'success': True,
                'count': len(emails),
                'emails': emails,
                'time_range_hours': hours
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
    
    async def _send_email(self, args: Dict[str, Any]) -> List[TextContent]:
        """Send an email via Gmail"""
        try:
            service = self._get_gmail_service()
            
            # Create message
            message = MIMEText(args['body_text'])
            message['to'] = args['to']
            message['subject'] = args['subject']
            
            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send email
            sent_message = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            result = {
                'success': True,
                'message_id': sent_message['id'],
                'to': args['to'],
                'subject': args['subject']
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
    server = EmailMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()

