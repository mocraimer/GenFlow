"""
Pytest configuration and shared fixtures for airflow-ai-bridge tests.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.Popen for MCP server testing."""
    process = MagicMock()
    process.stdin = MagicMock()
    process.stdout = MagicMock()
    process.stderr = MagicMock()
    process.poll.return_value = None
    process.terminate = MagicMock()
    process.kill = MagicMock()
    return process


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = AsyncMock()
    client._connected = True
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.list_tools = AsyncMock()
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def sample_tool_schema():
    """Sample tool schema for testing."""
    return {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Input text to process"
            },
            "options": {
                "type": "object", 
                "description": "Optional configuration",
                "properties": {
                    "format": {"type": "string", "enum": ["json", "text"]}
                }
            }
        },
        "required": ["text"]
    }