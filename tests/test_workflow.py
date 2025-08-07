"""
Tests for GenFlow workflow engine.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from genflow.agents import Agent, AgentConfig, AgentResponse
from genflow.workflow import (
    TaskDefinition,
    TaskExecution,
    TaskStatus,
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStatus,
)


class TestTaskDefinition:
    """Test TaskDefinition model."""
    
    def test_basic_task(self):
        """Test creating basic task definition."""
        task = TaskDefinition(
            id="task1",
            name="Test Task",
            agent_id="agent1",
            task_description="Do something"
        )
        
        assert task.id == "task1"
        assert task.name == "Test Task"
        assert task.agent_id == "agent1"
        assert task.task_description == "Do something"
        assert task.depends_on == []
        assert task.retry_count == 3
        assert task.timeout == 300.0
        assert task.context == {}
    
    def test_task_with_dependencies(self):
        """Test creating task with dependencies."""
        task = TaskDefinition(
            id="task2",
            name="Dependent Task",
            agent_id="agent1",
            task_description="Do something after task1",
            depends_on=["task1"],
            retry_count=5,
            timeout=600.0,
            context={"key": "value"}
        )
        
        assert task.depends_on == ["task1"]
        assert task.retry_count == 5
        assert task.timeout == 600.0
        assert task.context == {"key": "value"}


class TestTaskExecution:
    """Test TaskExecution model."""
    
    def test_initial_execution_state(self):
        """Test initial task execution state."""
        execution = TaskExecution(task_id="task1")
        
        assert execution.task_id == "task1"
        assert execution.status == TaskStatus.PENDING
        assert execution.start_time is None
        assert execution.end_time is None
        assert execution.attempts == 0
        assert execution.result is None
        assert execution.error is None


class TestWorkflowDefinition:
    """Test WorkflowDefinition model."""
    
    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            TaskDefinition(
                id="task1",
                name="First Task",
                agent_id="agent1",
                task_description="First task"
            ),
            TaskDefinition(
                id="task2", 
                name="Second Task",
                agent_id="agent2",
                task_description="Second task",
                depends_on=["task1"]
            ),
            TaskDefinition(
                id="task3",
                name="Third Task", 
                agent_id="agent3",
                task_description="Third task",
                depends_on=["task2"]
            )
        ]
    
    def test_workflow_creation(self, sample_tasks):
        """Test creating workflow definition."""
        workflow = WorkflowDefinition(
            name="Test Workflow",
            description="A test workflow",
            tasks=sample_tasks
        )
        
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert len(workflow.tasks) == 3
        assert workflow.global_context == {}
        assert workflow.max_parallel_tasks == 5
        assert workflow.default_timeout == 600.0
        assert workflow.id is not None
    
    def test_get_task(self, sample_tasks):
        """Test getting task by ID."""
        workflow = WorkflowDefinition(name="Test", tasks=sample_tasks)
        
        task = workflow.get_task("task2")
        assert task is not None
        assert task.id == "task2"
        
        missing = workflow.get_task("missing")
        assert missing is None
    
    def test_get_dependencies(self, sample_tasks):
        """Test getting task dependencies.""" 
        workflow = WorkflowDefinition(name="Test", tasks=sample_tasks)
        
        deps1 = workflow.get_dependencies("task1")
        assert deps1 == []
        
        deps2 = workflow.get_dependencies("task2")
        assert deps2 == ["task1"]
        
        deps3 = workflow.get_dependencies("task3")
        assert deps3 == ["task2"]
    
    def test_get_dependents(self, sample_tasks):
        """Test getting task dependents."""
        workflow = WorkflowDefinition(name="Test", tasks=sample_tasks)
        
        dependents1 = workflow.get_dependents("task1")
        assert dependents1 == ["task2"]
        
        dependents2 = workflow.get_dependents("task2")
        assert dependents2 == ["task3"]
        
        dependents3 = workflow.get_dependents("task3")
        assert dependents3 == []
    
    def test_validate_dependencies_valid(self, sample_tasks):
        """Test validating valid dependencies."""
        workflow = WorkflowDefinition(name="Test", tasks=sample_tasks)
        
        assert workflow.validate_dependencies() is True
    
    def test_validate_dependencies_missing(self):
        """Test validating with missing dependencies."""
        tasks = [
            TaskDefinition(
                id="task1",
                name="Task 1",
                agent_id="agent1",
                task_description="Task 1",
                depends_on=["missing_task"]
            )
        ]
        workflow = WorkflowDefinition(name="Test", tasks=tasks)
        
        assert workflow.validate_dependencies() is False
    
    def test_validate_dependencies_cycle(self):
        """Test validating with cyclic dependencies."""
        tasks = [
            TaskDefinition(
                id="task1",
                name="Task 1", 
                agent_id="agent1",
                task_description="Task 1",
                depends_on=["task2"]
            ),
            TaskDefinition(
                id="task2",
                name="Task 2",
                agent_id="agent2", 
                task_description="Task 2",
                depends_on=["task1"]
            )
        ]
        workflow = WorkflowDefinition(name="Test", tasks=tasks)
        
        assert workflow.validate_dependencies() is False


class TestWorkflowExecution:
    """Test WorkflowExecution model."""
    
    def test_initial_execution_state(self):
        """Test initial workflow execution state."""
        execution = WorkflowExecution(workflow_id="wf1")
        
        assert execution.workflow_id == "wf1"
        assert execution.status == WorkflowStatus.CREATED
        assert execution.start_time is None
        assert execution.end_time is None
        assert execution.task_executions == {}
        assert execution.execution_context == {}
    
    def test_get_task_execution(self):
        """Test getting task execution."""
        execution = WorkflowExecution(workflow_id="wf1")
        
        # Initially empty
        task_exec = execution.get_task_execution("task1")
        assert task_exec is None
        
        # Add task execution
        execution.task_executions["task1"] = TaskExecution(task_id="task1")
        task_exec = execution.get_task_execution("task1")
        assert task_exec is not None
        assert task_exec.task_id == "task1"
    
    def test_update_task_status(self):
        """Test updating task status."""
        execution = WorkflowExecution(workflow_id="wf1")
        result = AgentResponse(success=True, result="done")
        
        # Update status creates execution if not exists
        execution.update_task_status("task1", TaskStatus.SUCCESS, result)
        
        task_exec = execution.get_task_execution("task1")
        assert task_exec is not None
        assert task_exec.status == TaskStatus.SUCCESS
        assert task_exec.result == result


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id: str, delay: float = 0.1, should_fail: bool = False):
        self.id = agent_id
        self.delay = delay
        self.should_fail = should_fail
        self.execution_count = 0
    
    async def execute(self, task: str, context=None) -> AgentResponse:
        """Mock execute method."""
        await asyncio.sleep(self.delay)
        self.execution_count += 1
        
        if self.should_fail:
            return AgentResponse(
                success=False,
                error=f"Mock agent {self.id} failed",
                metadata={"agent_id": self.id}
            )
        else:
            return AgentResponse(
                success=True,
                result=f"Agent {self.id} completed: {task}",
                metadata={"agent_id": self.id}
            )


class TestWorkflowEngine:
    """Test WorkflowEngine functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create workflow engine."""
        return WorkflowEngine()
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock agents."""
        return {
            "agent1": MockAgent("agent1"),
            "agent2": MockAgent("agent2"), 
            "agent3": MockAgent("agent3")
        }
    
    @pytest.fixture
    def sample_workflow(self):
        """Create sample workflow definition."""
        tasks = [
            TaskDefinition(
                id="task1",
                name="First Task",
                agent_id="agent1",
                task_description="First task"
            ),
            TaskDefinition(
                id="task2",
                name="Second Task", 
                agent_id="agent2",
                task_description="Second task",
                depends_on=["task1"]
            )
        ]
        return WorkflowDefinition(name="Test Workflow", tasks=tasks)
    
    def test_agent_registration(self, engine, mock_agents):
        """Test agent registration and unregistration."""
        agent = mock_agents["agent1"]
        
        # Register agent
        engine.register_agent(agent)
        assert agent.id in engine._agents
        assert len(engine.list_agents()) == 1
        
        # Unregister agent
        engine.unregister_agent(agent.id)
        assert agent.id not in engine._agents
        assert len(engine.list_agents()) == 0
    
    def test_workflow_creation(self, engine, sample_workflow):
        """Test workflow creation."""
        workflow_id = engine.create_workflow(sample_workflow)
        
        assert workflow_id == sample_workflow.id
        assert workflow_id in engine._workflows
        assert len(engine.list_workflows()) == 1
    
    def test_workflow_creation_invalid_dependencies(self, engine):
        """Test workflow creation with invalid dependencies fails."""
        tasks = [
            TaskDefinition(
                id="task1",
                name="Task 1",
                agent_id="agent1", 
                task_description="Task 1",
                depends_on=["missing"]
            )
        ]
        workflow = WorkflowDefinition(name="Invalid", tasks=tasks)
        
        with pytest.raises(ValueError, match="Invalid workflow dependencies"):
            engine.create_workflow(workflow)
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self, engine, sample_workflow, mock_agents):
        """Test successful workflow execution."""
        # Register agents
        for agent in mock_agents.values():
            engine.register_agent(agent)
        
        # Create and execute workflow
        workflow_id = engine.create_workflow(sample_workflow)
        execution = await engine.execute_workflow(workflow_id)
        
        assert execution.status == WorkflowStatus.SUCCESS
        assert len(execution.task_executions) == 2
        
        # Check task1 executed first
        task1_exec = execution.get_task_execution("task1")
        assert task1_exec.status == TaskStatus.SUCCESS
        
        # Check task2 executed after task1
        task2_exec = execution.get_task_execution("task2")
        assert task2_exec.status == TaskStatus.SUCCESS
        
        # Verify agents were called
        assert mock_agents["agent1"].execution_count == 1
        assert mock_agents["agent2"].execution_count == 1
    
    @pytest.mark.asyncio
    async def test_workflow_execution_with_failure(self, engine, sample_workflow, mock_agents):
        """Test workflow execution with task failure."""
        # Make agent1 fail
        mock_agents["agent1"].should_fail = True
        
        # Register agents
        for agent in mock_agents.values():
            engine.register_agent(agent)
        
        # Create and execute workflow
        workflow_id = engine.create_workflow(sample_workflow)
        execution = await engine.execute_workflow(workflow_id)
        
        assert execution.status == WorkflowStatus.FAILED
        
        # Check task1 failed
        task1_exec = execution.get_task_execution("task1")
        assert task1_exec.status == TaskStatus.FAILED
        
        # Check task2 was not executed (dependency failed)
        task2_exec = execution.get_task_execution("task2")
        assert task2_exec.status == TaskStatus.PENDING
        
        # Verify only agent1 was called
        assert mock_agents["agent1"].execution_count >= 1  # Including retries
        assert mock_agents["agent2"].execution_count == 0
    
    @pytest.mark.asyncio
    async def test_workflow_execution_missing_agent(self, engine, sample_workflow):
        """Test workflow execution with missing agent."""
        # Don't register agents
        
        workflow_id = engine.create_workflow(sample_workflow)
        execution = await engine.execute_workflow(workflow_id)
        
        assert execution.status == WorkflowStatus.FAILED
        
        # Tasks should fail due to missing agents
        task1_exec = execution.get_task_execution("task1")
        assert task1_exec.status == TaskStatus.FAILED
        assert "not found" in task1_exec.result.error
    
    @pytest.mark.asyncio
    async def test_workflow_execution_not_found(self, engine):
        """Test executing non-existent workflow."""
        with pytest.raises(ValueError, match="Workflow .* not found"):
            await engine.execute_workflow("missing_workflow")
    
    def test_get_workflow_status(self, engine, sample_workflow, mock_agents):
        """Test getting workflow status."""
        # Register agents
        for agent in mock_agents.values():
            engine.register_agent(agent)
        
        workflow_id = engine.create_workflow(sample_workflow)
        
        # Initially no execution
        status = engine.get_workflow_status(workflow_id)
        assert status is None
    
    @pytest.mark.asyncio
    async def test_cancel_workflow(self, engine, sample_workflow, mock_agents):
        """Test workflow cancellation."""
        # Register agents with delay
        for agent in mock_agents.values():
            agent.delay = 1.0  # Long delay
            engine.register_agent(agent)
        
        workflow_id = engine.create_workflow(sample_workflow)
        
        # Start execution in background
        execution_task = asyncio.create_task(
            engine.execute_workflow(workflow_id)
        )
        
        # Wait a bit then cancel
        await asyncio.sleep(0.1)
        cancelled = await engine.cancel_workflow(workflow_id)
        
        assert cancelled is True
        
        # Check execution status
        status = engine.get_workflow_status(workflow_id)
        assert status.status == WorkflowStatus.CANCELLED
        
        # Clean up
        execution_task.cancel()
        try:
            await execution_task
        except asyncio.CancelledError:
            pass


class TestWorkflowBuilder:
    """Test WorkflowBuilder functionality."""
    
    def test_basic_workflow_building(self):
        """Test basic workflow building."""
        workflow = (WorkflowBuilder("Test Workflow", "Test description")
                   .add_task("task1", "agent1", "Do task 1")
                   .add_task("task2", "agent2", "Do task 2", depends_on=["task1"])
                   .build())
        
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Test description"
        assert len(workflow.tasks) == 2
        
        task1 = workflow.get_task("task1")
        assert task1.agent_id == "agent1"
        assert task1.depends_on == []
        
        task2 = workflow.get_task("task2")
        assert task2.agent_id == "agent2"
        assert task2.depends_on == ["task1"]
    
    def test_workflow_building_with_context(self):
        """Test workflow building with global context."""
        context = {"key": "value", "number": 42}
        
        workflow = (WorkflowBuilder("Test Workflow")
                   .add_task("task1", "agent1", "Task 1")
                   .set_global_context(context)
                   .set_max_parallel_tasks(10)
                   .build())
        
        assert workflow.global_context == context
        assert workflow.max_parallel_tasks == 10
    
    def test_workflow_building_with_task_options(self):
        """Test workflow building with task options."""
        workflow = (WorkflowBuilder("Test Workflow")
                   .add_task(
                       "task1", 
                       "agent1", 
                       "Task 1",
                       retry_count=5,
                       timeout=120.0,
                       context={"task_key": "task_value"}
                   )
                   .build())
        
        task = workflow.get_task("task1")
        assert task.retry_count == 5
        assert task.timeout == 120.0
        assert task.context == {"task_key": "task_value"}
    
    def test_workflow_building_invalid_dependencies(self):
        """Test workflow building with invalid dependencies."""
        with pytest.raises(ValueError, match="Invalid workflow dependencies"):
            (WorkflowBuilder("Invalid Workflow")
             .add_task("task1", "agent1", "Task 1", depends_on=["missing"])
             .build())