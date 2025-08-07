"""
Pytest configuration and fixtures for GenFlow tests.
"""

import asyncio
import pytest
from unittest.mock import MagicMock

from genflow.agents import Agent, AgentConfig, AgentResponse
from genflow.communication import MessageBus
from genflow.workflow import WorkflowEngine


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def message_bus():
    """Create and manage a message bus for tests."""
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def workflow_engine():
    """Create a workflow engine for tests."""
    return WorkflowEngine()


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    class MockAgent:
        def __init__(self, agent_id="mock_agent", success=True, result="mock result"):
            self.id = agent_id
            self.success = success
            self.result = result
            self.execution_count = 0
            self.last_task = None
            self.last_context = None
        
        async def execute(self, task, context=None):
            self.execution_count += 1
            self.last_task = task
            self.last_context = context
            
            return AgentResponse(
                success=self.success,
                result=self.result if self.success else None,
                error=None if self.success else "Mock agent failed",
                metadata={"agent_id": self.id, "execution_count": self.execution_count}
            )
        
        async def start(self):
            pass
        
        async def stop(self):
            pass
    
    return MockAgent


@pytest.fixture
def sample_agent_config():
    """Create a sample agent configuration."""
    return AgentConfig(
        name="test_agent",
        description="A test agent",
        model="gpt-4o",
        system_prompt="You are a test agent",
        mcp_servers=[],
        max_retries=3,
        timeout=300.0
    )


@pytest.fixture  
def github_agent_config():
    """Create an agent configuration with GitHub MCP."""
    return AgentConfig(
        name="github_agent",
        description="Agent with GitHub access",
        mcp_servers=[{"command": "mcp-server-github"}]
    )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location/name."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
        
        # Mark slow tests (tests that use sleep or have long timeouts)
        if any(keyword in item.name.lower() for keyword in ["timeout", "slow", "delay"]):
            item.add_marker(pytest.mark.slow)