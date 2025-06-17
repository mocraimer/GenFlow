# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GenFlow is a Python-based automation framework for creating workflows with agents. The project is designed to enable the creation of automation workflows where agents can collaborate to accomplish tasks.

## Project Status

This is a newly initialized repository in early development phase. The core structure and implementation are yet to be created.

## Development Setup

### Python Environment
This is a Python project. Set up a virtual environment before starting development:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Project Structure (To Be Created)
The following structure should be established:
- `src/` - Main source code for GenFlow
- `tests/` - Test files for the framework
- `docs/` - Documentation
- `examples/` - Example workflows and agent implementations

## Architecture Considerations

### Core Components to Implement
1. **Agent System**: Base classes and interfaces for creating agents
2. **Workflow Engine**: Core workflow execution and orchestration
3. **Workflow Agent**: Specialized agent for creating and managing workflows
4. **Communication Layer**: Inter-agent communication mechanisms

### Framework Integration
The .gitignore suggests potential integration with the Abstra framework for process automation. Consider this when designing the architecture.

## Key Implementation Notes

- Focus on modular design to allow easy agent creation and workflow composition
- Implement proper error handling and logging for workflow debugging
- Design with async/concurrent execution in mind for agent operations
- Create clear interfaces between agents and the workflow engine

## Testing Strategy

Implement comprehensive testing for:
- Individual agent behaviors
- Workflow execution logic
- Inter-agent communication
- Error handling and recovery mechanisms