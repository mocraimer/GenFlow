"""
GenFlow - Workflow automation framework with agents.

GenFlow provides a high-level framework for creating automation workflows
where agents can collaborate to accomplish tasks. Built on top of airflow-ai-bridge
for MCP integration and AI orchestration.
"""

from .agents import Agent, BaseAgent
from .workflow import Workflow, WorkflowEngine
from .communication import MessageBus, AgentCommunication

__version__ = "0.1.0"
__all__ = [
    "Agent",
    "BaseAgent", 
    "Workflow",
    "WorkflowEngine",
    "MessageBus",
    "AgentCommunication",
]