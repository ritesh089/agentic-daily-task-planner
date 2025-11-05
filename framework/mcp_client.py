"""
MCP Client Integration for Framework
Provides tools to agents via MCP servers
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None


class MCPClient:
    """Client for interacting with MCP servers"""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.servers: Dict[str, MCPServerConfig] = {}
        self.contexts: Dict[str, Any] = {}
        
    async def connect_server(self, config: MCPServerConfig):
        """Connect to an MCP server"""
        print(f"🔌 Connecting to MCP server: {config.name}")
        
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or os.environ.copy()
        )
        
        try:
            # Create stdio client
            stdio_transport = await stdio_client(server_params)
            read_stream, write_stream = stdio_transport
            
            # Create session
            session = ClientSession(read_stream, write_stream)
            
            # Initialize session
            await session.initialize()
            
            # Store session
            self.sessions[config.name] = session
            self.servers[config.name] = config
            
            # List tools
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            
            print(f"✓ Connected to {config.name}: {len(tool_names)} tool(s) available")
            print(f"  Tools: {', '.join(tool_names)}")
            
            return session
            
        except Exception as e:
            print(f"✗ Failed to connect to {config.name}: {e}")
            raise
    
    async def disconnect_server(self, server_name: str):
        """Disconnect from an MCP server"""
        if server_name in self.sessions:
            try:
                # TODO: Properly close session when MCP SDK supports it
                del self.sessions[server_name]
                del self.servers[server_name]
                print(f"✓ Disconnected from {server_name}")
            except Exception as e:
                print(f"⚠️  Error disconnecting from {server_name}: {e}")
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for server_name in list(self.sessions.keys()):
            await self.disconnect_server(server_name)
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Call a tool on an MCP server"""
        if server_name not in self.sessions:
            raise ValueError(f"Not connected to server: {server_name}")
        
        session = self.sessions[server_name]
        
        try:
            result = await session.call_tool(tool_name, arguments)
            
            # Extract text content from result
            if hasattr(result, 'content') and result.content:
                text_content = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        text_content.append(item.text)
                
                if len(text_content) == 1:
                    # Try to parse as JSON
                    try:
                        return json.loads(text_content[0])
                    except json.JSONDecodeError:
                        return text_content[0]
                return text_content
            
            return result
            
        except Exception as e:
            print(f"✗ Tool call failed ({server_name}.{tool_name}): {e}")
            raise
    
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List all tools available on a server"""
        if server_name not in self.sessions:
            raise ValueError(f"Not connected to server: {server_name}")
        
        session = self.sessions[server_name]
        
        try:
            result = await session.list_tools()
            
            tools = []
            for tool in result.tools:
                tools.append({
                    'name': tool.name,
                    'description': tool.description,
                    'inputSchema': tool.inputSchema
                })
            
            return tools
            
        except Exception as e:
            print(f"✗ Failed to list tools for {server_name}: {e}")
            raise
    
    def get_tools_for_langchain(self, server_name: str) -> List[Any]:
        """
        Get MCP tools wrapped for LangChain agents
        Returns a list of tools that can be bound to a LangChain model
        """
        # This will be implemented to create LangChain-compatible tool wrappers
        # For now, we'll use direct MCP calls in agents
        pass


class MCPManager:
    """Manages MCP client lifecycle"""
    
    def __init__(self):
        self.client: Optional[MCPClient] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def initialize(self, servers: List[MCPServerConfig]):
        """Initialize MCP client and connect to servers"""
        print("🚀 Initializing MCP Client...")
        
        self.client = MCPClient()
        
        # Connect to all servers
        for server_config in servers:
            await self.client.connect_server(server_config)
        
        print(f"✓ MCP Client initialized with {len(servers)} server(s)")
        return self.client
    
    async def shutdown(self):
        """Shutdown MCP client and disconnect from servers"""
        if self.client:
            print("🔌 Shutting down MCP Client...")
            await self.client.disconnect_all()
            self.client = None
            print("✓ MCP Client shutdown complete")
    
    def get_client(self) -> Optional[MCPClient]:
        """Get the MCP client instance"""
        return self.client


# Global MCP manager instance
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP manager"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


async def init_mcp_client(use_mocks: bool = False) -> MCPClient:
    """
    Initialize MCP client with appropriate servers (real or mock)
    
    Args:
        use_mocks: If True, use mock MCP servers for testing
    
    Returns:
        MCPClient instance
    """
    manager = get_mcp_manager()
    
    # Determine which servers to use
    if use_mocks:
        servers = [
            MCPServerConfig(
                name="email",
                command=sys.executable,
                args=[
                    os.path.join(
                        os.path.dirname(__file__),
                        "../mcp-servers/email-server/mock_server.py"
                    )
                ]
            ),
            MCPServerConfig(
                name="slack",
                command=sys.executable,
                args=[
                    os.path.join(
                        os.path.dirname(__file__),
                        "../mcp-servers/slack-server/mock_server.py"
                    )
                ]
            )
        ]
    else:
        servers = [
            MCPServerConfig(
                name="email",
                command=sys.executable,
                args=[
                    os.path.join(
                        os.path.dirname(__file__),
                        "../mcp-servers/email-server/server.py"
                    )
                ]
            ),
            MCPServerConfig(
                name="slack",
                command=sys.executable,
                args=[
                    os.path.join(
                        os.path.dirname(__file__),
                        "../mcp-servers/slack-server/server.py"
                    )
                ]
            )
        ]
    
    client = await manager.initialize(servers)
    return client


async def shutdown_mcp_client():
    """Shutdown MCP client"""
    manager = get_mcp_manager()
    await manager.shutdown()


def run_async_tool_call(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Helper function to call MCP tools from synchronous code (like LangGraph nodes)
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to call
        arguments: Tool arguments
    
    Returns:
        Tool result
    """
    manager = get_mcp_manager()
    client = manager.get_client()
    
    if not client:
        raise RuntimeError("MCP client not initialized. Call init_mcp_client() first.")
    
    # Run in event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If loop is already running (e.g., in Jupyter), create a task
        future = asyncio.ensure_future(client.call_tool(server_name, tool_name, arguments))
        # Wait for it synchronously (this will block, but that's expected for tool calls)
        return asyncio.run_coroutine_threadsafe(
            client.call_tool(server_name, tool_name, arguments),
            loop
        ).result()
    else:
        # If no loop is running, use asyncio.run
        return asyncio.run(client.call_tool(server_name, tool_name, arguments))

