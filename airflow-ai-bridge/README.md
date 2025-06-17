# airflow-ai-bridge

Seamless MCP (Model Context Protocol) server integration for Astronomer's airflow-ai-sdk.

## Overview

airflow-ai-bridge extends the [airflow-ai-sdk](https://github.com/astronomer/airflow-ai-sdk) to add Model Context Protocol (MCP) server support, enabling AI agents in your Airflow DAGs to interact with external tools like GitHub, Slack, filesystems, and more.

This package focuses on doing one thing well: making MCP servers "just work" with existing airflow-ai-sdk workflows.

## Key Features

- **Zero-configuration MCP tool registration** - MCP tools automatically appear in your agents
- **Seamless integration** - Works alongside existing airflow-ai-sdk code
- **Production-ready** - Connection pooling, error handling, and async support
- **Type-safe** - Full Python 3.9+ type annotations
- **Minimal overhead** - Thin wrapper around airflow-ai-sdk

## Installation

```bash
# Basic installation
pip install airflow-ai-bridge

# With airflow-ai-sdk support (recommended)
pip install "airflow-ai-bridge[airflow-ai-sdk]"
```

## Quick Start

Transform your existing airflow-ai-sdk agents by adding MCP server support:

```python
from airflow import DAG
from airflow_ai_bridge import mcp_agent
from datetime import datetime

with DAG("github_analyzer", start_date=datetime(2024, 1, 1)) as dag:
    
    # Before: Standard AI agent
    # @task.agent(model="gpt-4o")
    # def analyze_repo():
    #     return "analyze the repository"
    
    # After: Agent with GitHub MCP access
    @mcp_agent(
        model="gpt-4o",
        mcp_servers=[{"command": "mcp-server-github"}]
    )
    def analyze_repo():
        return "Check open issues and suggest improvements"
```

## MCP Server Configuration

Configure MCP servers with a simple dictionary:

```python
@mcp_agent(
    model="gpt-4o",
    mcp_servers=[
        {
            "command": "mcp-server-github",
            "args": ["--repo", "astronomer/airflow"],
            "env": {"GITHUB_TOKEN": "{{ var.value.github_token }}"}
        },
        {
            "command": "mcp-server-filesystem",
            "args": ["--root", "/tmp/airflow-data"]
        }
    ]
)
def multi_tool_agent(context):
    return "Read files and create GitHub issues based on errors"
```

## Examples

### DAG Generator
Use MCP filesystem access to let AI write DAGs:

```python
from airflow_ai_bridge import mcp_agent

@mcp_agent(
    model="gpt-4o",
    system_prompt="You are a DAG generator assistant",
    mcp_servers=[{
        "command": "mcp-server-filesystem",
        "args": ["--root", "/opt/airflow/dags"]
    }]
)
def generate_dag(requirements: str):
    return f"Create a DAG that: {requirements}"
```

### Daily GitHub Summary
Automated repository analysis:

```python
@mcp_agent(
    model="gpt-4o",
    mcp_servers=[{"command": "mcp-server-github"}]
)
def daily_summary():
    return """Analyze today's activity:
    - New issues and their priority
    - PR review status
    - Suggested actions for maintainers
    """
```

### Multi-Server Coordination
Combine multiple MCP servers:

```python
@mcp_agent(
    model="gpt-4o",
    mcp_servers=[
        {"command": "mcp-server-github"},
        {"command": "mcp-server-slack"},
        {"command": "mcp-server-google-calendar"}
    ]
)
def coordinate_release():
    return """
    1. Check GitHub for release blockers
    2. Schedule release meeting via Calendar
    3. Notify team on Slack with summary
    """
```

## Supported MCP Servers

The following MCP servers have been tested with airflow-ai-bridge:

- `mcp-server-github` - GitHub API access
- `mcp-server-filesystem` - Local file operations
- `mcp-server-slack` - Slack messaging
- `mcp-server-google-calendar` - Calendar management
- `mcp-server-sqlite` - Database queries
- [More servers](https://github.com/modelcontextprotocol/servers)

## Migration Guide

Migrating from standard airflow-ai-sdk is straightforward:

```python
# Before
from airflow_ai_sdk import task

@task.agent(model="gpt-4o")
def my_agent(data):
    return f"Process: {data}"

# After
from airflow_ai_bridge import mcp_agent

@mcp_agent(
    model="gpt-4o",
    mcp_servers=[{"command": "mcp-server-github"}]
)
def my_agent(data):
    return f"Process: {data} and check GitHub"
```

All existing airflow-ai-sdk features continue to work:
- Structured output with Pydantic models
- Streaming responses
- Error handling and retries
- Result parsing

## Architecture

airflow-ai-bridge acts as a thin layer between airflow-ai-sdk and MCP servers:

```
Airflow DAG
    ↓
airflow-ai-bridge (MCP integration)
    ↓
airflow-ai-sdk (AI orchestration)
    ↓
Pydantic AI (LLM interface)
    ↓
MCP Servers (External tools)
```

## Requirements

- Python 3.9+
- Apache Airflow 3.0+
- airflow-ai-sdk 0.1.0+
- MCP servers installed separately

## Development

```bash
# Clone the repository
git clone https://github.com/astronomer/airflow-ai-bridge
cd airflow-ai-bridge

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
ruff check src tests
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Links

- [airflow-ai-sdk](https://github.com/astronomer/airflow-ai-sdk) - The foundation we build on
- [Model Context Protocol](https://modelcontextprotocol.org/) - MCP specification
- [MCP Servers](https://github.com/modelcontextprotocol/servers) - Available MCP servers
- [Documentation](https://airflow-ai-bridge.readthedocs.io) - Full documentation