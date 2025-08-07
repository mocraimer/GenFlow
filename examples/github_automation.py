"""
GitHub automation workflow example using GenFlow with MCP integration.

This example demonstrates how to create a workflow that uses agents with
GitHub MCP server integration to automate repository tasks.
"""

import asyncio
import logging
from datetime import datetime

from genflow import Agent, AgentConfig, WorkflowEngine, WorkflowBuilder, MessageBus, AgentFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run GitHub automation workflow example."""
    print("🐙 Starting GenFlow GitHub Automation Example")
    
    # Initialize the message bus and workflow engine
    message_bus = MessageBus()
    await message_bus.start()
    
    workflow_engine = WorkflowEngine()
    
    # Create agents with GitHub MCP integration
    print("📋 Creating GitHub-enabled agents...")
    
    # Issue analyzer agent
    issue_analyzer = AgentFactory.create_github_agent(
        name="issue_analyzer",
        description="Analyzes GitHub issues and pull requests",
        system_prompt="""You are a GitHub issue analyzer. Your responsibilities:
1. Review open issues and categorize them by type and priority
2. Identify issues that need attention or are stale
3. Suggest appropriate labels and assignments
4. Provide summaries of issue status and trends"""
    )
    
    # Code reviewer agent
    code_reviewer = AgentFactory.create_github_agent(
        name="code_reviewer", 
        description="Reviews code and pull requests",
        system_prompt="""You are an automated code reviewer. Your responsibilities:
1. Review pull request changes for code quality
2. Check for common issues, security concerns, and best practices
3. Suggest improvements and optimizations  
4. Validate that PR descriptions are complete and accurate"""
    )
    
    # Release coordinator agent
    release_coordinator = AgentFactory.create_github_agent(
        name="release_coordinator",
        description="Coordinates releases and manages project status", 
        system_prompt="""You are a release coordinator. Your responsibilities:
1. Analyze repository state for release readiness
2. Identify blockers and dependencies
3. Generate release notes and changelogs
4. Coordinate with team on release planning"""
    )
    
    # Report generator agent (no GitHub access needed)
    report_generator = Agent(AgentConfig(
        name="report_generator",
        description="Generates comprehensive reports",
        system_prompt="You create detailed reports from provided data, formatting them clearly and highlighting key insights."
    ))
    
    # Register agents with workflow engine
    workflow_engine.register_agent(issue_analyzer)
    workflow_engine.register_agent(code_reviewer)
    workflow_engine.register_agent(release_coordinator)
    workflow_engine.register_agent(report_generator)
    
    # Start agents
    await issue_analyzer.start()
    await code_reviewer.start()
    await release_coordinator.start()
    await report_generator.start()
    
    print(f"✅ Created and started {len(workflow_engine.list_agents())} agents")
    
    # Create GitHub automation workflow
    print("🏗️ Building GitHub automation workflow...")
    
    workflow = (WorkflowBuilder("github_automation", "Automated GitHub repository management and reporting")
                .add_task(
                    task_id="analyze_issues",
                    agent_id=issue_analyzer.id,
                    task_description="""Analyze the current state of GitHub issues in the repository:
1. List all open issues with their labels, assignees, and age
2. Categorize issues by type (bug, feature, documentation, etc.)
3. Identify stale issues (older than 30 days with no activity)
4. Suggest prioritization based on labels and activity
5. Provide a summary of issue health metrics"""
                )
                .add_task(
                    task_id="review_pull_requests", 
                    agent_id=code_reviewer.id,
                    task_description="""Review current pull requests in the repository:
1. List all open pull requests with basic information
2. Check for PRs that need review or have been waiting too long
3. Identify any PRs with merge conflicts or CI failures
4. Suggest review assignments based on changed files
5. Provide summary of PR queue health""",
                    depends_on=[]  # Can run in parallel with issue analysis
                )
                .add_task(
                    task_id="assess_release_readiness",
                    agent_id=release_coordinator.id,
                    task_description="""Assess the repository's release readiness:
1. Check if there are any open critical issues or bugs
2. Review recent commits and merged PRs since last release
3. Identify potential release blockers
4. Generate preliminary release notes for recent changes
5. Suggest next release timeline and version number""",
                    depends_on=["analyze_issues", "review_pull_requests"]
                )
                .add_task(
                    task_id="generate_status_report",
                    agent_id=report_generator.id,
                    task_description="""Generate a comprehensive repository status report:
1. Combine insights from issue analysis, PR review, and release assessment
2. Create executive summary with key metrics and health indicators
3. Highlight urgent items that need attention
4. Provide recommendations for repository maintenance
5. Format as a professional status report""",
                    depends_on=["analyze_issues", "review_pull_requests", "assess_release_readiness"]
                )
                .set_global_context({
                    "repository": "mocraimer/GenFlow",
                    "report_date": datetime.now().strftime("%Y-%m-%d"),
                    "analysis_type": "weekly_status"
                })
                .set_max_parallel_tasks(3)  # Allow parallel execution where possible
                .build())
    
    # Register and execute workflow
    workflow_id = workflow_engine.create_workflow(workflow)
    print(f"✅ Created workflow: {workflow.name} (ID: {workflow_id})")
    
    print("▶️ Executing GitHub automation workflow...")
    print("⚠️  Note: This example requires GitHub MCP server to be installed and configured")
    print("   Install with: pip install mcp-server-github")
    print("   Configure with GITHUB_TOKEN environment variable")
    
    start_time = datetime.now()
    
    try:
        execution = await workflow_engine.execute_workflow(workflow_id)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Display results
        print(f"\n📊 GitHub Automation Workflow Complete!")
        print(f"Status: {execution.status}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Tasks executed: {len(execution.task_executions)}")
        
        print(f"\n📋 Task Results:")
        for task_id, task_execution in execution.task_executions.items():
            print(f"\n🔸 Task: {task_id}")
            print(f"  Status: {task_execution.status}")
            if task_execution.result:
                if task_execution.result.success:
                    result_preview = str(task_execution.result.result)[:300] + "..." if len(str(task_execution.result.result)) > 300 else str(task_execution.result.result)
                    print(f"  Result: {result_preview}")
                else:
                    print(f"  Error: {task_execution.result.error}")
            if task_execution.error:
                print(f"  Execution Error: {task_execution.error}")
        
        # Show final status report if available
        report_task = execution.task_executions.get("generate_status_report")
        if report_task and report_task.result and report_task.result.success:
            print(f"\n📄 Repository Status Report:")
            print("=" * 60)
            print(report_task.result.result)
            print("=" * 60)
        
        # Show workflow statistics
        stats = workflow_engine.get_workflow_status(workflow_id)
        if stats:
            successful_tasks = sum(1 for t in stats.task_executions.values() if t.status.value == "success")
            failed_tasks = sum(1 for t in stats.task_executions.values() if t.status.value == "failed")
            print(f"\n📈 Workflow Statistics:")
            print(f"  ✅ Successful tasks: {successful_tasks}")
            print(f"  ❌ Failed tasks: {failed_tasks}")
            print(f"  ⏱️ Total execution time: {duration:.2f} seconds")
    
    except Exception as e:
        print(f"\n❌ Workflow execution failed: {e}")
        print("This might be due to missing GitHub MCP server or configuration.")
        print("To run this example successfully:")
        print("1. Install mcp-server-github: pip install mcp-server-github")
        print("2. Set GITHUB_TOKEN environment variable with your GitHub token")
        print("3. Ensure you have access to the repository specified in the workflow")
    
    # Cleanup
    await issue_analyzer.stop()
    await code_reviewer.stop()
    await release_coordinator.stop()
    await report_generator.stop()
    await message_bus.stop()
    
    print("\n✅ GitHub automation example completed!")


if __name__ == "__main__":
    asyncio.run(main())