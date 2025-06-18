"""
Enhanced decorators that wrap airflow-ai-sdk to add MCP support.

This module provides the main integration point between airflow-ai-sdk
and MCP servers, offering seamless tool registration and execution.
"""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from pydantic_ai import Agent

from .compat import task
from .tools import register_mcp_tools

logger = logging.getLogger(__name__)

# Type variable for decorated functions
T = TypeVar('T', bound=Callable[..., Any])


def mcp_agent(
    model: str | Any = "gpt-4o",
    *,
    system_prompt: str = "",
    mcp_servers: list[dict[str, Any]] | None = None,
    **kwargs: Any
) -> Callable[[T], T]:
    """
    Enhanced @task.agent decorator that automatically registers MCP tools.
    
    This wraps airflow-ai-sdk's @task.agent decorator, adding MCP server support
    while maintaining all existing functionality and compatibility.
    
    Args:
        model: The model to use (same as airflow-ai-sdk)
        system_prompt: System prompt for the agent
        mcp_servers: List of MCP server configurations
        **kwargs: Additional arguments passed to airflow-ai-sdk's @task.agent
        
    Returns:
        Decorator function
        
    Example:
        @mcp_agent(
            model="gpt-4o",
            mcp_servers=[{"command": "mcp-server-github"}]
        )
        def analyze_repo(context):
            return "Check open issues and suggest improvements"
    """
    def decorator(func: T) -> T:
        # Create the agent instance
        agent = Agent(model, system_prompt=system_prompt)
        
        # Register MCP tools if provided
        if mcp_servers:
            # We need to handle this during task execution, not decoration time
            # Store MCP config for later use
            func._mcp_servers = mcp_servers  # type: ignore
        
        # Create wrapper for MCP tool registration
        @wraps(func)
        def mcp_wrapper(*args: Any, **kwargs: Any) -> Any:
            # This will be called during Airflow task execution
            if hasattr(func, '_mcp_servers'):
                # Register MCP tools before executing
                try:
                    # Run async tool registration in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            register_mcp_tools(agent, func._mcp_servers)
                        )
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"Failed to register MCP tools: {e}")
                    # Continue without MCP tools rather than failing
            
            # Call the original function
            return func(*args, **kwargs)
        
        # Apply the original airflow-ai-sdk decorator
        return task.agent(agent=agent, **kwargs)(mcp_wrapper)
    
    return decorator


def mcp_llm(
    model: str | Any = "gpt-4o",
    *,
    mcp_servers: list[dict[str, Any]] | None = None,
    **kwargs: Any
) -> Callable[[T], T]:
    """
    Enhanced @task.llm decorator with MCP support.
    
    This extends airflow-ai-sdk's @task.llm to work with MCP tools
    by creating an agent with tools under the hood.
    
    Args:
        model: The model to use
        mcp_servers: List of MCP server configurations
        **kwargs: Additional arguments passed to airflow-ai-sdk
        
    Returns:
        Decorator function
        
    Example:
        @mcp_llm(
            model="gpt-4o",
            mcp_servers=[{"command": "mcp-server-filesystem"}],
            result_type=str
        )
        def process_files(directory: str) -> str:
            return f"Analyze all files in {directory}"
    """
    def decorator(func: T) -> T:
        if mcp_servers:
            # If MCP servers are specified, use mcp_agent instead
            return mcp_agent(
                model=model,
                mcp_servers=mcp_servers,
                **kwargs
            )(func)
        else:
            # No MCP servers, use standard @task.llm
            return task.llm(model=model, **kwargs)(func)
    
    return decorator


def mcp_llm_branch(
    model: str | Any = "gpt-4o",
    *,
    mcp_servers: list[dict[str, Any]] | None = None,
    **kwargs: Any
) -> Callable[[T], T]:
    """
    Enhanced @task.llm_branch decorator with MCP support.
    
    This extends airflow-ai-sdk's @task.llm_branch to work with MCP tools
    for AI-driven workflow branching with external tool access.
    
    Args:
        model: The model to use
        mcp_servers: List of MCP server configurations
        **kwargs: Additional arguments passed to airflow-ai-sdk
        
    Returns:
        Decorator function
        
    Example:
        @mcp_llm_branch(
            model="gpt-4o",
            mcp_servers=[{"command": "mcp-server-github"}]
        )
        def decide_next_action(context):
            return "Check GitHub issues and decide whether to proceed with deployment"
    """
    def decorator(func: T) -> T:
        if mcp_servers:
            # Create agent for branching with MCP tools
            agent = Agent(model)
            
            @wraps(func)
            def mcp_branch_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Register MCP tools
                if hasattr(func, '_mcp_servers'):
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(
                                register_mcp_tools(agent, func._mcp_servers)
                            )
                        finally:
                            loop.close()
                    except Exception as e:
                        logger.error(f"Failed to register MCP tools for branching: {e}")
                
                return func(*args, **kwargs)
            
            func._mcp_servers = mcp_servers  # type: ignore
            
            # Use agent-based branching
            return task.agent(agent=agent, **kwargs)(mcp_branch_wrapper)
        else:
            # No MCP servers, use standard @task.llm_branch
            return task.llm_branch(model=model, **kwargs)(func)
    
    return decorator


# Legacy/convenience aliases
agent = mcp_agent  # Allow @agent(...) as shorthand
llm = mcp_llm      # Allow @llm(...) as shorthand
llm_branch = mcp_llm_branch  # Allow @llm_branch(...) as shorthand