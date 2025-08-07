"""
Basic GenFlow workflow example.

This example demonstrates how to create a simple workflow with multiple agents
that collaborate to complete a task using GenFlow.
"""

import asyncio
import logging
from datetime import datetime

from genflow import Agent, AgentConfig, WorkflowEngine, WorkflowBuilder, MessageBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run a basic workflow example."""
    print("🚀 Starting GenFlow Basic Workflow Example")
    
    # Initialize the message bus and workflow engine
    message_bus = MessageBus()
    await message_bus.start()
    
    workflow_engine = WorkflowEngine()
    
    # Create agents
    print("📋 Creating agents...")
    
    # Data collector agent
    data_collector = Agent(AgentConfig(
        name="data_collector",
        description="Collects and processes data",
        system_prompt="You are a data collection agent. Your job is to gather and structure data for analysis."
    ))
    
    # Data analyzer agent  
    data_analyzer = Agent(AgentConfig(
        name="data_analyzer", 
        description="Analyzes processed data",
        system_prompt="You are a data analysis agent. You receive structured data and provide insights and recommendations."
    ))
    
    # Report generator agent
    report_generator = Agent(AgentConfig(
        name="report_generator",
        description="Generates reports from analysis",
        system_prompt="You are a report generator. You take analysis results and create comprehensive, well-formatted reports."
    ))
    
    # Register agents with workflow engine
    workflow_engine.register_agent(data_collector)
    workflow_engine.register_agent(data_analyzer)
    workflow_engine.register_agent(report_generator)
    
    # Start agents
    await data_collector.start()
    await data_analyzer.start()
    await report_generator.start()
    
    print(f"✅ Created and started {len(workflow_engine.list_agents())} agents")
    
    # Create a workflow
    print("🏗️ Building workflow...")
    
    workflow = (WorkflowBuilder("data_processing_workflow", "Process data and generate report")
                .add_task(
                    task_id="collect_data",
                    agent_id=data_collector.id,
                    task_description="Collect sample sales data for the last quarter. Generate realistic data with products, quantities, dates, and revenues."
                )
                .add_task(
                    task_id="analyze_data", 
                    agent_id=data_analyzer.id,
                    task_description="Analyze the collected sales data. Identify trends, top products, revenue patterns, and growth opportunities.",
                    depends_on=["collect_data"]
                )
                .add_task(
                    task_id="generate_report",
                    agent_id=report_generator.id, 
                    task_description="Create a comprehensive quarterly sales report based on the analysis. Include executive summary, key findings, and recommendations.",
                    depends_on=["analyze_data"]
                )
                .set_global_context({"quarter": "Q4 2024", "company": "GenFlow Demo Corp"})
                .build())
    
    # Register and execute workflow
    workflow_id = workflow_engine.create_workflow(workflow)
    print(f"✅ Created workflow: {workflow.name} (ID: {workflow_id})")
    
    print("▶️ Executing workflow...")
    start_time = datetime.now()
    
    execution = await workflow_engine.execute_workflow(workflow_id)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Display results
    print(f"\n📊 Workflow Execution Complete!")
    print(f"Status: {execution.status}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Tasks executed: {len(execution.task_executions)}")
    
    print(f"\n📋 Task Results:")
    for task_id, task_execution in execution.task_executions.items():
        print(f"\n🔸 Task: {task_id}")
        print(f"  Status: {task_execution.status}")
        if task_execution.result:
            result_preview = str(task_execution.result.result)[:200] + "..." if len(str(task_execution.result.result)) > 200 else str(task_execution.result.result)
            print(f"  Result: {result_preview}")
        if task_execution.error:
            print(f"  Error: {task_execution.error}")
    
    # Show final report if available
    report_task = execution.task_executions.get("generate_report")
    if report_task and report_task.result and report_task.result.success:
        print(f"\n📄 Generated Report:")
        print("=" * 50)
        print(report_task.result.result)
        print("=" * 50)
    
    # Cleanup
    await data_collector.stop()
    await data_analyzer.stop()
    await report_generator.stop()
    await message_bus.stop()
    
    print("\n✅ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())