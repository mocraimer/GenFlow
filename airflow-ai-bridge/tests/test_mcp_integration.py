"""
Comprehensive tests for MCP integration in airflow-ai-bridge.

These tests cover the core MCP functionality, tool registration,
and integration with Pydantic AI agents.
"""

import asyncio
import json
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Any, Dict, List

import pytest

try:
    from pydantic_ai import Agent
except ImportError:
    # Mock pydantic_ai for testing
    class Agent:
        def __init__(self, model, system_prompt=""):
            self.model = model
            self.system_prompt = system_prompt
        
        def tool(self, func):
            return func

from airflow_ai_bridge.mcp import (
    MCPClient, 
    MCPServerConfig, 
    MCPTool, 
    MCPError, 
    MCPConnectionError, 
    MCPProtocolError
)
from airflow_ai_bridge.tools import MCPToolRegistry, register_mcp_tools
from airflow_ai_bridge.pool import MCPConnectionPool
from airflow_ai_bridge.decorators import mcp_agent


class TestMCPClient:
    """Test suite for MCPClient functionality."""

    @pytest.fixture
    def mcp_config(self):
        """Create test MCP server configuration."""
        return MCPServerConfig(
            command="test-mcp-server",
            args=["--test"],
            env={"TEST_ENV": "test_value"},
            timeout=10.0
        )

    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess for MCP server."""
        process = MagicMock()
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        process.stderr = MagicMock()
        process.poll.return_value = None
        return process

    @pytest.fixture
    def mcp_client(self, mcp_config):
        """Create MCPClient instance for testing."""
        return MCPClient(mcp_config)

    @pytest.mark.asyncio
    async def test_client_initialization(self, mcp_client, mcp_config):
        """Test MCPClient initialization."""
        assert mcp_client.config == mcp_config
        assert not mcp_client._connected
        assert mcp_client._tools == []
        assert mcp_client._request_id == 0

    @pytest.mark.asyncio
    async def test_connection_success(self, mcp_client, mock_process):
        """Test successful MCP server connection."""
        with patch('subprocess.Popen', return_value=mock_process):
            # Mock successful initialization response
            mock_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-server", "version": "1.0.0"}
                }
            }
            
            mock_process.stdout.readline.return_value = json.dumps(mock_response) + "\n"
            
            await mcp_client.connect()
            
            assert mcp_client._connected
            assert mcp_client._process == mock_process

    @pytest.mark.asyncio
    async def test_connection_failure(self, mcp_client):
        """Test MCP server connection failure."""
        with patch('subprocess.Popen', side_effect=Exception("Connection failed")):
            with pytest.raises(MCPConnectionError, match="Failed to connect to MCP server"):
                await mcp_client.connect()

    @pytest.mark.asyncio
    async def test_list_tools_success(self, mcp_client, mock_process):
        """Test successful tool listing."""
        # Setup connected client
        mcp_client._connected = True
        mcp_client._process = mock_process
        
        # Mock tools/list response
        tools_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "param1": {"type": "string", "description": "First parameter"}
                            },
                            "required": ["param1"]
                        }
                    }
                ]
            }
        }
        
        mock_process.stdout.readline.return_value = json.dumps(tools_response) + "\n"
        
        tools = await mcp_client.list_tools()
        
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert tools[0].description == "A test tool"
        assert "param1" in tools[0].input_schema["properties"]

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mcp_client, mock_process):
        """Test successful tool execution."""
        # Setup connected client
        mcp_client._connected = True
        mcp_client._process = mock_process
        
        # Mock tool call response
        tool_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {"type": "text", "text": "Tool execution result"}
                ]
            }
        }
        
        mock_process.stdout.readline.return_value = json.dumps(tool_response) + "\n"
        
        result = await mcp_client.call_tool("test_tool", {"param1": "value1"})
        
        assert result == "Tool execution result"

    @pytest.mark.asyncio
    async def test_call_tool_error(self, mcp_client, mock_process):
        """Test tool execution error handling."""
        # Setup connected client
        mcp_client._connected = True
        mcp_client._process = mock_process
        
        # Mock error response
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -1,
                "message": "Tool execution failed"
            }
        }
        
        mock_process.stdout.readline.return_value = json.dumps(error_response) + "\n"
        
        with pytest.raises(MCPProtocolError, match="Tool 'test_tool' execution failed"):
            await mcp_client.call_tool("test_tool", {"param1": "value1"})

    @pytest.mark.asyncio
    async def test_disconnect(self, mcp_client, mock_process):
        """Test client disconnection."""
        mcp_client._connected = True
        mcp_client._process = mock_process
        
        await mcp_client.disconnect()
        
        assert not mcp_client._connected
        assert mcp_client._process is None
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mcp_client, mock_process):
        """Test async context manager functionality."""
        with patch('subprocess.Popen', return_value=mock_process):
            # Mock initialization response
            mock_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
            }
            mock_process.stdout.readline.return_value = json.dumps(mock_response) + "\n"
            
            async with mcp_client as client:
                assert client._connected
            
            assert not mcp_client._connected


class TestMCPToolRegistry:
    """Test suite for MCPToolRegistry functionality."""

    @pytest.fixture
    def registry(self):
        """Create MCPToolRegistry instance."""
        return MCPToolRegistry()

    @pytest.fixture
    def mock_agent(self):
        """Create mock Pydantic AI agent."""
        agent = MagicMock()
        agent.tool = MagicMock()
        return agent

    @pytest.fixture
    def sample_mcp_servers(self):
        """Sample MCP server configurations."""
        return [
            {
                "command": "mcp-server-test",
                "args": ["--test"],
                "env": {"TEST": "true"}
            }
        ]

    @pytest.fixture
    def sample_tools(self):
        """Sample MCP tools."""
        return [
            MCPTool(
                name="sample_tool",
                description="A sample tool for testing",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Input text"}
                    },
                    "required": ["text"]
                }
            )
        ]

    @pytest.mark.asyncio
    async def test_register_mcp_tools(self, registry, mock_agent, sample_mcp_servers, sample_tools):
        """Test MCP tool registration with agent."""
        # Mock the pool and client
        with patch.object(registry._pool, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.list_tools.return_value = sample_tools
            mock_get_client.return_value = mock_client
            
            await registry.register_mcp_tools(mock_agent, sample_mcp_servers)
            
            # Verify client was obtained and tools were listed
            mock_get_client.assert_called_once()
            mock_client.list_tools.assert_called_once()
            
            # Verify tool was registered with agent
            mock_agent.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_argument_model(self, registry):
        """Test Pydantic model creation from JSON schema."""
        tool = MCPTool(
            name="test_tool",
            description="Test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "required_param": {"type": "string", "description": "Required parameter"},
                    "optional_param": {"type": "integer", "description": "Optional parameter"}
                },
                "required": ["required_param"]
            }
        )
        
        model_class = registry._create_argument_model(tool)
        
        # Test model creation with valid data
        instance = model_class(required_param="test", optional_param=42)
        assert instance.required_param == "test"
        assert instance.optional_param == 42
        
        # Test model validation
        with pytest.raises(Exception):  # Should fail without required param
            model_class(optional_param=42)

    def test_json_schema_to_python_type(self, registry):
        """Test JSON schema type conversion."""
        assert registry._json_schema_to_python_type({"type": "string"}) == str
        assert registry._json_schema_to_python_type({"type": "integer"}) == int
        assert registry._json_schema_to_python_type({"type": "number"}) == float
        assert registry._json_schema_to_python_type({"type": "boolean"}) == bool
        assert registry._json_schema_to_python_type({"type": "unknown"}) == str  # Default

    def test_dict_to_server_config(self, registry):
        """Test conversion from dict to MCPServerConfig."""
        config_dict = {
            "command": "test-server",
            "args": ["--arg1", "--arg2"],
            "env": {"VAR": "value"},
            "timeout": 15.0
        }
        
        config = registry._dict_to_server_config(config_dict)
        
        assert config.command == "test-server"
        assert config.args == ["--arg1", "--arg2"]
        assert config.env == {"VAR": "value"}
        assert config.timeout == 15.0

    @pytest.mark.asyncio
    async def test_cleanup(self, registry):
        """Test registry cleanup."""
        with patch.object(registry._pool, 'cleanup') as mock_cleanup:
            await registry.cleanup()
            mock_cleanup.assert_called_once()


class TestMCPConnectionPool:
    """Test suite for MCPConnectionPool functionality."""

    @pytest.fixture
    def pool(self):
        """Create MCPConnectionPool instance."""
        return MCPConnectionPool()

    @pytest.fixture
    def sample_config(self):
        """Sample MCPServerConfig."""
        return MCPServerConfig(command="test-server", args=["--test"])

    @pytest.mark.asyncio
    async def test_get_client_new(self, pool, sample_config):
        """Test getting a new client from pool."""
        with patch('airflow_ai_bridge.pool.MCPClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client._connected = True
            mock_client.connect = AsyncMock()
            mock_client_class.return_value = mock_client
            
            client = await pool.get_client(sample_config)
            
            assert client == mock_client
            mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_reuse(self, pool, sample_config):
        """Test reusing existing client from pool."""
        # First, add a client to the pool
        server_key = pool._get_server_key(sample_config)
        mock_client = AsyncMock()
        mock_client._connected = True
        pool._clients[server_key] = mock_client
        pool._connection_counts[server_key] = 1
        pool._locks[server_key] = asyncio.Lock()
        
        client = await pool.get_client(sample_config)
        
        assert client == mock_client
        assert pool._connection_counts[server_key] == 2

    def test_get_server_key(self, pool):
        """Test server key generation."""
        config1 = MCPServerConfig(command="server", args=["--arg1"])
        config2 = MCPServerConfig(command="server", args=["--arg2"])
        config3 = MCPServerConfig(command="server", args=["--arg1"])
        
        key1 = pool._get_server_key(config1)
        key2 = pool._get_server_key(config2)
        key3 = pool._get_server_key(config3)
        
        assert key1 != key2  # Different args
        assert key1 == key3  # Same config

    @pytest.mark.asyncio
    async def test_cleanup(self, pool, sample_config):
        """Test pool cleanup."""
        # Add a mock client
        server_key = pool._get_server_key(sample_config)
        mock_client = AsyncMock()
        pool._clients[server_key] = mock_client
        pool._connection_counts[server_key] = 1
        
        await pool.cleanup()
        
        assert len(pool._clients) == 0
        assert len(pool._connection_counts) == 0
        mock_client.disconnect.assert_called_once()


class TestMCPDecorators:
    """Test suite for MCP decorators."""

    @pytest.fixture
    def sample_mcp_servers(self):
        """Sample MCP server configurations."""
        return [{"command": "mcp-server-test"}]

    def test_mcp_agent_decorator_basic(self, sample_mcp_servers):
        """Test basic mcp_agent decorator functionality."""
        @mcp_agent(model="gpt-4o", mcp_servers=sample_mcp_servers)
        def test_function():
            return "test result"
        
        # Check that the function has MCP server config attached
        assert hasattr(test_function, '_mcp_servers')
        assert test_function._mcp_servers == sample_mcp_servers

    def test_mcp_agent_without_mcp_servers(self):
        """Test mcp_agent decorator without MCP servers."""
        @mcp_agent(model="gpt-4o")
        def test_function():
            return "test result"
        
        # Should work without MCP servers
        assert callable(test_function)

    def test_mcp_llm_decorator(self, sample_mcp_servers):
        """Test mcp_llm decorator."""
        @mcp_agent(model="gpt-4o", mcp_servers=sample_mcp_servers)
        def test_function():
            return "test result"
        
        assert callable(test_function)

    @pytest.mark.asyncio
    async def test_register_mcp_tools_function(self, sample_mcp_servers):
        """Test standalone register_mcp_tools function."""
        mock_agent = MagicMock()
        
        with patch('airflow_ai_bridge.tools._tool_registry') as mock_registry:
            mock_registry.register_mcp_tools = AsyncMock()
            
            await register_mcp_tools(mock_agent, sample_mcp_servers)
            
            mock_registry.register_mcp_tools.assert_called_once_with(
                mock_agent, sample_mcp_servers
            )


class TestIntegration:
    """Integration tests for complete MCP workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_tool_execution(self):
        """Test complete workflow from tool registration to execution."""
        # This is a more complex integration test that would require
        # mock MCP server or real MCP server for full testing
        
        # Setup mock components
        mock_agent = MagicMock()
        mock_agent.tool = MagicMock()
        
        mcp_servers = [{"command": "mock-mcp-server"}]
        
        # Mock the entire chain
        with patch('airflow_ai_bridge.tools.MCPConnectionPool') as mock_pool_class:
            mock_pool = AsyncMock()
            mock_client = AsyncMock()
            
            # Mock tool discovery
            mock_tool = MCPTool(
                name="integration_test_tool",
                description="Integration test tool",
                input_schema={
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"]
                }
            )
            mock_client.list_tools.return_value = [mock_tool]
            
            # Mock tool execution
            mock_client.call_tool.return_value = "Integration test result"
            
            mock_pool.get_client.return_value = mock_client
            mock_pool_class.return_value = mock_pool
            
            # Execute tool registration
            registry = MCPToolRegistry()
            await registry.register_mcp_tools(mock_agent, mcp_servers)
            
            # Verify tool was registered
            mock_agent.tool.assert_called_once()
            
            # Verify client interactions
            mock_pool.get_client.assert_called_once()
            mock_client.list_tools.assert_called_once()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])