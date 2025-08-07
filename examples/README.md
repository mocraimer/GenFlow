# GenFlow Examples

This directory contains examples demonstrating GenFlow's capabilities for workflow automation with agents.

## Examples Overview

### 1. Basic Workflow (`basic_workflow.py`)

**What it demonstrates:**
- Creating agents with different roles and capabilities
- Building workflows with task dependencies
- Executing workflows and handling results
- Basic GenFlow architecture and concepts

**Key concepts:**
- Agent configuration and initialization
- Workflow definition using WorkflowBuilder
- Task orchestration and dependency management
- Result handling and error management

**How to run:**
```bash
cd examples
python basic_workflow.py
```

### 2. GitHub Automation (`github_automation.py`)

**What it demonstrates:**
- Integration with external tools via MCP servers
- GitHub repository automation and analysis
- Parallel task execution
- Real-world workflow automation scenarios

**Key concepts:**
- MCP server integration (GitHub)
- AgentFactory for preconfigured agents
- Parallel workflow execution
- External system integration

**Prerequisites:**
```bash
# Install GitHub MCP server
pip install mcp-server-github

# Set GitHub token
export GITHUB_TOKEN=your_github_token_here
```

**How to run:**
```bash
cd examples
python github_automation.py
```

### 3. Agent Communication (`agent_communication.py`)

**What it demonstrates:**
- Inter-agent communication patterns
- Message bus functionality
- Request-response communication
- Broadcast messaging
- Message handling and subscriptions

**Key concepts:**
- AgentCommunication interface
- Message filtering and routing
- Asynchronous communication patterns
- Message history and statistics

**How to run:**
```bash
cd examples
python agent_communication.py
```

## Running Examples

### Prerequisites

1. **Install GenFlow** (from the root directory):
```bash
pip install -e .
```

2. **Optional: Install MCP servers** for GitHub example:
```bash
pip install mcp-server-github mcp-server-filesystem
```

3. **Set environment variables** as needed:
```bash
export GITHUB_TOKEN=your_token_here  # For GitHub example
```

### Running Individual Examples

Each example is self-contained and can be run independently:

```bash
# Basic workflow
python examples/basic_workflow.py

# GitHub automation (requires MCP setup)
python examples/github_automation.py

# Agent communication
python examples/agent_communication.py
```

## Example Structure

Each example follows this general pattern:

1. **Setup**: Initialize message bus, workflow engine, and agents
2. **Configuration**: Create agents with appropriate configurations
3. **Workflow Definition**: Define tasks, dependencies, and context
4. **Execution**: Run the workflow and handle results
5. **Cleanup**: Properly shutdown agents and services

## Key GenFlow Concepts Demonstrated

### Agents
- **BaseAgent**: Abstract base for all agents
- **Agent**: Standard AI-enabled agent with MCP support
- **WorkflowAgent**: Specialized for workflow management
- **AgentFactory**: Convenient agent creation with presets

### Workflows
- **WorkflowDefinition**: Declarative workflow structure
- **WorkflowEngine**: Execution engine with dependency management
- **WorkflowBuilder**: Fluent API for workflow creation
- **TaskDefinition**: Individual task configuration

### Communication
- **MessageBus**: Central communication hub
- **AgentCommunication**: High-level communication interface
- **AgentMessage**: Structured message format
- **Message patterns**: Point-to-point, broadcast, request-response

### Integration
- **MCP Integration**: Connect to external tools and services
- **Airflow Bridge**: Built on airflow-ai-bridge foundation
- **Async Operations**: Full async/await support
- **Error Handling**: Comprehensive error management

## Extending Examples

You can extend these examples by:

1. **Adding new agent types** with custom behaviors
2. **Integrating additional MCP servers** (filesystem, Slack, etc.)
3. **Creating more complex workflows** with branching and loops
4. **Implementing custom communication patterns**
5. **Adding persistence and state management**

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure GenFlow is installed (`pip install -e .`)
2. **MCP server not found**: Install required MCP servers
3. **Authentication errors**: Check environment variables and tokens
4. **Agent timeout**: Increase timeout values for complex tasks

### Debugging

Enable debug logging to see detailed execution:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

After exploring these examples:

1. **Read the source code** in `src/genflow/` to understand implementation
2. **Create your own workflows** for specific use cases
3. **Integrate additional MCP servers** for your tools
4. **Contribute examples** for new scenarios and patterns