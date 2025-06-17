# Changelog

All notable changes to airflow-ai-bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-01-15

### Added
- Initial release of airflow-ai-bridge
- MCP (Model Context Protocol) server integration for airflow-ai-sdk
- `@mcp_agent` decorator with seamless tool registration
- `@mcp_llm` and `@mcp_llm_branch` decorators for enhanced functionality
- Core MCP client with stdio transport support
- Connection pooling for MCP servers to optimize performance
- Comprehensive tool registration system for Pydantic AI integration
- Production-ready error handling and async support
- Full Python 3.9+ type annotations
- Complete test suite with >90% coverage
- Rich examples demonstrating real-world usage:
  - DAG Generator with filesystem MCP access
  - GitHub Daily Analysis with automated reporting
  - Multi-MCP Release Coordination workflow
- Comprehensive documentation and development guide

### Features
- Zero-configuration MCP tool registration
- Backward compatibility with existing airflow-ai-sdk code
- Support for multiple MCP servers in single agents
- Automatic Pydantic model generation from MCP tool schemas
- Connection reuse and reference counting
- Graceful error handling and degradation
- Comprehensive logging for debugging and monitoring

### Technical Details
- Built on top of airflow-ai-sdk (not a replacement)
- Supports Apache Airflow 3.0+
- Requires Python 3.9+
- Uses Pydantic AI for LLM interface
- Implements MCP protocol version 2024-11-05
- Stdio transport with HTTP transport planned for future releases

[Unreleased]: https://github.com/astronomer/airflow-ai-bridge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/astronomer/airflow-ai-bridge/releases/tag/v0.1.0