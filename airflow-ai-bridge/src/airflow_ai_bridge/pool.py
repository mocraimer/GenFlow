"""
Connection pooling for MCP servers.

This module manages MCP client connections to avoid repeatedly starting/stopping
MCP server processes and to handle concurrent access safely.
"""

import asyncio
import logging
import weakref
from typing import Dict, Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager

from .mcp import MCPClient, MCPServerConfig

logger = logging.getLogger(__name__)


class MCPConnectionPool:
    """
    Connection pool for managing MCP client connections.
    
    This class ensures that only one connection per MCP server is active,
    handles connection reuse, and provides proper cleanup.
    """

    def __init__(self) -> None:
        self._clients: Dict[str, MCPClient] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._connection_counts: Dict[str, int] = {}

    async def get_client(self, config: MCPServerConfig) -> MCPClient:
        """
        Get or create an MCP client for the given configuration.
        
        Args:
            config: MCP server configuration
            
        Returns:
            Connected MCP client
        """
        server_key = self._get_server_key(config)
        
        # Ensure we have a lock for this server
        if server_key not in self._locks:
            self._locks[server_key] = asyncio.Lock()
        
        async with self._locks[server_key]:
            # Check if we already have a connected client
            if server_key in self._clients:
                client = self._clients[server_key]
                if client._connected:  # Check if still connected
                    self._connection_counts[server_key] += 1
                    return client
                else:
                    # Clean up disconnected client
                    await self._cleanup_client(server_key)
            
            # Create new client
            client = MCPClient(config)
            try:
                await client.connect()
                self._clients[server_key] = client
                self._connection_counts[server_key] = 1
                
                logger.info(f"Created new MCP client for: {config.command}")
                return client
                
            except Exception as e:
                logger.error(f"Failed to create MCP client for {config.command}: {e}")
                raise

    async def release_client(self, config: MCPServerConfig) -> None:
        """
        Release a client connection (decrease reference count).
        
        Args:
            config: MCP server configuration
        """
        server_key = self._get_server_key(config)
        
        if server_key in self._locks:
            async with self._locks[server_key]:
                if server_key in self._connection_counts:
                    self._connection_counts[server_key] -= 1
                    
                    # If no more references, we could optionally disconnect
                    # For now, we keep connections alive for reuse
                    if self._connection_counts[server_key] <= 0:
                        logger.debug(f"MCP client for {config.command} has no active references")

    @asynccontextmanager
    async def client_context(self, config: MCPServerConfig) -> AsyncGenerator[MCPClient, None]:
        """
        Context manager for safely using an MCP client.
        
        Args:
            config: MCP server configuration
            
        Yields:
            Connected MCP client
        """
        client = await self.get_client(config)
        try:
            yield client
        finally:
            await self.release_client(config)

    async def cleanup(self) -> None:
        """Clean up all MCP client connections."""
        cleanup_tasks = []
        
        for server_key in list(self._clients.keys()):
            cleanup_tasks.append(self._cleanup_client(server_key))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self._clients.clear()
        self._locks.clear()
        self._connection_counts.clear()
        
        logger.info("Cleaned up all MCP client connections")

    async def _cleanup_client(self, server_key: str) -> None:
        """Clean up a specific client connection."""
        if server_key in self._clients:
            client = self._clients[server_key]
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting MCP client {server_key}: {e}")
            finally:
                del self._clients[server_key]
                self._connection_counts.pop(server_key, None)

    def _get_server_key(self, config: MCPServerConfig) -> str:
        """Generate a unique key for the server configuration."""
        # Create a key that uniquely identifies this server configuration
        key_parts = [config.command]
        
        if config.args:
            key_parts.extend(config.args)
        
        if config.env:
            # Sort env vars for consistent key generation
            env_items = sorted(config.env.items())
            for key, value in env_items:
                key_parts.append(f"{key}={value}")
        
        return "|".join(key_parts)

    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about current connections."""
        return {
            "active_connections": len(self._clients),
            "connection_counts": dict(self._connection_counts),
            "servers": list(self._clients.keys())
        }


# Global connection pool instance
_connection_pool = MCPConnectionPool()


async def get_mcp_client(config: MCPServerConfig) -> MCPClient:
    """Get an MCP client from the global pool."""
    return await _connection_pool.get_client(config)


async def cleanup_mcp_connections() -> None:
    """Clean up all MCP connections in the global pool."""
    await _connection_pool.cleanup()


def get_connection_pool() -> MCPConnectionPool:
    """Get the global connection pool instance."""
    return _connection_pool