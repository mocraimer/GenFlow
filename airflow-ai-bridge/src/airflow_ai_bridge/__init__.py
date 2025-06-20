"""
airflow-ai-bridge: MCP server integration for airflow-ai-sdk

This package extends Astronomer's airflow-ai-sdk to add seamless
Model Context Protocol (MCP) server integration, enabling AI agents
in Airflow DAGs to interact with external tools and services.
"""

from .decorators import agent, llm, llm_branch, mcp_agent, mcp_llm, mcp_llm_branch
from .mcp import (
    MCPClient,
    MCPConnectionError,
    MCPError,
    MCPProtocolError,
    MCPServerConfig,
    MCPTool,
)
from .pool import cleanup_mcp_connections, get_connection_pool, get_mcp_client
from .tools import cleanup_mcp_tools, get_tool_registry, register_mcp_tools

# Optional imports for UI and CLI
try:
    from . import cli
except ImportError:
    cli = None

try:
    from . import ui
except ImportError:
    ui = None

__version__ = "0.1.0"
__author__ = "Airflow AI Bridge Contributors"

# Main exports - these are what users will import
__all__ = [
    # Decorators (main user interface)
    "mcp_agent",
    "mcp_llm",
    "mcp_llm_branch",
    "agent",  # Convenience alias
    "llm",  # Convenience alias
    "llm_branch",  # Convenience alias
    # MCP Core
    "MCPClient",
    "MCPServerConfig",
    "MCPTool",
    "MCPError",
    "MCPConnectionError",
    "MCPProtocolError",
    # Tool Management
    "register_mcp_tools",
    "cleanup_mcp_tools",
    "get_tool_registry",
    # Connection Management
    "get_mcp_client",
    "cleanup_mcp_connections",
    "get_connection_pool",
    # Package info
    "__version__",
]

# Package-level documentation
__doc__ = """
airflow-ai-bridge enables seamless MCP server integration with airflow-ai-sdk.

Quick start:

    from airflow_ai_bridge import mcp_agent
    
    @mcp_agent(
        model="gpt-4o",
        mcp_servers=[{"command": "mcp-server-github"}]
    )
    def analyze_repo():
        return "Check open issues and suggest improvements"

See README.md for more examples and documentation.
"""
