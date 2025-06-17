"""
Tool registration system for integrating MCP servers with Pydantic AI agents.

This module bridges MCP tools with Pydantic AI's tool system, making
MCP server capabilities available to airflow-ai-sdk agents.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Tuple, get_type_hints
from functools import wraps

from pydantic import BaseModel, Field, create_model
from pydantic_ai import Agent

from .mcp import MCPClient, MCPServerConfig, MCPTool
from .pool import MCPConnectionPool

logger = logging.getLogger(__name__)


class MCPToolError(Exception):
    """Raised when MCP tool registration or execution fails."""
    pass


class MCPToolRegistry:
    """
    Registry for managing MCP tools and their integration with Pydantic AI agents.
    
    This class handles the discovery and registration of MCP tools,
    converting them into Pydantic AI compatible tool functions.
    """

    def __init__(self) -> None:
        self._pool = MCPConnectionPool()
        self._registered_tools: Dict[str, MCPTool] = {}
        self._tool_clients: Dict[str, str] = {}  # tool_name -> server_command mapping

    async def register_mcp_tools(
        self, 
        agent: Agent, 
        mcp_servers: List[Dict[str, Any]]
    ) -> None:
        """
        Register MCP server tools with a Pydantic AI agent.
        
        This is the core integration point that makes MCP tools available
        to airflow-ai-sdk agents without manual configuration.
        
        Args:
            agent: The Pydantic AI agent to register tools with
            mcp_servers: List of MCP server configurations
        """
        for server_config_dict in mcp_servers:
            try:
                # Convert dict to MCPServerConfig
                server_config = self._dict_to_server_config(server_config_dict)
                
                # Get or create client for this server
                client = await self._pool.get_client(server_config)
                
                # Discover available tools
                tools = await client.list_tools()
                
                # Register each tool with the agent
                for tool in tools:
                    await self._register_single_tool(agent, tool, server_config.command)
                    
                logger.info(
                    f"Registered {len(tools)} tools from MCP server: {server_config.command}"
                )
                
            except Exception as e:
                logger.error(f"Failed to register MCP server {server_config_dict}: {e}")
                raise MCPToolError(f"MCP server registration failed: {e}")

    async def _register_single_tool(
        self, 
        agent: Agent, 
        mcp_tool: MCPTool, 
        server_command: str
    ) -> None:
        """Register a single MCP tool with a Pydantic AI agent."""
        tool_name = mcp_tool.name
        
        # Store tool metadata
        self._registered_tools[tool_name] = mcp_tool
        self._tool_clients[tool_name] = server_command
        
        # Create Pydantic model for tool arguments
        argument_model = self._create_argument_model(mcp_tool)
        
        # Create the tool function
        async def mcp_tool_function(**kwargs: Any) -> str:
            """Dynamically created MCP tool function."""
            try:
                # Validate arguments using the generated model
                validated_args = argument_model(**kwargs)
                
                # Get client for this tool's server
                server_config = MCPServerConfig(command=server_command)
                client = await self._pool.get_client(server_config)
                
                # Execute the tool
                result = await client.call_tool(tool_name, validated_args.model_dump())
                
                # Convert result to string for LLM consumption
                if isinstance(result, dict):
                    return str(result)
                elif isinstance(result, list):
                    return "\n".join(str(item) for item in result)
                else:
                    return str(result)
                    
            except Exception as e:
                error_msg = f"MCP tool '{tool_name}' execution failed: {e}"
                logger.error(error_msg)
                return f"Error: {error_msg}"
        
        # Set function metadata
        mcp_tool_function.__name__ = tool_name
        mcp_tool_function.__doc__ = mcp_tool.description
        
        # Register with Pydantic AI agent
        agent.tool(mcp_tool_function)  # type: ignore[arg-type]
        
        logger.debug(f"Registered MCP tool: {tool_name}")

    def _create_argument_model(self, mcp_tool: MCPTool) -> Type[BaseModel]:
        """
        Create a Pydantic model for MCP tool arguments.
        
        This converts the MCP tool's JSON schema into a Pydantic model
        for type validation and IDE support.
        """
        schema = mcp_tool.input_schema
        
        if not schema or schema.get("type") != "object":
            # No arguments or unsupported schema
            return create_model(f"{mcp_tool.name}Args")
        
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))
        
        # Convert JSON schema properties to Pydantic field definitions
        field_definitions: Dict[str, Any] = {}
        
        for field_name, field_schema in properties.items():
            field_type = self._json_schema_to_python_type(field_schema)
            field_description = field_schema.get("description", "")
            
            if field_name in required_fields:
                field_definitions[field_name] = (
                    field_type, 
                    Field(description=field_description)
                )
            else:
                field_definitions[field_name] = (
                    Optional[field_type],
                    Field(default=None, description=field_description)
                )
        
        return create_model(f"{mcp_tool.name}Args", **field_definitions)

    def _json_schema_to_python_type(self, schema: Dict[str, Any]) -> Type[Any]:
        """Convert JSON schema type to Python type annotation."""
        schema_type = schema.get("type", "string")
        
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": List[Any],
            "object": Dict[str, Any],
        }
        
        return type_mapping.get(schema_type, str)

    def _dict_to_server_config(self, config_dict: Dict[str, Any]) -> MCPServerConfig:
        """Convert dictionary configuration to MCPServerConfig."""
        return MCPServerConfig(
            command=config_dict["command"],
            args=config_dict.get("args"),
            env=config_dict.get("env"),
            timeout=config_dict.get("timeout", 30.0)
        )

    async def cleanup(self) -> None:
        """Clean up MCP connections."""
        await self._pool.cleanup()

    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._registered_tools.keys())

    def get_tool_info(self, tool_name: str) -> Optional[MCPTool]:
        """Get information about a registered tool."""
        return self._registered_tools.get(tool_name)


# Global registry instance
_tool_registry: MCPToolRegistry = MCPToolRegistry()


async def register_mcp_tools(agent: Agent, mcp_servers: List[Dict[str, Any]]) -> None:
    """
    Convenience function to register MCP tools with an agent.
    
    This is the main entry point used by the decorators.
    """
    await _tool_registry.register_mcp_tools(agent, mcp_servers)


async def cleanup_mcp_tools() -> None:
    """Clean up MCP tool connections."""
    await _tool_registry.cleanup()


def get_tool_registry() -> MCPToolRegistry:
    """Get the global tool registry instance."""
    return _tool_registry