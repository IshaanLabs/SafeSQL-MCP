"""
╔══════════════════════════════════════════════════════════════════╗
║                    SQL AI AGENT                                   ║
║          AI-Powered Database Operations Assistant                 ║
║                                                                  ║
║  An intelligent agent that translates natural language into       ║
║  safe, audited SQL operations with human-in-the-loop approval.   ║
╚══════════════════════════════════════════════════════════════════╝

Usage:
    python app.py                   → Interactive CLI agent
    python app.py --mode mcp        → Start MCP server
    python app.py --mode api        → Start FastAPI server (future)
    python app.py --health          → Health check
"""

import sys
import os
import argparse
import asyncio
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import Client
from config import MODEL_NAME, OLLAMA_BASE_URL, NORTHWIND_DB_PATH, AUDIT_DB_PATH
from db import setup_audit_db, get_northwind_db
from logger import get_logger

logger = get_logger("app")

# ─────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────

APP_NAME = "SQL AI Agent"
VERSION = "1.0.0"

BANNER = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    {APP_NAME} v{VERSION}                         ║
║          AI-Powered Database Operations Assistant                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Commands:
  Type any natural language question to query/modify the database.

  Special commands:
    /tables         → List all database tables
    /schema <table> → Show schema for a table
    /explain <sql>  → Explain a SQL query
    /preview <sql>  → Preview impact of a write query
    /history        → Show recent audit logs
    /approve        → Approve pending operation
    /reject         → Reject pending operation
    /status         → Show agent status
    /clear          → Clear conversation history
    /help           → Show this help
    /quit           → Exit the agent

  Examples:
    "Show me top 10 customers by revenue"
    "How many orders were placed last month?"
    "Update product prices by 5% for beverages"
    "Delete all cancelled orders"
"""

# ─────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────

def health_check() -> bool:
    """Verify all dependencies are available and working."""
    checks = {}

    # Check Northwind DB
    try:
        assert os.path.exists(NORTHWIND_DB_PATH)
        db = get_northwind_db()
        tables = db.get_usable_table_names()
        assert len(tables) > 0
        checks["northwind_db"] = f"OK ({len(tables)} tables)"
    except Exception as e:
        checks["northwind_db"] = f"FAIL: {e}"

    # Check Audit DB
    try:
        setup_audit_db()
        assert os.path.exists(AUDIT_DB_PATH)
        checks["audit_db"] = "OK"
    except Exception as e:
        checks["audit_db"] = f"FAIL: {e}"

    # Check LLM connectivity
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=MODEL_NAME)
        response = llm.invoke("Say OK")
        assert response.content
        checks["llm"] = f"OK ({MODEL_NAME})"
    except Exception as e:
        checks["llm"] = f"FAIL: {e}"

    # Check LangGraph
    try:
        from graph import agent
        assert agent is not None
        checks["langgraph"] = "OK (graph compiled)"
    except Exception as e:
        checks["langgraph"] = f"FAIL: {e}"

    # Print results
    print(f"\n{'─' * 50}")
    print(f"  {APP_NAME} - Health Check")
    print(f"{'─' * 50}")
    for component, status in checks.items():
        icon = "✓" if "OK" in status else "✗"
        print(f"  {icon} {component:20s} {status}")
    print(f"{'─' * 50}\n")

    all_ok = all("OK" in v for v in checks.values())
    return all_ok


# ─────────────────────────────────────────────────────────────────
# Interactive CLI Agent
# ─────────────────────────────────────────────────────────────────

class SQLAgent:
    """Interactive CLI agent that connects to MCP server via SSE."""

    def __init__(self, server_url="http://127.0.0.1:8100/sse"):
        self.server_url = server_url
        self.conversation_history = []
        self.pending_approval = None

        logger.info(f"SQL Agent initialized, connecting to {server_url}")

    def _get_loop(self):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def _call_tool(self, tool_name: str, arguments: dict = None) -> str:
        async def _call():
            client = Client(self.server_url)
            async with client:
                result = await client.call_tool(tool_name, arguments or {})
                # Extract text from CallToolResult
                if hasattr(result, 'content'):
                    parts = result.content
                    if isinstance(parts, list):
                        return "\n".join(p.text if hasattr(p, 'text') else str(p) for p in parts)
                    return str(parts)
                return str(result)

        loop = self._get_loop()
        return loop.run_until_complete(_call())

    def _check_connection(self) -> bool:
        try:
            async def _ping():
                client = Client(self.server_url)
                async with client:
                    await client.list_tools()
                    return True
            loop = self._get_loop()
            return loop.run_until_complete(_ping())
        except Exception:
            return False

    def _print_response(self, text: str):
        print(f"\n  🤖 {text}\n")

    def _print_info(self, text: str):
        print(f"  ℹ  {text}")

    def _print_warning(self, text: str):
        print(f"  ⚠  {text}")

    def _print_error(self, text: str):
        print(f"  ✗  {text}")

    def _print_success(self, text: str):
        print(f"  ✓  {text}")

    def handle_tables(self):
        result = self._call_tool("get_tables")
        self._print_response(result)

    def handle_schema(self, args: str):
        if not args:
            self._print_error("Usage: /schema <table_name>")
            return
        result = self._call_tool("get_database_schema", {"table_names": args.strip()})
        print(f"\n{result}\n")

    def handle_explain(self, args: str):
        if not args:
            self._print_error("Usage: /explain <sql_query>")
            return
        result = self._call_tool("explain_sql", {"sql": args.strip()})
        self._print_response(result)

    def handle_preview(self, args: str):
        if not args:
            self._print_error("Usage: /preview <sql_query>")
            return
        result = self._call_tool("preview_write_operation", {"sql": args.strip()})
        self._print_response(result)

    def handle_history(self):
        result = self._call_tool("get_audit_logs", {"limit": 10})
        print(f"\n  {result}\n")

    def handle_approve(self):
        if not self.pending_approval:
            self._print_error("No pending operation to approve")
            return

        self._print_info("Approving operation...")
        result = self._call_tool("approve_operation", {
            "thread_id": self.pending_approval,
            "approved_by": "cli_user"
        })
        self.pending_approval = None
        self._print_success("Approved and executed")
        self._print_response(result)

    def handle_reject(self):
        if not self.pending_approval:
            self._print_error("No pending operation to reject")
            return

        self._print_info("Rejecting operation...")
        result = self._call_tool("reject_operation", {
            "thread_id": self.pending_approval,
            "reason": "Rejected by CLI user"
        })
        self.pending_approval = None
        self._print_warning("Operation rejected. No changes made.")

    def handle_status(self):
        print(f"\n  {'─' * 40}")
        print(f"  Agent Status")
        print(f"  {'─' * 40}")
        self._print_info(f"Server: {self.server_url}")
        self._print_info(f"Connected: {self._check_connection()}")
        self._print_info(f"Conversation turns: {len(self.conversation_history)}")
        pending = "Yes" if self.pending_approval else "No"
        self._print_info(f"Pending approval: {pending}")
        print(f"  {'─' * 40}\n")

    def handle_clear(self):
        self.conversation_history = []
        self._print_success("Conversation history cleared")

    def handle_question(self, question: str):
        """Process a natural language question through the MCP server."""
        start_time = time.time()
        result = self._call_tool("ask_database", {"question": question})
        elapsed = time.time() - start_time

        # Check if approval is needed
        if "APPROVAL REQUIRED" in result:
            # Extract thread_id
            lines = result.split("\n")
            thread_line = next((l for l in lines if l.startswith("Thread ID:")), "")
            thread_id = thread_line.replace("Thread ID: ", "").strip()
            self.pending_approval = thread_id

            print(f"\n  {'━' * 50}")
            print(f"  ⏸  APPROVAL REQUIRED")
            print(f"  {'━' * 50}")
            for line in lines:
                if line.startswith("SQL:") or line.startswith("Risk Level:") or line.startswith("Rows Affected:"):
                    self._print_info(line)
            print(f"  {'━' * 50}")
            print(f"  Type /approve to execute or /reject to cancel")
            print(f"  {'━' * 50}\n")
        else:
            self._print_response(result)
            self._print_info(f"({elapsed:.1f}s)")

        # Update conversation history
        self.conversation_history.append(f"User: {question}")
        self.conversation_history.append(f"Agent: {result[:200]}")

    def run(self):
        """Main interactive loop."""
        print(BANNER)

        # Check connection
        if not self._check_connection():
            self._print_error(f"Cannot connect to MCP server at {self.server_url}")
            self._print_info("Start the server first: python app.py --mode http")
            return

        self._print_success(f"Connected to MCP server at {self.server_url}")
        self._print_success("Agent ready. Type /help for commands.\n")

        while True:
            try:
                user_input = input("  You → ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.startswith("/"):
                    cmd_parts = user_input.split(" ", 1)
                    cmd = cmd_parts[0].lower()
                    args = cmd_parts[1] if len(cmd_parts) > 1 else ""

                    if cmd in ("/quit", "/exit", "/q"):
                        self._print_info("Shutting down agent. Goodbye!")
                        logger.info("Agent shutdown by user")
                        break
                    elif cmd == "/help":
                        print(HELP_TEXT)
                    elif cmd == "/tables":
                        self.handle_tables()
                    elif cmd == "/schema":
                        self.handle_schema(args)
                    elif cmd == "/explain":
                        self.handle_explain(args)
                    elif cmd == "/preview":
                        self.handle_preview(args)
                    elif cmd == "/history":
                        self.handle_history()
                    elif cmd == "/approve":
                        self.handle_approve()
                    elif cmd == "/reject":
                        self.handle_reject()
                    elif cmd == "/status":
                        self.handle_status()
                    elif cmd == "/clear":
                        self.handle_clear()
                    else:
                        self._print_error(f"Unknown command: {cmd}. Type /help for available commands.")
                else:
                    self.handle_question(user_input)

            except KeyboardInterrupt:
                print("\n")
                self._print_info("Use /quit to exit gracefully.")
            except EOFError:
                self._print_info("Shutting down agent. Goodbye!")
                break
            except Exception as e:
                self._print_error(f"Unexpected error: {e}")
                logger.exception(f"Unhandled error in CLI loop: {e}")


# ─────────────────────────────────────────────────────────────────
# MCP Server Mode
# ─────────────────────────────────────────────────────────────────

def run_mcp_server():
    """Start the MCP server in stdio mode."""
    logger.info("Starting MCP server (stdio)")
    print(BANNER)
    print("  Starting MCP Server...")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Ollama: {OLLAMA_BASE_URL}")
    print(f"  Database: {NORTHWIND_DB_PATH}")
    print(f"  Mode: MCP (stdio)\n")

    from server import mcp
    mcp.run(transport="stdio")


def run_mcp_http_server(host="127.0.0.1", port=8100):
    """Start the MCP server in SSE mode for Streamlit and CLI."""
    logger.info(f"Starting MCP SSE server on {host}:{port}")
    print(BANNER)
    print("  Starting MCP SSE Server...")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Ollama: {OLLAMA_BASE_URL}")
    print(f"  Database: {NORTHWIND_DB_PATH}")
    print(f"  Mode: SSE (Server-Sent Events)")
    print(f"  URL: http://{host}:{port}/mcp")
    print(f"\n  Clients can now connect:")
    print(f"    → Streamlit: streamlit run streamlit_app.py")
    print(f"    → CLI:       python app.py --mode cli\n")

    from server import mcp
    mcp.run(transport="streamable-http", host=host, port=port)


# ─────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        prog="sql-ai-agent",
        description=f"{APP_NAME} - AI-Powered Database Operations Assistant"
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "mcp", "http"],
        default="cli",
        help="Run mode: 'cli' for interactive terminal, 'mcp' for MCP stdio server, 'http' for MCP SSE server (default: cli)"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run health check and exit"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8100,
        help="Port for SSE server (default: 8100)"
    )
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:8100/mcp",
        help="MCP server URL for CLI mode (default: http://127.0.0.1:8100/mcp)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} v{VERSION}"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info(f"{APP_NAME} v{VERSION} starting | mode={args.mode}")

    # Health check mode
    if args.health:
        healthy = health_check()
        sys.exit(0 if healthy else 1)

    # Initialize audit DB
    setup_audit_db()

    # Run selected mode
    if args.mode == "mcp":
        run_mcp_server()
    elif args.mode == "http":
        run_mcp_http_server(host=args.host, port=args.port)
    else:
        agent = SQLAgent(server_url=args.server_url)
        agent.run()

    logger.info(f"{APP_NAME} shutdown complete")


if __name__ == "__main__":
    main()
