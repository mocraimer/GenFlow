"""
Example DAG: Daily GitHub repository analysis using MCP

This example demonstrates using airflow-ai-bridge with MCP GitHub tools
to perform automated repository analysis and reporting.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.email import EmailOperator
from airflow.operators.python import PythonOperator

from airflow_ai_bridge import mcp_agent

# DAG configuration
default_args = {
    "owner": "airflow-ai-bridge",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

dag = DAG(
    "github_daily_analysis",
    default_args=default_args,
    description="Daily GitHub repository analysis and reporting",
    schedule_interval="0 8 * * *",  # Daily at 8 AM
    catchup=False,
    tags=["github", "mcp", "analysis", "daily"],
)


@mcp_agent(
    model="gpt-4o",
    system_prompt="""You are a GitHub repository analyst that provides daily insights.
    
    You have access to GitHub API through MCP tools and can:
    - List and analyze issues
    - Review pull requests
    - Check repository activity
    - Analyze contributor activity
    - Review security alerts
    
    Always provide actionable insights and prioritize items by importance.
    """,
    mcp_servers=[
        {
            "command": "mcp-server-github",
            "env": {
                "GITHUB_TOKEN": "{{ var.value.github_token }}",
                "GITHUB_REPOSITORY": "{{ var.value.github_repository }}",
            },
        }
    ],
)
def analyze_repository_health(context) -> dict:
    """
    Analyze overall repository health and activity.

    Returns:
        Dictionary with analysis results
    """
    execution_date = context["execution_date"].strftime("%Y-%m-%d")

    analysis_request = f"""
    Perform a comprehensive repository health analysis for {execution_date}:
    
    1. **Issue Analysis**:
       - Count of open issues by label/priority
       - New issues created in the last 24 hours
       - Issues that have been open for >30 days
       - Critical issues that need immediate attention
    
    2. **Pull Request Review**:
       - Open PRs awaiting review
       - PRs that have been open >7 days
       - Recently merged PRs (last 24 hours)
       - PRs with conflicts or failing checks
    
    3. **Repository Activity**:
       - New commits in the last 24 hours
       - Active contributors
       - Release readiness status
    
    4. **Health Metrics**:
       - Security alerts (if any)
       - Dependency updates needed
       - Code quality trends
    
    Provide a structured summary with priority rankings and recommended actions.
    """

    return analysis_request


@mcp_agent(
    model="gpt-4o",
    system_prompt="""You are a GitHub issue triager that categorizes and prioritizes issues.
    
    Focus on:
    - Identifying critical bugs
    - Categorizing feature requests
    - Suggesting labels and assignees
    - Estimating complexity
    """,
    mcp_servers=[
        {
            "command": "mcp-server-github",
            "env": {
                "GITHUB_TOKEN": "{{ var.value.github_token }}",
                "GITHUB_REPOSITORY": "{{ var.value.github_repository }}",
            },
        }
    ],
)
def triage_new_issues(context) -> dict:
    """
    Triage and categorize new issues from the last 24 hours.

    Returns:
        Dictionary with triage results
    """
    return """
    Triage all issues created in the last 24 hours:
    
    For each new issue:
    1. **Categorization**:
       - Type: bug, feature, enhancement, question, documentation
       - Priority: critical, high, medium, low
       - Component: which part of the system is affected
    
    2. **Analysis**:
       - Completeness of issue description
       - Steps to reproduce (for bugs)
       - Acceptance criteria (for features)
    
    3. **Recommendations**:
       - Suggested labels to add
       - Potential assignees based on expertise
       - Estimated effort/complexity
       - Related issues or duplicates
    
    4. **Actions Needed**:
       - Issues requiring immediate attention
       - Issues needing more information
       - Issues that can be closed (duplicates, invalid)
    
    Return a summary with actionable recommendations for each issue.
    """


@mcp_agent(
    model="gpt-4o",
    system_prompt="""You are a code review assistant that analyzes pull requests.
    
    Focus on:
    - Code quality and best practices
    - Security considerations
    - Performance implications
    - Testing coverage
    """,
    mcp_servers=[
        {
            "command": "mcp-server-github",
            "env": {
                "GITHUB_TOKEN": "{{ var.value.github_token }}",
                "GITHUB_REPOSITORY": "{{ var.value.github_repository }}",
            },
        }
    ],
)
def review_pull_requests(context) -> dict:
    """
    Review open pull requests and provide insights.

    Returns:
        Dictionary with PR review results
    """
    return """
    Review all open pull requests:
    
    For each PR:
    1. **Status Check**:
       - CI/CD pipeline status
       - Merge conflicts
       - Review status (approved, changes requested, pending)
    
    2. **Code Analysis**:
       - Size and complexity of changes
       - Areas of code modified
       - Potential impact on system
    
    3. **Quality Assessment**:
       - Code quality and best practices
       - Security considerations
       - Performance implications
       - Test coverage
    
    4. **Review Recommendations**:
       - PRs ready to merge
       - PRs needing additional review
       - PRs requiring changes
       - Stale PRs (open >7 days)
    
    5. **Priority Actions**:
       - Critical PRs blocking releases
       - PRs from external contributors
       - PRs addressing security issues
    
    Provide prioritized recommendations for maintainer actions.
    """


@mcp_agent(
    model="gpt-4o",
    system_prompt="You are a release planning assistant that helps coordinate releases.",
    mcp_servers=[
        {
            "command": "mcp-server-github",
            "env": {
                "GITHUB_TOKEN": "{{ var.value.github_token }}",
                "GITHUB_REPOSITORY": "{{ var.value.github_repository }}",
            },
        }
    ],
)
def assess_release_readiness(context) -> dict:
    """
    Assess readiness for next release.

    Returns:
        Dictionary with release assessment
    """
    return """
    Assess release readiness:
    
    1. **Release Blockers**:
       - Critical bugs that must be fixed
       - Security issues requiring patches
       - Breaking changes needing documentation
    
    2. **Feature Completeness**:
       - Features targeted for this release
       - Completion status of major features
       - Testing status
    
    3. **Quality Gates**:
       - All tests passing
       - No regressions detected
       - Documentation updated
       - Changelog prepared
    
    4. **Risk Assessment**:
       - New features stability
       - Dependency updates impact
       - Backward compatibility
    
    5. **Release Recommendations**:
       - Go/no-go recommendation
       - Suggested release timeline
       - Pre-release tasks needed
       - Post-release monitoring plan
    
    Provide a clear release readiness assessment with action items.
    """


def format_daily_report(**context) -> str:
    """
    Format the daily GitHub analysis report.

    Returns:
        Formatted HTML report
    """
    # Get results from previous tasks
    ti = context["ti"]

    repo_health = ti.xcom_pull(task_ids="analyze_repository_health")
    issue_triage = ti.xcom_pull(task_ids="triage_new_issues")
    pr_review = ti.xcom_pull(task_ids="review_pull_requests")
    release_status = ti.xcom_pull(task_ids="assess_release_readiness")

    execution_date = context["execution_date"].strftime("%Y-%m-%d")

    html_report = f"""
    <html>
    <head>
        <title>GitHub Daily Report - {execution_date}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #0366d6; }}
            .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #0366d6; }}
            .critical {{ border-left-color: #d73a49; }}
            .warning {{ border-left-color: #f66a0a; }}
            .success {{ border-left-color: #28a745; }}
        </style>
    </head>
    <body>
        <h1>GitHub Daily Report - {execution_date}</h1>
        
        <div class="section">
            <h2>Repository Health</h2>
            <pre>{repo_health}</pre>
        </div>
        
        <div class="section">
            <h2>Issue Triage</h2>
            <pre>{issue_triage}</pre>
        </div>
        
        <div class="section">
            <h2>Pull Request Review</h2>
            <pre>{pr_review}</pre>
        </div>
        
        <div class="section">
            <h2>Release Readiness</h2>
            <pre>{release_status}</pre>
        </div>
        
        <div class="section">
            <h2>Next Steps</h2>
            <p>This report was generated automatically by airflow-ai-bridge.</p>
            <p>Review the recommendations and take appropriate actions.</p>
        </div>
    </body>
    </html>
    """

    return html_report


# Task definitions
analyze_health_task = PythonOperator(
    task_id="analyze_repository_health",
    python_callable=analyze_repository_health,
    dag=dag,
)

triage_issues_task = PythonOperator(
    task_id="triage_new_issues",
    python_callable=triage_new_issues,
    dag=dag,
)

review_prs_task = PythonOperator(
    task_id="review_pull_requests",
    python_callable=review_pull_requests,
    dag=dag,
)

assess_release_task = PythonOperator(
    task_id="assess_release_readiness",
    python_callable=assess_release_readiness,
    dag=dag,
)

format_report_task = PythonOperator(
    task_id="format_daily_report",
    python_callable=format_daily_report,
    dag=dag,
)

send_report_task = EmailOperator(
    task_id="send_daily_report",
    to=["{{ var.value.github_report_recipients }}"],
    subject="GitHub Daily Report - {{ ds }}",
    html_content='{{ ti.xcom_pull(task_ids="format_daily_report") }}',
    dag=dag,
)

# Set task dependencies - run analysis tasks in parallel, then format and send report
(
    [analyze_health_task, triage_issues_task, review_prs_task, assess_release_task]
    >> format_report_task
    >> send_report_task
)


if __name__ == "__main__":
    # Test the DAG locally
    print("Testing GitHub daily analysis...")

    # Mock context for testing
    test_context = {"execution_date": datetime(2024, 1, 15, 8, 0, 0)}

    # This would require actual GitHub credentials and repository access
    print("Note: This example requires GitHub token and repository configuration")
    print("Set the following Airflow variables:")
    print("- github_token: Your GitHub personal access token")
    print("- github_repository: Repository to analyze (e.g., 'owner/repo')")
    print("- github_report_recipients: Email addresses for reports")
