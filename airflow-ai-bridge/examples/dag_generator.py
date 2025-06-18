"""
Example DAG: AI-powered DAG generator using MCP filesystem access

This example shows how to use airflow-ai-bridge with MCP filesystem tools
to let AI write and manage Airflow DAGs automatically.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from airflow_ai_bridge import mcp_agent

# DAG configuration
default_args = {
    'owner': 'airflow-ai-bridge',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'ai_dag_generator',
    default_args=default_args,
    description='AI generates DAGs using MCP filesystem access',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['ai', 'mcp', 'generator'],
)


@mcp_agent(
    model="gpt-4o",
    system_prompt="""You are a DAG generation assistant that creates Airflow DAGs based on
requirements.
    
    You have access to the filesystem and can:
    1. Read existing DAG files to understand patterns
    2. Write new DAG files following best practices
    3. Validate DAG syntax
    
    Always follow these principles:
    - Use proper imports and DAG structure
    - Include appropriate error handling
    - Add meaningful descriptions and tags
    - Follow Airflow best practices
    """,
    mcp_servers=[{
        "command": "mcp-server-filesystem",
        "args": ["--root", "/opt/airflow/dags"],
        "env": {"ALLOWED_EXTENSIONS": "py,sql,yaml"}
    }]
)
def generate_dag_from_requirements(requirements: str) -> str:
    """
    Generate a new DAG based on natural language requirements.
    
    Args:
        requirements: Natural language description of the desired DAG
        
    Returns:
        Status message about DAG generation
    """
    return f"""
    Create a new Airflow DAG based on these requirements:
    
    {requirements}
    
    Steps to follow:
    1. First, read existing DAG files to understand the current patterns and structure
    2. Create a new DAG file with appropriate name (use underscore_case)
    3. Include proper imports, default_args, and DAG definition
    4. Add the required tasks based on the requirements
    5. Ensure proper task dependencies
    6. Validate the DAG structure
    7. Write the DAG file to the dags directory
    
    Return a summary of what was created.
    """


@mcp_agent(
    model="gpt-4o",
    system_prompt="You are a DAG analysis assistant that reviews existing DAGs for improvements.",
    mcp_servers=[{
        "command": "mcp-server-filesystem", 
        "args": ["--root", "/opt/airflow/dags"]
    }]
)
def analyze_existing_dags() -> str:
    """
    Analyze existing DAGs and suggest improvements.
    
    Returns:
        Analysis report with suggestions
    """
    return """
    Analyze all DAG files in the dags directory and provide:
    
    1. Overview of existing DAGs (count, types, patterns)
    2. Common issues or anti-patterns found
    3. Suggestions for improvements
    4. Recommendations for standardization
    5. Security considerations
    
    Focus on:
    - Code quality and best practices
    - Resource usage optimization
    - Error handling patterns
    - Documentation completeness
    """


@mcp_agent(
    model="gpt-4o",
    system_prompt="You are a DAG maintenance assistant that helps keep DAGs clean and updated.",
    mcp_servers=[{
        "command": "mcp-server-filesystem",
        "args": ["--root", "/opt/airflow/dags"]
    }]
)
def cleanup_deprecated_dags() -> str:
    """
    Clean up deprecated or unused DAGs.
    
    Returns:
        Cleanup report
    """
    return """
    Review all DAG files and identify:
    
    1. DAGs that haven't been modified in over 6 months
    2. DAGs with deprecated imports or patterns
    3. Unused or commented-out code
    4. DAGs that might be duplicates
    
    For each deprecated DAG:
    - Move to a 'deprecated' subdirectory
    - Add a comment explaining why it was deprecated
    - Create a migration guide if needed
    
    Provide a summary of cleanup actions taken.
    """


# Task definitions
generate_dag_task = PythonOperator(
    task_id='generate_dag_from_requirements',
    python_callable=generate_dag_from_requirements,
    op_kwargs={
        'requirements': """
        Create a data pipeline DAG that:
        1. Extracts data from a PostgreSQL database
        2. Transforms the data using pandas
        3. Loads the result into a data warehouse
        4. Sends notification on completion
        5. Runs daily at 2 AM
        """
    },
    dag=dag,
)

analyze_dags_task = PythonOperator(
    task_id='analyze_existing_dags',
    python_callable=analyze_existing_dags,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_deprecated_dags',
    python_callable=cleanup_deprecated_dags,
    dag=dag,
)

# Set task dependencies
analyze_dags_task >> generate_dag_task >> cleanup_task


if __name__ == "__main__":
    # Test the DAG locally
    print("Testing DAG generator...")
    
    # This would typically be run by Airflow
    result = generate_dag_from_requirements(
        "Create a simple ETL pipeline that processes CSV files"
    )
    print(f"Generated DAG: {result}")