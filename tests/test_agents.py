"""
Tests for GenFlow agent system.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from genflow.agents import (
    Agent,
    AgentConfig,
    AgentFactory,
    AgentMessage,
    AgentResponse,
    BaseAgent,
    WorkflowAgent,
)


class TestAgentConfig:
    """Test AgentConfig model."""
    
    def test_default_config(self):
        """Test creating agent config with defaults."""
        config = AgentConfig(name="test_agent")
        
        assert config.name == "test_agent"
        assert config.description == ""
        assert config.model == "gpt-4o"
        assert config.system_prompt == ""
        assert config.mcp_servers == []
        assert config.max_retries == 3
        assert config.timeout == 300.0
    
    def test_custom_config(self):
        """Test creating agent config with custom values."""
        mcp_servers = [{"command": "mcp-server-github"}]
        config = AgentConfig(
            name="github_agent",
            description="Agent with GitHub access",
            model="gpt-4",
            system_prompt="You are a GitHub agent",
            mcp_servers=mcp_servers,
            max_retries=5,
            timeout=600.0
        )
        
        assert config.name == "github_agent"
        assert config.description == "Agent with GitHub access"
        assert config.model == "gpt-4"
        assert config.system_prompt == "You are a GitHub agent"
        assert config.mcp_servers == mcp_servers
        assert config.max_retries == 5
        assert config.timeout == 600.0


class TestAgentMessage:
    """Test AgentMessage model."""
    
    def test_default_message(self):
        """Test creating message with defaults."""
        message = AgentMessage(
            sender="agent1",
            recipient="agent2",
            content="Hello"
        )
        
        assert message.sender == "agent1"
        assert message.recipient == "agent2"
        assert message.content == "Hello"
        assert message.message_type == "general"
        assert message.metadata == {}
        assert message.id is not None
    
    def test_custom_message(self):
        """Test creating message with custom values."""
        metadata = {"priority": "high"}
        message = AgentMessage(
            sender="agent1",
            recipient="agent2", 
            content="Urgent task",
            message_type="task",
            metadata=metadata
        )
        
        assert message.message_type == "task"
        assert message.metadata == metadata


class TestAgentResponse:
    """Test AgentResponse model."""
    
    def test_success_response(self):
        """Test creating success response."""
        response = AgentResponse(
            success=True,
            result="Task completed",
            metadata={"duration": 5.2}
        )
        
        assert response.success is True
        assert response.result == "Task completed"
        assert response.error is None
        assert response.metadata == {"duration": 5.2}
    
    def test_error_response(self):
        """Test creating error response."""
        response = AgentResponse(
            success=False,
            error="Task failed",
            metadata={"attempt": 2}
        )
        
        assert response.success is False
        assert response.result is None
        assert response.error == "Task failed"
        assert response.metadata == {"attempt": 2}


class MockAgent(BaseAgent):
    """Mock agent implementation for testing."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.executed_tasks = []
    
    async def execute(self, task: str, context=None) -> AgentResponse:
        """Mock execute method."""
        self.executed_tasks.append((task, context))
        return AgentResponse(
            success=True,
            result=f"Executed: {task}",
            metadata={"agent_id": self.id}
        )


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    @pytest.fixture
    def agent_config(self):
        """Create test agent config."""
        return AgentConfig(name="test_agent")
    
    @pytest.fixture
    def mock_agent(self, agent_config):
        """Create mock agent."""
        return MockAgent(agent_config)
    
    def test_agent_initialization(self, mock_agent):
        """Test agent initialization."""
        assert mock_agent.config.name == "test_agent"
        assert mock_agent.id.startswith("test_agent_")
        assert not mock_agent.is_running()
        assert len(mock_agent._message_handlers) == 0
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, mock_agent):
        """Test agent start/stop lifecycle."""
        # Initially not running
        assert not mock_agent.is_running()
        
        # Start agent
        await mock_agent.start()
        assert mock_agent.is_running()
        
        # Stop agent
        await mock_agent.stop()
        assert not mock_agent.is_running()
    
    @pytest.mark.asyncio
    async def test_execute_task(self, mock_agent):
        """Test task execution."""
        task = "Test task"
        context = {"key": "value"}
        
        response = await mock_agent.execute(task, context)
        
        assert response.success is True
        assert response.result == "Executed: Test task"
        assert mock_agent.executed_tasks == [(task, context)]
    
    def test_message_handler_registration(self, mock_agent):
        """Test message handler registration."""
        handler = AsyncMock()
        
        mock_agent.register_message_handler("test", handler)
        
        assert "test" in mock_agent._message_handlers
        assert mock_agent._message_handlers["test"] == handler
    
    @pytest.mark.asyncio
    async def test_handle_message_with_handler(self, mock_agent):
        """Test message handling with registered handler."""
        handler = AsyncMock(return_value=AgentResponse(success=True, result="handled"))
        mock_agent.register_message_handler("test", handler)
        
        message = AgentMessage(
            sender="sender",
            recipient=mock_agent.id,
            content="test message",
            message_type="test"
        )
        
        response = await mock_agent.handle_message(message)
        
        assert response is not None
        assert response.success is True
        assert response.result == "handled"
        handler.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_handle_message_without_handler(self, mock_agent):
        """Test message handling without registered handler."""
        message = AgentMessage(
            sender="sender",
            recipient=mock_agent.id,
            content="test message",
            message_type="unknown"
        )
        
        response = await mock_agent.handle_message(message)
        
        assert response is None


class TestAgent:
    """Test standard Agent implementation."""
    
    @pytest.fixture
    def agent_config(self):
        """Create test agent config."""
        return AgentConfig(name="standard_agent")
    
    @pytest.fixture
    def agent(self, agent_config):
        """Create standard agent."""
        return Agent(agent_config)
    
    def test_agent_initialization_without_mcp(self, agent):
        """Test agent initialization without MCP servers."""
        assert agent._ai_agent is None
    
    def test_agent_initialization_with_mcp(self):
        """Test agent initialization with MCP servers."""
        config = AgentConfig(
            name="mcp_agent",
            mcp_servers=[{"command": "mcp-server-github"}]
        )
        agent = Agent(config)
        
        assert agent._ai_agent is not None
    
    @pytest.mark.asyncio
    async def test_execute_simple(self, agent):
        """Test simple execution without AI agent."""
        response = await agent.execute("test task")
        
        assert response.success is True
        assert "test task" in response.result
        assert response.metadata["agent_id"] == agent.id
        assert response.metadata["execution_type"] == "simple"


class TestWorkflowAgent:
    """Test WorkflowAgent implementation."""
    
    @pytest.fixture
    def workflow_agent_config(self):
        """Create workflow agent config."""
        return AgentConfig(name="workflow_manager")
    
    @pytest.fixture  
    def workflow_agent(self, workflow_agent_config):
        """Create workflow agent."""
        return WorkflowAgent(workflow_agent_config)
    
    def test_workflow_agent_initialization(self, workflow_agent):
        """Test workflow agent initialization."""
        assert workflow_agent.config.name == "workflow_manager"
        assert "workflow management agent" in workflow_agent.config.system_prompt.lower()
        assert len(workflow_agent._managed_workflows) == 0
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, workflow_agent):
        """Test workflow creation."""
        requirements = "Create a data processing pipeline"
        
        response = await workflow_agent.create_workflow(requirements)
        
        assert response.success is True
        assert requirements in str(response.result)
    
    @pytest.mark.asyncio
    async def test_manage_workflow(self, workflow_agent):
        """Test workflow management."""
        workflow_id = "test_workflow_123"
        action = "start"
        
        response = await workflow_agent.manage_workflow(workflow_id, action)
        
        assert response.success is True
        assert workflow_id in str(response.result)
        assert action in str(response.result)
    
    def test_register_workflow(self, workflow_agent):
        """Test workflow registration."""
        workflow_id = "test_workflow"
        mock_workflow = MagicMock()
        
        workflow_agent.register_workflow(workflow_id, mock_workflow)
        
        assert workflow_id in workflow_agent._managed_workflows
        assert workflow_agent._managed_workflows[workflow_id] == mock_workflow
    
    def test_get_managed_workflows(self, workflow_agent):
        """Test getting managed workflows."""
        workflow_ids = ["wf1", "wf2", "wf3"]
        
        for wf_id in workflow_ids:
            workflow_agent.register_workflow(wf_id, MagicMock())
        
        managed = workflow_agent.get_managed_workflows()
        
        assert set(managed) == set(workflow_ids)


class TestAgentFactory:
    """Test AgentFactory functionality."""
    
    def test_create_standard_agent(self):
        """Test creating standard agent."""
        agent = AgentFactory.create_agent("standard", "test_agent", description="Test agent")
        
        assert isinstance(agent, Agent)
        assert agent.config.name == "test_agent"
        assert agent.config.description == "Test agent"
    
    def test_create_workflow_agent(self):
        """Test creating workflow agent."""
        agent = AgentFactory.create_agent("workflow", "workflow_agent")
        
        assert isinstance(agent, WorkflowAgent)
        assert agent.config.name == "workflow_agent"
    
    def test_create_unknown_agent_type(self):
        """Test creating unknown agent type raises error."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            AgentFactory.create_agent("unknown", "test")
    
    def test_create_github_agent(self):
        """Test creating GitHub agent."""
        agent = AgentFactory.create_github_agent("github_bot")
        
        assert isinstance(agent, Agent)
        assert agent.config.name == "github_bot"
        assert len(agent.config.mcp_servers) == 1
        assert agent.config.mcp_servers[0]["command"] == "mcp-server-github"
    
    def test_create_filesystem_agent(self):
        """Test creating filesystem agent."""
        root_path = "/custom/path"
        agent = AgentFactory.create_filesystem_agent("file_agent", root_path=root_path)
        
        assert isinstance(agent, Agent)
        assert agent.config.name == "file_agent"
        assert len(agent.config.mcp_servers) == 1
        
        mcp_config = agent.config.mcp_servers[0]
        assert mcp_config["command"] == "mcp-server-filesystem"
        assert "--root" in mcp_config["args"]
        assert root_path in mcp_config["args"]