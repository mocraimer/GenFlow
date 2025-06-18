"""
Core MCP (Model Context Protocol) client implementation.

This module handles the MCP protocol communication via stdio transport,
focusing on tool discovery and execution without reimplementing AI logic.
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MCPTransportType(Enum):
    """Supported MCP transport types."""
    STDIO = "stdio"
    HTTP = "http"  # Future support


@dataclass
class MCPTool:
    """Represents an MCP tool definition."""
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    command: str
    args: list[str] | None = None
    env: dict[str, str] | None = None
    transport: MCPTransportType = MCPTransportType.STDIO
    timeout: float = 30.0


class MCPError(Exception):
    """Base exception for MCP-related errors."""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails."""
    pass


class MCPProtocolError(MCPError):
    """Raised when MCP protocol communication fails."""
    pass


class MCPClient:
    """
    MCP client for communicating with MCP servers via stdio.
    
    Handles the MCP protocol for tool discovery and execution,
    designed to work seamlessly with Pydantic AI agents.
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: subprocess.Popen[str] | None = None
        self._tools: list[MCPTool] = []
        self._connected = False
        self._request_id = 0

    async def connect(self) -> None:
        """Initialize connection to the MCP server."""
        if self._connected:
            return

        try:
            # Start the MCP server process
            env = dict(os.environ)
            if self.config.env:
                env.update(self.config.env)

            # Security validation: ensure command is not empty and is a string
            if not self.config.command or not isinstance(self.config.command, str):
                raise MCPConnectionError("Invalid MCP server command")
            
            command = [self.config.command]
            if self.config.args:
                # Validate args are strings
                if not all(isinstance(arg, str) for arg in self.config.args):
                    raise MCPConnectionError("Invalid MCP server arguments - must be strings")
                command.extend(self.config.args)

            # Security: Using subprocess with shell=False (default) and explicit command list
            # This is safe as we're not using shell interpretation
            # nosec B603 - subprocess call with shell=False is safe
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                env=env,
                shell=False  # Explicitly set for clarity
            )

            # Send initialize request
            initialize_request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "airflow-ai-bridge",
                        "version": "0.1.0"
                    }
                }
            }

            response = await self._send_request(initialize_request)
            
            if "error" in response:
                raise MCPConnectionError(f"MCP server initialization failed: {response['error']}")

            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            await self._send_notification(initialized_notification)

            self._connected = True
            logger.info(f"Successfully connected to MCP server: {self.config.command}")

        except Exception as e:
            await self.disconnect()
            raise MCPConnectionError(f"Failed to connect to MCP server {self.config.command}: {e}") from e

    async def disconnect(self) -> None:
        """Close the connection to the MCP server."""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.sleep(0.1)
                if self._process.poll() is None:
                    self._process.kill()
            except Exception as e:
                logger.warning(f"Error during MCP server shutdown: {e}")
            finally:
                self._process = None

        self._connected = False
        self._tools.clear()

    async def list_tools(self) -> list[MCPTool]:
        """Get available tools from the MCP server."""
        if not self._connected:
            await self.connect()

        if self._tools:  # Cache tools after first request
            return self._tools

        try:
            tools_request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/list"
            }

            response = await self._send_request(tools_request)
            
            if "error" in response:
                raise MCPProtocolError(f"Failed to list tools: {response['error']}")

            tools_data = response.get("result", {}).get("tools", [])
            self._tools = [
                MCPTool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {})
                )
                for tool in tools_data
            ]

            logger.info(f"Discovered {len(self._tools)} tools from MCP server")
            return self._tools

        except Exception as e:
            raise MCPProtocolError(f"Error listing MCP tools: {e}") from e

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool on the MCP server."""
        if not self._connected:
            await self.connect()

        try:
            tool_request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments
                }
            }

            response = await self._send_request(tool_request)
            
            if "error" in response:
                error_info = response["error"]
                raise MCPProtocolError(
                    f"Tool '{name}' execution failed: {error_info.get('message', 'Unknown error')}"
                )

            result = response.get("result", {})
            
            # Extract content from MCP response format
            content = result.get("content", [])
            if content:
                # Handle different content types (text, images, etc.)
                text_content = []
                for item in content:
                    if item.get("type") == "text":
                        text_content.append(item.get("text", ""))
                
                return "\n".join(text_content) if text_content else result
            
            return result

        except Exception as e:
            if isinstance(e, MCPProtocolError):
                raise
            raise MCPProtocolError(f"Error calling MCP tool '{name}': {e}") from e

    async def _send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for response."""
        if not self._process or not self._process.stdin:
            raise MCPConnectionError("MCP server process not available")

        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self._process.stdin.write(request_str)
            self._process.stdin.flush()

            # Wait for response
            response_line = await asyncio.wait_for(
                self._read_line(),
                timeout=self.config.timeout
            )

            if not response_line:
                raise MCPProtocolError("Empty response from MCP server")

            response: dict[str, Any] = json.loads(response_line)
            return response

        except asyncio.TimeoutError:
            raise MCPProtocolError(f"MCP server request timeout ({self.config.timeout}s)") from None
        except json.JSONDecodeError as e:
            raise MCPProtocolError(f"Invalid JSON response from MCP server: {e}") from e

    async def _send_notification(self, notification: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._process or not self._process.stdin:
            raise MCPConnectionError("MCP server process not available")

        notification_str = json.dumps(notification) + "\n"
        self._process.stdin.write(notification_str)
        self._process.stdin.flush()

    async def _read_line(self) -> str:
        """Read a line from the MCP server stdout."""
        if not self._process or not self._process.stdout:
            raise MCPConnectionError("MCP server process not available")

        # Use asyncio to read from subprocess stdout
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process.stdout.readline)

    def _next_request_id(self) -> int:
        """Generate next request ID."""
        self._request_id += 1
        return self._request_id

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()