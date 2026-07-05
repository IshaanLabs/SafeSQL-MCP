"""
MCP Server for SQL AI Agent
Exposes tools for database operations via FastMCP.
The MCP client calls tools, the server orchestrates the LangGraph agent.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP
from langgraph.types import Command

from graph import agent
from tools.schema import list_tables, get_schema, describe_table
from tools.query import query_database, explain_query
from tools.write import preview_update
from tools.audit import get_execution_history
from db import setup_audit_db
from logger import get_logger

logger = get_logger("server")

# Initialize
setup_audit_db()

mcp = FastMCP(
    name="SQL AI Agent",
    instructions="""You are an AI Database Operations Assistant.
    You help users query and modify databases using natural language.
    For read operations, results are returned immediately.
    For write operations (UPDATE, DELETE), you must preview the impact and get approval before executing.
    DROP and TRUNCATE operations are blocked entirely."""
)


# --- Thread management ---
_thread_counter = 0

def _next_thread_id() -> str:
    global _thread_counter
    _thread_counter += 1
    return f"mcp-thread-{_thread_counter}"


# Store pending approvals: thread_id -> state snapshot
_pending_approvals = {}


# --- MCP Tools ---

@mcp.tool()
def ask_database(question: str) -> str:
    """
    Ask a natural language question about the database.
    For read queries, returns results immediately.
    For write queries, returns a preview and asks for approval.
    """
    logger.info(f"ask_database called: {question}")

    thread_id = _next_thread_id()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_question": question,
        "conversation_history": [],
    }

    result = agent.invoke(initial_state, config=config)

    # Check if interrupted (needs approval)
    state = agent.get_state(config)
    is_interrupted = len(state.tasks) > 0 and any(
        hasattr(t, 'interrupts') and t.interrupts for t in state.tasks
    )

    if is_interrupted:
        # Store for later approval
        _pending_approvals[thread_id] = config

        # Get interrupt details
        interrupt_info = {}
        for task in state.tasks:
            if hasattr(task, 'interrupts') and task.interrupts:
                for intr in task.interrupts:
                    interrupt_info = intr.value

        return (
            f"⏸ APPROVAL REQUIRED\n\n"
            f"SQL: {interrupt_info.get('sql', 'N/A')}\n"
            f"Risk Level: {interrupt_info.get('risk_level', 'N/A')}\n"
            f"Rows Affected: {interrupt_info.get('rows_affected', 'Unknown')}\n\n"
            f"Thread ID: {thread_id}\n"
            f"Use approve_operation(thread_id='{thread_id}') to approve\n"
            f"Use reject_operation(thread_id='{thread_id}') to reject"
        )

    # Completed without interrupt
    return result.get("final_response", "No response generated")


@mcp.tool()
def approve_operation(thread_id: str, approved_by: str = "user") -> str:
    """Approve a pending write operation that requires human approval."""
    logger.info(f"approve_operation called: thread={thread_id}, by={approved_by}")

    if thread_id not in _pending_approvals:
        return f"No pending operation found for thread: {thread_id}"

    config = _pending_approvals.pop(thread_id)

    result = agent.invoke(
        Command(resume={"approved": True, "approved_by": approved_by}),
        config=config
    )

    return result.get("final_response", "Operation executed successfully")


@mcp.tool()
def reject_operation(thread_id: str, reason: str = "") -> str:
    """Reject a pending write operation."""
    logger.info(f"reject_operation called: thread={thread_id}, reason={reason}")

    if thread_id not in _pending_approvals:
        return f"No pending operation found for thread: {thread_id}"

    config = _pending_approvals.pop(thread_id)

    result = agent.invoke(
        Command(resume={"approved": False, "approved_by": "user"}),
        config=config
    )

    return result.get("final_response", "Operation rejected. No changes made.")


@mcp.tool()
def get_database_schema(table_names: str = "") -> str:
    """Get the schema for database tables. Pass comma-separated table names, or empty for all."""
    logger.info(f"get_database_schema called: {table_names}")
    if table_names:
        return get_schema(table_names)
    return get_schema()


@mcp.tool()
def get_tables() -> str:
    """List all available database tables."""
    logger.info("get_tables called")
    tables = list_tables()
    return f"Available tables: {', '.join(tables)}"


@mcp.tool()
def describe_database_table(table_name: str) -> str:
    """Get detailed schema information for a specific table."""
    logger.info(f"describe_database_table called: {table_name}")
    return describe_table(table_name)


@mcp.tool()
def run_read_query(sql: str) -> str:
    """Execute a read-only SQL query directly. Only SELECT statements allowed."""
    logger.info(f"run_read_query called: {sql}")
    return query_database(sql)


@mcp.tool()
def explain_sql(sql: str) -> str:
    """Explain what a SQL query does in plain English."""
    logger.info(f"explain_sql called: {sql}")
    return explain_query(sql)


@mcp.tool()
def preview_write_operation(sql: str) -> str:
    """Preview the impact of a write operation without executing it."""
    logger.info(f"preview_write_operation called: {sql}")
    result = preview_update(sql)
    if "error" in result:
        return f"Error: {result['error']}"
    return (
        f"Preview:\n"
        f"  Original SQL: {result['original_sql']}\n"
        f"  Rows affected: {result['rows_affected']}\n"
        f"  Preview query: {result['preview_sql']}"
    )


@mcp.tool()
def get_audit_logs(limit: int = 10) -> str:
    """Get recent execution audit logs."""
    logger.info(f"get_audit_logs called: limit={limit}")
    history = get_execution_history(limit)
    if not history:
        return "No audit logs found"

    lines = []
    for entry in history:
        lines.append(
            f"[{entry['timestamp']}] {entry['operation_type']} | "
            f"{entry['status']} | {entry['user_question'][:50]} | "
            f"Rows: {entry['rows_affected']}"
        )
    return "\n".join(lines)


# --- Entry point ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "sse"], default="sse",
                        help="Transport mode: 'stdio' for MCP clients, 'sse' for Streamlit/web (default: sse)")
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE transport")
    parser.add_argument("--port", type=int, default=8100, help="Port for SSE transport")
    args = parser.parse_args()

    if args.transport == "sse":
        logger.info(f"Starting SQL AI MCP Server (SSE) on {args.host}:{args.port}")
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        logger.info("Starting SQL AI MCP Server (stdio)")
        mcp.run()
