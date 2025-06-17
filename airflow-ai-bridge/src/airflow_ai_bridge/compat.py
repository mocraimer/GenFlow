"""
Compatibility layer for airflow-ai-sdk imports.

This module handles different versions and import paths of airflow-ai-sdk.
"""

import warnings
from typing import Any, Callable


class MockTask:
    """Mock task decorator for when airflow-ai-sdk is not available."""
    
    @staticmethod
    def agent(agent: Any = None, **kwargs) -> Callable:
        """Mock agent decorator."""
        def decorator(func: Callable) -> Callable:
            warnings.warn(
                "airflow-ai-sdk not available, using mock decorator. "
                "Install airflow-ai-sdk for full functionality.",
                UserWarning
            )
            return func
        return decorator
    
    @staticmethod
    def llm(model: Any = None, **kwargs) -> Callable:
        """Mock llm decorator."""
        def decorator(func: Callable) -> Callable:
            warnings.warn(
                "airflow-ai-sdk not available, using mock decorator. "
                "Install airflow-ai-sdk for full functionality.",
                UserWarning
            )
            return func
        return decorator
    
    @staticmethod
    def llm_branch(model: Any = None, **kwargs) -> Callable:
        """Mock llm_branch decorator."""
        def decorator(func: Callable) -> Callable:
            warnings.warn(
                "airflow-ai-sdk not available, using mock decorator. "
                "Install airflow-ai-sdk for full functionality.",
                UserWarning
            )
            return func
        return decorator


# Try to import task from various locations
task = None

try:
    # First try: decorators module
    from airflow_ai_sdk.decorators import task  # type: ignore[import-not-found]
except ImportError:
    try:
        # Second try: direct import
        from airflow_ai_sdk import task  # type: ignore[import-not-found]
    except ImportError:
        try:
            # Third try: operators module
            from airflow_ai_sdk.operators import task  # type: ignore[import-not-found]
        except ImportError:
            try:
                # Fourth try: maybe it's in a different structure
                import airflow_ai_sdk  # type: ignore[import-not-found]
                # Try to find task in the module
                for attr in ['task', 'Task', 'decorators', 'operators']:
                    if hasattr(airflow_ai_sdk, attr):
                        obj = getattr(airflow_ai_sdk, attr)
                        if hasattr(obj, 'agent'):
                            task = obj
                            break
                        elif hasattr(obj, 'task'):
                            task = getattr(obj, 'task')
                            break
            except ImportError:
                pass

# If we still don't have task, use mock
if task is None:
    task = MockTask()