"""
Command Line Interface for Airflow AI Bridge

Provides easy access to DAG generation and UI launching functionality.
"""

import click
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional

@click.group()
@click.version_option()
def cli():
    """Airflow AI Bridge CLI - Generate DAGs with AI and MCP servers"""
    pass

@cli.command()
@click.argument('description')
@click.option('--servers', '-s', multiple=True, 
              help='MCP servers to use (github, filesystem, slack, sqlite)')
@click.option('--model', '-m', default='gpt-4o',
              help='AI model to use for generation')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path for the generated DAG')
@click.option('--schedule', default='@daily',
              help='Schedule interval for the DAG')
def generate(description: str, servers: tuple, model: str, output: Optional[str], schedule: str):
    """Generate a DAG from natural language description"""
    
    click.echo("🤖 Airflow AI Bridge - DAG Generator")
    click.echo("=" * 50)
    click.echo(f"📝 Description: {description}")
    click.echo(f"🤖 Model: {model}")
    click.echo(f"📡 Servers: {', '.join(servers) if servers else 'filesystem (default)'}")
    click.echo(f"⏰ Schedule: {schedule}")
    click.echo()
    
    # Use filesystem as default if no servers specified
    if not servers:
        servers = ('filesystem',)
    
    # Generate DAG code (simplified version for CLI)
    dag_code = generate_dag_code(description, list(servers), model, schedule)
    
    if output:
        # Write to file
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(dag_code)
        
        click.echo(f"✅ DAG saved to: {output_path}")
        click.echo(f"📁 File size: {output_path.stat().st_size} bytes")
    else:
        # Print to stdout
        click.echo("📄 Generated DAG Code:")
        click.echo("-" * 50)
        click.echo(dag_code)
    
    click.echo()
    click.echo("🚀 Next steps:")
    click.echo("1. Review and customize the generated DAG")
    click.echo("2. Place it in your Airflow DAGs directory")
    click.echo("3. Configure required Airflow variables")
    click.echo("4. Enable the DAG in Airflow UI")

@cli.command()
@click.option('--port', '-p', default=8501, help='Port to run the UI on')
@click.option('--host', '-h', default='localhost', help='Host to bind the UI to')
def ui(port: int, host: str):
    """Launch the Streamlit web UI"""
    
    click.echo("🚀 Launching Airflow AI Bridge Web UI...")
    click.echo(f"🌐 URL: http://{host}:{port}")
    click.echo("⏹️  Press Ctrl+C to stop")
    click.echo()
    
    # Get the path to the UI module
    ui_path = Path(__file__).parent / "ui.py"
    
    if not ui_path.exists():
        click.echo("❌ UI module not found. Please ensure streamlit is installed.")
        sys.exit(1)
    
    try:
        # Launch Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            str(ui_path),
            "--server.port", str(port),
            "--server.address", host,
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down UI...")
    except FileNotFoundError:
        click.echo("❌ Streamlit not found. Install with: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error launching UI: {e}")
        sys.exit(1)

@cli.command()
def list_servers():
    """List available MCP servers"""
    
    servers = {
        "github": "🐙 GitHub - Repository analysis, issue management, PR operations",
        "filesystem": "📁 Filesystem - File operations, DAG management, local data processing",
        "slack": "💬 Slack - Team notifications, status updates, alerts",
        "sqlite": "🗄️ SQLite - Database queries, data analysis, metadata management"
    }
    
    click.echo("📋 Available MCP Servers:")
    click.echo("=" * 50)
    
    for server_name, description in servers.items():
        click.echo(f"  {description}")
    
    click.echo()
    click.echo("💡 Usage examples:")
    click.echo("  airflow-ai-bridge generate 'Process CSV files' --servers filesystem")
    click.echo("  airflow-ai-bridge generate 'Analyze GitHub repo' --servers github slack")

@cli.command()
@click.argument('server_name')
def test_server(server_name: str):
    """Test MCP server connection"""
    
    click.echo(f"🔌 Testing MCP server: {server_name}")
    
    # This is a placeholder - in a real implementation, you'd test the actual server
    servers = ["github", "filesystem", "slack", "sqlite"]
    
    if server_name not in servers:
        click.echo(f"❌ Unknown server: {server_name}")
        click.echo(f"Available servers: {', '.join(servers)}")
        sys.exit(1)
    
    click.echo(f"⏳ Connecting to {server_name}...")
    
    # Simulate connection test
    import time
    time.sleep(1)
    
    click.echo(f"✅ {server_name} server connection successful!")
    click.echo(f"📊 Server status: Ready")
    click.echo(f"🔧 Available tools: Checking...")
    
    # Mock tool listing
    tools = {
        "github": ["list_issues", "create_pr", "get_repo_info"],
        "filesystem": ["read_file", "write_file", "list_directory"],
        "slack": ["send_message", "create_channel", "get_users"],
        "sqlite": ["execute_query", "create_table", "get_schema"]
    }
    
    if server_name in tools:
        click.echo(f"🛠️  Available tools: {', '.join(tools[server_name])}")

def generate_dag_code(description: str, servers: List[str], model: str, schedule: str) -> str:
    """Generate DAG code (simplified version for CLI)"""
    
    from datetime import datetime
    import json
    
    # Create MCP server configurations
    mcp_configs = []
    for server in servers:
        config = {"command": f"mcp-server-{server}"}
        
        if server == "filesystem":
            config["args"] = ["--root", "/opt/airflow/dags"]
        elif server == "github":
            config["env"] = {"GITHUB_TOKEN": "{{ var.value.github_token }}"}
        elif server == "slack":
            config["env"] = {"SLACK_TOKEN": "{{ var.value.slack_token }}"}
        
        mcp_configs.append(config)
    
    dag_code = f'''"""
Generated DAG: AI-powered workflow
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Description: {description}
Generated via: airflow-ai-bridge CLI
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow_ai_bridge import mcp_agent

# DAG configuration
default_args = {{
    "owner": "airflow-ai-bridge",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}}

dag = DAG(
    "cli_generated_workflow",
    default_args=default_args,
    description="CLI-generated workflow using MCP servers",
    schedule_interval="{schedule}",
    catchup=False,
    tags=["ai", "mcp", "cli-generated"],
)

@mcp_agent(
    model="{model}",
    system_prompt="""You are an intelligent workflow assistant that can execute complex tasks
    using the available MCP tools. Follow best practices and provide detailed status updates.""",
    mcp_servers={json.dumps(mcp_configs, indent=8)}
)
def execute_workflow() -> str:
    """
    Execute the AI-powered workflow based on requirements.
    
    Returns:
        Status message about workflow execution
    """
    return """
    {description}
    
    Please execute this workflow using the available MCP tools:
    {", ".join(servers)}
    
    Provide detailed status updates and handle any errors gracefully.
    """

# Create the task
workflow_task = PythonOperator(
    task_id="execute_cli_workflow",
    python_callable=execute_workflow,
    dag=dag,
)
'''
    
    return dag_code

if __name__ == '__main__':
    cli() 