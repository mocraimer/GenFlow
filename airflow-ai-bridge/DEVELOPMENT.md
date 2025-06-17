# Development Guide for airflow-ai-bridge

## Package Overview

airflow-ai-bridge is a production-ready Python package that extends Astronomer's airflow-ai-sdk to add seamless Model Context Protocol (MCP) server integration. This allows AI agents in Airflow DAGs to interact with external tools like GitHub, Slack, filesystems, and more.

## Architecture

```
Airflow DAG
    ↓
airflow-ai-bridge (MCP integration layer)
    ↓
airflow-ai-sdk (AI orchestration)
    ↓
Pydantic AI (LLM interface)
    ↓
MCP Servers (External tools)
```

## Core Components

### 1. MCP Client (`src/airflow_ai_bridge/mcp.py`)
- Handles MCP protocol communication via stdio transport
- Manages server process lifecycle
- Implements JSON-RPC message handling
- Provides async context manager interface

### 2. Tool Registration (`src/airflow_ai_bridge/tools.py`)
- Bridges MCP tools with Pydantic AI's tool system
- Automatically converts MCP tool schemas to Pydantic models
- Handles tool discovery and registration
- Manages tool execution with error handling

### 3. Connection Pooling (`src/airflow_ai_bridge/pool.py`)
- Manages MCP client connections to avoid process churn
- Provides connection reuse and reference counting
- Handles concurrent access safely
- Implements proper cleanup procedures

### 4. Enhanced Decorators (`src/airflow_ai_bridge/decorators.py`)
- Wraps airflow-ai-sdk decorators to add MCP support
- Maintains backward compatibility
- Provides `@mcp_agent`, `@mcp_llm`, and `@mcp_llm_branch`
- Handles async tool registration in sync Airflow context

## Key Features

✅ **Zero-configuration MCP tool registration**
✅ **Seamless integration with existing airflow-ai-sdk code**
✅ **Production-ready connection pooling**
✅ **Full async support with proper error handling**
✅ **Complete type safety with Python 3.9+ annotations**
✅ **Comprehensive testing suite**
✅ **Rich examples demonstrating real-world usage**

## Usage Examples

### Basic Usage
```python
from airflow_ai_bridge import mcp_agent

@mcp_agent(
    model="gpt-4o",
    mcp_servers=[{"command": "mcp-server-github"}]
)
def analyze_repo():
    return "Check open issues and suggest improvements"
```

### Multi-Server Coordination
```python
@mcp_agent(
    model="gpt-4o",
    mcp_servers=[
        {"command": "mcp-server-github"},
        {"command": "mcp-server-slack"},
        {"command": "mcp-server-filesystem"}
    ]
)
def coordinate_release():
    return "Check GitHub, notify Slack, update docs"
```

## Development Setup

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy src

# Format code
black src tests examples
ruff check src tests examples

# Run all checks
pytest && mypy src && black --check src tests examples && ruff check src tests examples
```

## Testing

The package includes comprehensive tests covering:
- MCP client protocol handling
- Tool registration and execution
- Connection pooling
- Decorator functionality
- Integration scenarios
- Error handling

Run tests with: `pytest tests/ -v`

## Examples

### 1. DAG Generator (`examples/dag_generator.py`)
Uses MCP filesystem access to let AI write and manage Airflow DAGs automatically.

### 2. GitHub Daily Analysis (`examples/github_daily.py`)
Automated repository analysis using MCP GitHub tools with email reporting.

### 3. Multi-MCP Release Coordination (`examples/multi_mcp.py`)
Complex release management using GitHub, Slack, Calendar, and filesystem tools.

## Production Considerations

### Performance
- Connection pooling minimizes MCP server startup overhead
- Async implementation prevents blocking Airflow tasks
- Tool caching reduces repeated discovery calls

### Security
- MCP servers run as separate processes
- Environment variable isolation
- No credential exposure in logs

### Error Handling
- Graceful degradation when MCP servers unavailable
- Detailed error messages for debugging
- Automatic retry mechanisms where appropriate

### Monitoring
- Comprehensive logging at appropriate levels
- Connection pool metrics available
- Tool execution timing and success rates

## Extending the Package

### Adding New MCP Transports
Currently supports stdio transport. HTTP transport can be added by:
1. Extending `MCPTransportType` enum
2. Implementing HTTP client in `MCPClient`
3. Adding HTTP-specific configuration options

### Custom Tool Processing
Override `MCPToolRegistry._register_single_tool()` to customize:
- Tool argument validation
- Result processing
- Error handling
- Caching behavior

### Integration with Other AI Frameworks
The MCP client can be used independently of Pydantic AI:
```python
from airflow_ai_bridge.mcp import MCPClient, MCPServerConfig

config = MCPServerConfig(command="mcp-server-github")
async with MCPClient(config) as client:
    tools = await client.list_tools()
    result = await client.call_tool("get_issues", {"repo": "owner/repo"})
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit a pull request

## Roadmap

- [ ] HTTP transport support for MCP servers
- [ ] Enhanced connection pool metrics and monitoring
- [ ] Integration with Airflow's built-in logging system
- [ ] Support for MCP server auto-discovery
- [ ] Performance optimizations for large-scale deployments
- [ ] Additional example DAGs for common use cases

## Support

- Check the README.md for usage examples
- Review the examples/ directory for real-world scenarios
- Run tests to verify your setup
- Open issues for bugs or feature requests