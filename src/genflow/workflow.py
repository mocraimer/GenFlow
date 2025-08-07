"""
Workflow engine for GenFlow.

Provides workflow definition, execution, and orchestration capabilities
integrated with Airflow through airflow-ai-bridge.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from .agents import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of a workflow task."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success" 
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


class WorkflowStatus(str, Enum):
    """Status of a workflow."""
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskDefinition(BaseModel):
    """Definition of a task within a workflow."""
    
    id: str
    name: str
    agent_id: str
    task_description: str
    depends_on: List[str] = Field(default_factory=list)
    retry_count: int = 3
    timeout: float = 300.0
    context: Dict[str, Any] = Field(default_factory=dict)


class TaskExecution(BaseModel):
    """Runtime execution state of a task."""
    
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attempts: int = 0
    result: Optional[AgentResponse] = None
    error: Optional[str] = None


class WorkflowDefinition(BaseModel):
    """Definition of a complete workflow."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    tasks: List[TaskDefinition]
    global_context: Dict[str, Any] = Field(default_factory=dict)
    max_parallel_tasks: int = 5
    default_timeout: float = 600.0
    
    def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_dependencies(self, task_id: str) -> List[str]:
        """Get dependencies for a task."""
        task = self.get_task(task_id)
        return task.depends_on if task else []
    
    def get_dependents(self, task_id: str) -> List[str]:
        """Get tasks that depend on the given task."""
        dependents = []
        for task in self.tasks:
            if task_id in task.depends_on:
                dependents.append(task.id)
        return dependents
    
    def validate_dependencies(self) -> bool:
        """Validate that all dependencies exist and there are no cycles."""
        task_ids = {task.id for task in self.tasks}
        
        # Check all dependencies exist
        for task in self.tasks:
            for dep in task.depends_on:
                if dep not in task_ids:
                    logger.error(f"Task {task.id} depends on non-existent task {dep}")
                    return False
        
        # Check for cycles using DFS
        def has_cycle(task_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            for dep in self.get_dependents(task_id):
                if dep not in visited:
                    if has_cycle(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        visited = set()
        for task in self.tasks:
            if task.id not in visited:
                if has_cycle(task.id, visited, set()):
                    logger.error("Cycle detected in workflow dependencies")
                    return False
        
        return True


class WorkflowExecution(BaseModel):
    """Runtime execution state of a workflow."""
    
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    task_executions: Dict[str, TaskExecution] = Field(default_factory=dict)
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    
    def get_task_execution(self, task_id: str) -> Optional[TaskExecution]:
        """Get execution state for a task."""
        return self.task_executions.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: Optional[AgentResponse] = None) -> None:
        """Update the status of a task execution."""
        if task_id not in self.task_executions:
            self.task_executions[task_id] = TaskExecution(task_id=task_id)
        
        execution = self.task_executions[task_id]
        execution.status = status
        execution.result = result
        
        if status == TaskStatus.RUNNING and not execution.start_time:
            execution.start_time = datetime.utcnow()
        elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED]:
            execution.end_time = datetime.utcnow()


class WorkflowEngine:
    """
    Core workflow execution engine.
    
    Manages workflow lifecycle, task scheduling, and coordination between agents.
    Integrates with Airflow through airflow-ai-bridge for production deployments.
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._running_tasks: Set[str] = set()
        
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the workflow engine."""
        self._agents[agent.id] = agent
        logger.info(f"Registered agent {agent.id} with workflow engine")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the workflow engine."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
    
    def create_workflow(self, definition: WorkflowDefinition) -> str:
        """Create a new workflow from definition."""
        if not definition.validate_dependencies():
            raise ValueError("Invalid workflow dependencies")
        
        self._workflows[definition.id] = definition
        logger.info(f"Created workflow {definition.id}: {definition.name}")
        return definition.id
    
    async def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None) -> WorkflowExecution:
        """Execute a workflow."""
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self._workflows[workflow_id]
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.utcnow(),
            execution_context=context or {}
        )
        
        # Initialize task executions
        for task in workflow.tasks:
            execution.task_executions[task.id] = TaskExecution(task_id=task.id)
        
        self._executions[workflow_id] = execution
        
        try:
            await self._execute_workflow_tasks(workflow, execution)
            
            # Determine final status
            failed_tasks = [t for t in execution.task_executions.values() if t.status == TaskStatus.FAILED]
            if failed_tasks:
                execution.status = WorkflowStatus.FAILED
            else:
                execution.status = WorkflowStatus.SUCCESS
                
        except Exception as e:
            logger.error(f"Workflow {workflow_id} execution failed: {e}")
            execution.status = WorkflowStatus.FAILED
        finally:
            execution.end_time = datetime.utcnow()
        
        logger.info(f"Workflow {workflow_id} completed with status: {execution.status}")
        return execution
    
    async def _execute_workflow_tasks(self, workflow: WorkflowDefinition, execution: WorkflowExecution) -> None:
        """Execute all tasks in a workflow with proper dependency management."""
        completed_tasks = set()
        semaphore = asyncio.Semaphore(workflow.max_parallel_tasks)
        
        while len(completed_tasks) < len(workflow.tasks):
            # Find ready tasks (all dependencies completed successfully)
            ready_tasks = []
            for task in workflow.tasks:
                if (task.id not in completed_tasks and 
                    task.id not in self._running_tasks and
                    execution.get_task_execution(task.id).status == TaskStatus.PENDING):
                    
                    dependencies_met = all(
                        dep in completed_tasks and 
                        execution.get_task_execution(dep).status == TaskStatus.SUCCESS
                        for dep in task.depends_on
                    )
                    
                    if dependencies_met:
                        ready_tasks.append(task)
            
            if not ready_tasks:
                if not self._running_tasks:
                    # No ready tasks and nothing running - check for failures
                    failed_tasks = [
                        t for t in execution.task_executions.values() 
                        if t.status == TaskStatus.FAILED
                    ]
                    if failed_tasks:
                        logger.error(f"Workflow blocked by failed tasks: {[t.task_id for t in failed_tasks]}")
                        break
                
                # Wait for running tasks to complete
                await asyncio.sleep(0.1)
                continue
            
            # Start ready tasks
            tasks_to_run = []
            for task in ready_tasks:
                task_coro = self._execute_single_task(workflow, task, execution, semaphore)
                tasks_to_run.append(task_coro)
            
            # Run tasks and wait for at least one to complete
            if tasks_to_run:
                done, pending = await asyncio.wait(tasks_to_run, return_when=asyncio.FIRST_COMPLETED)
                
                # Update completed tasks
                for task_coro in done:
                    try:
                        task_id = await task_coro
                        completed_tasks.add(task_id)
                        self._running_tasks.discard(task_id)
                    except Exception as e:
                        logger.error(f"Task execution error: {e}")
                
                # Continue with pending tasks
                for task_coro in pending:
                    task_coro.cancel()
    
    async def _execute_single_task(
        self, 
        workflow: WorkflowDefinition, 
        task: TaskDefinition, 
        execution: WorkflowExecution,
        semaphore: asyncio.Semaphore
    ) -> str:
        """Execute a single task."""
        async with semaphore:
            self._running_tasks.add(task.id)
            task_execution = execution.get_task_execution(task.id)
            
            try:
                # Find the agent
                agent = self._agents.get(task.agent_id)
                if not agent:
                    raise ValueError(f"Agent {task.agent_id} not found")
                
                # Update status to running
                execution.update_task_status(task.id, TaskStatus.RUNNING)
                
                # Prepare task context
                task_context = {**workflow.global_context, **task.context, **execution.execution_context}
                
                # Execute with timeout
                try:
                    result = await asyncio.wait_for(
                        agent.execute(task.task_description, task_context),
                        timeout=task.timeout
                    )
                    
                    if result.success:
                        execution.update_task_status(task.id, TaskStatus.SUCCESS, result)
                        logger.info(f"Task {task.id} completed successfully")
                    else:
                        if task_execution.attempts < task.retry_count:
                            task_execution.attempts += 1
                            execution.update_task_status(task.id, TaskStatus.RETRY)
                            logger.warning(f"Task {task.id} failed, retrying ({task_execution.attempts}/{task.retry_count})")
                            # Recursive retry
                            return await self._execute_single_task(workflow, task, execution, semaphore)
                        else:
                            execution.update_task_status(task.id, TaskStatus.FAILED, result)
                            logger.error(f"Task {task.id} failed after {task.retry_count} attempts")
                
                except asyncio.TimeoutError:
                    error_msg = f"Task {task.id} timed out after {task.timeout}s"
                    logger.error(error_msg)
                    result = AgentResponse(success=False, error=error_msg)
                    execution.update_task_status(task.id, TaskStatus.FAILED, result)
                
            except Exception as e:
                error_msg = f"Task {task.id} execution error: {e}"
                logger.error(error_msg)
                result = AgentResponse(success=False, error=error_msg)
                execution.update_task_status(task.id, TaskStatus.FAILED, result)
            
            return task.id
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get the execution status of a workflow."""
        return self._executions.get(workflow_id)
    
    def list_workflows(self) -> List[str]:
        """List all registered workflow IDs."""
        return list(self._workflows.keys())
    
    def list_agents(self) -> List[str]:
        """List all registered agent IDs."""
        return list(self._agents.keys())
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        execution = self._executions.get(workflow_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = datetime.utcnow()
            logger.info(f"Cancelled workflow {workflow_id}")
            return True
        return False


class WorkflowBuilder:
    """Builder class for creating workflow definitions."""
    
    def __init__(self, name: str, description: str = ""):
        self.workflow = WorkflowDefinition(name=name, description=description, tasks=[])
    
    def add_task(
        self,
        task_id: str,
        agent_id: str,
        task_description: str,
        depends_on: List[str] = None,
        **kwargs: Any
    ) -> "WorkflowBuilder":
        """Add a task to the workflow."""
        task = TaskDefinition(
            id=task_id,
            name=task_id,
            agent_id=agent_id,
            task_description=task_description,
            depends_on=depends_on or [],
            **kwargs
        )
        self.workflow.tasks.append(task)
        return self
    
    def set_global_context(self, context: Dict[str, Any]) -> "WorkflowBuilder":
        """Set global context for the workflow."""
        self.workflow.global_context = context
        return self
    
    def set_max_parallel_tasks(self, max_parallel: int) -> "WorkflowBuilder":
        """Set maximum parallel task execution."""
        self.workflow.max_parallel_tasks = max_parallel
        return self
    
    def build(self) -> WorkflowDefinition:
        """Build and return the workflow definition."""
        if not self.workflow.validate_dependencies():
            raise ValueError("Invalid workflow dependencies")
        return self.workflow