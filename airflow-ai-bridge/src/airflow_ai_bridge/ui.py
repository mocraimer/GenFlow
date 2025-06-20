"""
Streamlit UI for Airflow AI Bridge

A web interface for generating Airflow DAGs using AI and MCP servers.
Run with: streamlit run src/airflow_ai_bridge/ui.py
"""

import streamlit as st
import json
from datetime import datetime
from typing import List, Dict, Any

# Page configuration
st.set_page_config(
    page_title="Airflow AI Bridge",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .example-card {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

def get_mcp_servers_info() -> Dict[str, Dict[str, Any]]:
    """Get information about available MCP servers"""
    return {
        "github": {
            "name": "GitHub",
            "description": "Repository analysis, issue management, PR operations",
            "command": "mcp-server-github",
            "icon": "🐙",
            "use_cases": ["Repository analysis", "Issue tracking", "PR management", "Release coordination"]
        },
        "filesystem": {
            "name": "Filesystem",
            "description": "File operations, DAG management, local data processing",
            "command": "mcp-server-filesystem",
            "icon": "📁",
            "use_cases": ["File processing", "DAG generation", "Log analysis", "Data validation"]
        },
        "slack": {
            "name": "Slack",
            "description": "Team notifications, status updates, alerts",
            "command": "mcp-server-slack",
            "icon": "💬",
            "use_cases": ["Notifications", "Status updates", "Alert management", "Team coordination"]
        },
        "sqlite": {
            "name": "SQLite",
            "description": "Database queries, data analysis, metadata management",
            "command": "mcp-server-sqlite",
            "icon": "🗄️",
            "use_cases": ["Data analysis", "Metadata queries", "Result storage", "Audit logs"]
        }
    }

def render_sidebar():
    """Render the sidebar with MCP server selection"""
    st.sidebar.title("📡 MCP Servers")
    st.sidebar.markdown("Select the tools your DAG will use:")
    
    servers_info = get_mcp_servers_info()
    selected_servers = []
    
    for server_key, server_info in servers_info.items():
        with st.sidebar.expander(f"{server_info['icon']} {server_info['name']}", expanded=False):
            st.markdown(f"**{server_info['description']}**")
            st.markdown("**Use cases:**")
            for use_case in server_info['use_cases']:
                st.markdown(f"• {use_case}")
            
            if st.checkbox(f"Use {server_info['name']}", key=f"server_{server_key}"):
                selected_servers.append({
                    "name": server_key,
                    "command": server_info['command'],
                    "display_name": server_info['name']
                })
    
    return selected_servers

def render_examples():
    """Render example workflows"""
    st.markdown("### 💡 Example Workflows")
    
    examples = [
        {
            "title": "📊 Data Pipeline",
            "description": "Process CSV files from S3, transform with pandas, load to warehouse",
            "servers": ["filesystem", "sqlite"],
            "prompt": "Create a daily ETL pipeline that extracts CSV files from an S3 bucket, transforms the data using pandas to clean and aggregate it, then loads the results into a data warehouse. Include error handling and data validation steps."
        },
        {
            "title": "🐙 GitHub Analysis",
            "description": "Daily summary of repository activity and PR status",
            "servers": ["github", "slack"],
            "prompt": "Create a daily workflow that analyzes GitHub repository activity, summarizes open issues and PR status, identifies high-priority items, and sends a summary report to the team Slack channel."
        },
        {
            "title": "🔄 Release Coordination",
            "description": "Multi-tool workflow for release management",
            "servers": ["github", "slack"],
            "prompt": "Create a release coordination workflow that checks GitHub for release blockers, schedules release meetings, and notifies the team on Slack with status updates and action items."
        },
        {
            "title": "📁 File Processing",
            "description": "Monitor and process incoming files",
            "servers": ["filesystem", "sqlite"],
            "prompt": "Create a workflow that monitors a directory for new files, processes them based on file type, extracts metadata, stores results in a SQLite database, and moves processed files to an archive directory."
        }
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            with st.container():
                st.markdown(f"""
                <div class="example-card">
                    <h4>{example['title']}</h4>
                    <p>{example['description']}</p>
                    <p><strong>Uses:</strong> {', '.join(example['servers'])}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Use this example", key=f"example_{i}"):
                    st.session_state.description = example['prompt']
                    # Set server selections
                    for server in example['servers']:
                        st.session_state[f"server_{server}"] = True
                    st.rerun()

def generate_dag_preview(description: str, selected_servers: List[Dict]) -> str:
    """Generate a preview of the DAG code"""
    
    # Create MCP server configurations
    mcp_configs = []
    for server in selected_servers:
        config = {"command": server["command"]}
        
        # Add common configurations based on server type
        if server["name"] == "filesystem":
            config["args"] = ["--root", "/opt/airflow/dags"]
        elif server["name"] == "github":
            config["env"] = {"GITHUB_TOKEN": "{{ var.value.github_token }}"}
        elif server["name"] == "slack":
            config["env"] = {"SLACK_TOKEN": "{{ var.value.slack_token }}"}
        
        mcp_configs.append(config)
    
    # Generate basic DAG structure
    dag_code = f'''"""
Generated DAG: AI-powered workflow
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Description: {description}
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
    "ai_generated_workflow",
    default_args=default_args,
    description="AI-generated workflow using MCP servers",
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=["ai", "mcp", "generated"],
)

@mcp_agent(
    model="gpt-4o",
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
    {", ".join([s["display_name"] for s in selected_servers])}
    
    Provide detailed status updates and handle any errors gracefully.
    """

# Create the task
workflow_task = PythonOperator(
    task_id="execute_ai_workflow",
    python_callable=execute_workflow,
    dag=dag,
)
'''
    
    return dag_code

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🚀 Airflow AI Bridge</h1>', unsafe_allow_html=True)
    st.markdown("**Generate intelligent Airflow DAGs using AI and MCP servers**")
    
    # Sidebar
    selected_servers = render_sidebar()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📝 Describe Your Workflow")
        
        # Get description from session state if set by example
        default_description = st.session_state.get('description', '')
        
        description = st.text_area(
            "What would you like your DAG to do?",
            value=default_description,
            placeholder="Example: Create a daily ETL pipeline that processes CSV files from S3, transforms the data, and loads it into a data warehouse...",
            height=150,
            help="Describe your workflow in natural language. Be as specific as possible about data sources, transformations, and outputs."
        )
        
        # Model selection
        model = st.selectbox(
            "🤖 AI Model",
            ["gpt-4o", "gpt-4", "claude-3-sonnet", "claude-3-haiku"],
            help="Choose the AI model to generate your DAG"
        )
        
        # Advanced options
        with st.expander("⚙️ Advanced Options", expanded=False):
            schedule = st.selectbox(
                "Schedule Interval",
                ["@daily", "@hourly", "@weekly", "@monthly", "None"],
                help="How often should this DAG run?"
            )
            
            retries = st.number_input("Max Retries", min_value=0, max_value=10, value=1)
            
            tags = st.text_input(
                "Tags (comma-separated)",
                value="ai,mcp,generated",
                help="Tags to help organize your DAGs"
            )
    
    with col2:
        st.markdown("### 📡 Selected Servers")
        if selected_servers:
            for server in selected_servers:
                st.markdown(f"✅ **{server['display_name']}**")
        else:
            st.info("👈 Select MCP servers from the sidebar")
        
        st.markdown("### 📊 Generation Stats")
        st.metric("Servers Selected", len(selected_servers))
        st.metric("Description Length", len(description.split()) if description else 0)
    
    # Generate button
    st.markdown("---")
    
    if st.button("🤖 Generate DAG", type="primary", use_container_width=True):
        if not description.strip():
            st.error("❌ Please provide a workflow description")
            return
        
        if not selected_servers:
            st.warning("⚠️ No MCP servers selected. Using filesystem server by default.")
            selected_servers = [{
                "name": "filesystem",
                "command": "mcp-server-filesystem",
                "display_name": "Filesystem"
            }]
        
        with st.spinner("🔄 Generating your DAG..."):
            try:
                # Generate the DAG code
                dag_code = generate_dag_preview(description, selected_servers)
                
                st.success("✅ DAG generated successfully!")
                
                # Show the generated code
                st.markdown("### 📄 Generated DAG Code")
                st.code(dag_code, language="python")
                
                # Download button
                st.download_button(
                    label="💾 Download DAG File",
                    data=dag_code,
                    file_name=f"ai_generated_dag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py",
                    mime="text/python",
                    use_container_width=True
                )
                
                # Instructions
                st.markdown("### 🚀 Next Steps")
                st.info("""
                1. **Download** the generated DAG file
                2. **Review** the code and customize as needed
                3. **Place** the file in your Airflow DAGs directory
                4. **Configure** any required Airflow variables or connections
                5. **Enable** the DAG in the Airflow UI
                """)
                
            except Exception as e:
                st.error(f"❌ Error generating DAG: {str(e)}")
                st.info("💡 Try simplifying your description or selecting different servers")
    
    # Examples section
    st.markdown("---")
    render_examples()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        Built with ❤️ using <a href="https://github.com/astronomer/airflow-ai-bridge">airflow-ai-bridge</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 