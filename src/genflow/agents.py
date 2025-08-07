"""
Core agent system for GenFlow.

Provides base classes and interfaces for creating agents that can participate
in GenFlow workflows, built on top of airflow-ai-bridge MCP integration.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    
    name: str
    description: str = ""
    model: str = "gpt-4o"
    system_prompt: str = ""
    mcp_servers: List[Dict[str, Any]] = Field(default_factory=list)
    max_retries: int = 3
    timeout: float = 300.0


class AgentMessage(BaseModel):
    """Message sent between agents."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    sender: str
    recipient: str
    content: str
    message_type: str = "general"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from an agent execution."""
    
    success: bool
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all GenFlow agents.
    
    Provides common functionality for agent lifecycle management,
    communication, and integration with the workflow engine.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.id = f"{config.name}_{uuid4().hex[:8]}"
        self._running = False
        self._message_handlers: Dict[str, callable] = {}
        
        # Initialize underlying AI agent if MCP servers are configured
        if config.mcp_servers:
            self._ai_agent = PydanticAgent(
                model=config.model,
                system_prompt=config.system_prompt
            )
        else:
            self._ai_agent = None
            
        logger.info(f"Created agent {self.id} with config: {config.name}")
    
    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Execute a task and return the response."""
        pass
    
    async def start(self) -> None:
        """Start the agent."""
        self._running = True
        logger.info(f"Started agent {self.id}")
    
    async def stop(self) -> None:
        """Stop the agent."""
        self._running = False
        logger.info(f"Stopped agent {self.id}")
    
    def is_running(self) -> bool:
        """Check if agent is running."""
        return self._running
    
    def register_message_handler(self, message_type: str, handler: callable) -> None:
        """Register a handler for a specific message type."""
        self._message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentResponse]:
        """Handle incoming message."""
        handler = self._message_handlers.get(message.message_type)
        if handler:
            try:
                return await handler(message)
            except Exception as e:
                logger.error(f"Error handling message {message.id}: {e}")
                return AgentResponse(
                    success=False,
                    error=str(e),
                    metadata={"message_id": message.id}
                )
        else:
            logger.warning(f"No handler for message type: {message.message_type}")
            return None


class Agent(BaseAgent):
    """
    Standard GenFlow agent with AI capabilities.
    
    Integrates with airflow-ai-bridge for MCP server access and AI model interaction.
    Can be used directly or extended for specific use cases.
    """
    
    async def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Execute a task using the AI agent."""
        if context is None:
            context = {}
            
        try:
            if self._ai_agent:
                # Register MCP tools if configured
                if self.config.mcp_servers:
                    await self._register_mcp_tools()
                
                # Run the AI agent
                result = await self._ai_agent.run(task, message_history=context.get("history", []))
                
                return AgentResponse(
                    success=True,
                    result=result.data,
                    metadata={
                        "agent_id": self.id,
                        "model": self.config.model,
                        "usage": getattr(result, "usage", {})
                    }
                )
            else:
                # Fallback for agents without AI capabilities
                return await self._execute_simple(task, context)
                
        except Exception as e:
            logger.error(f"Agent {self.id} execution failed: {e}")
            return AgentResponse(
                success=False,
                error=str(e),
                metadata={"agent_id": self.id}
            )
    
    async def _execute_simple(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """Simple execution for agents without AI capabilities."""
        return AgentResponse(
            success=True,
            result=f"Task '{task}' acknowledged by {self.config.name}",
            metadata={"agent_id": self.id, "execution_type": "simple"}
        )
    
    async def _register_mcp_tools(self) -> None:
        """Register MCP tools with the AI agent."""
        try:
            # Import here to avoid circular dependencies
            from airflow_ai_bridge.tools import register_mcp_tools
            
            if self._ai_agent and self.config.mcp_servers:
                await register_mcp_tools(self._ai_agent, self.config.mcp_servers)
                logger.debug(f"Registered MCP tools for agent {self.id}")
                
        except ImportError:
            logger.warning("airflow-ai-bridge not available, skipping MCP tool registration")
        except Exception as e:
            logger.error(f"Failed to register MCP tools for agent {self.id}: {e}")


class WorkflowAgent(Agent):
    """
    Specialized agent for creating and managing workflows.
    
    This agent can generate workflow definitions, manage workflow execution,
    and coordinate with other agents in the system.
    """
    
    def __init__(self, config: AgentConfig):
        # Override system prompt for workflow management
        if not config.system_prompt:
            config.system_prompt = """You are a workflow management agent. Your role is to:
1. Create and modify workflow definitions
2. Coordinate execution between multiple agents
3. Monitor workflow progress and handle errors
4. Generate reports on workflow outcomes

You have access to various tools through MCP servers for interacting with external systems."""
        
        super().__init__(config)
        self._managed_workflows: Dict[str, "Workflow"] = {}
    
    async def create_workflow(self, requirements: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Create a new workflow based on requirements."""
        task = f"""Create a workflow definition for the following requirements:
        
Requirements: {requirements}

Generate a workflow that includes:
1. Required agents and their configurations
2. Task sequence and dependencies
3. Error handling and retry logic
4. Expected outputs and success criteria

Return the workflow as a structured format."""

        return await self.execute(task, context)
    
    async def manage_workflow(self, workflow_id: str, action: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Manage an existing workflow (start, stop, monitor, etc.)."""
        task = f"""Manage workflow {workflow_id} with action: {action}
        
Provide detailed status updates and any necessary modifications based on current state."""
        
        return await self.execute(task, context)
    
    def register_workflow(self, workflow_id: str, workflow: "Workflow") -> None:
        """Register a workflow for management."""
        self._managed_workflows[workflow_id] = workflow
        logger.info(f"Registered workflow {workflow_id} with agent {self.id}")
    
    def get_managed_workflows(self) -> List[str]:
        """Get list of managed workflow IDs."""
        return list(self._managed_workflows.keys())


class AgentFactory:
    """Factory for creating agents with predefined configurations."""
    
    @staticmethod
    def create_agent(agent_type: str, name: str, **kwargs: Any) -> BaseAgent:
        """Create an agent of the specified type."""
        if agent_type == "workflow":
            config = AgentConfig(name=name, **kwargs)
            return WorkflowAgent(config)
        elif agent_type == "standard":
            config = AgentConfig(name=name, **kwargs)
            return Agent(config)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    @staticmethod
    def create_github_agent(name: str = "github_agent", **kwargs: Any) -> Agent:
        """Create an agent with GitHub MCP server."""
        config = AgentConfig(
            name=name,
            description="Agent with GitHub integration",
            mcp_servers=[{"command": "mcp-server-github"}],
            **kwargs
        )
        return Agent(config)
    
    @staticmethod
    def create_filesystem_agent(name: str = "filesystem_agent", root_path: str = "/tmp", **kwargs: Any) -> Agent:
        """Create an agent with filesystem MCP server."""
        config = AgentConfig(
            name=name,
            description="Agent with filesystem access",
            mcp_servers=[{
                "command": "mcp-server-filesystem",
                "args": ["--root", root_path]
            }],
            **kwargs
        )
        return Agent(config)