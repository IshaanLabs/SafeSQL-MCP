"""
SafeSQL-MCP — Streamlit Web UI
LangGraph-powered MCP server for natural language SQL
with human-in-the-loop approval for database write operations.
"""

import streamlit as st
import asyncio
import time
import json
from fastmcp import Client

# ─────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SafeSQL-MCP",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────
# Custom CSS — Professional Dark Theme
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .block-container { padding-top: 1rem; }

    .brand-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(74, 144, 226, 0.3);
        box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    }
    .brand-header h1 {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.8rem;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .brand-header .subtitle {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 0.3rem;
        font-weight: 400;
    }
    .brand-header .badge {
        display: inline-block;
        background: rgba(74, 144, 226, 0.2);
        border: 1px solid rgba(74, 144, 226, 0.4);
        color: #7dd3fc;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 0.5rem;
        vertical-align: middle;
    }

    .status-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .status-card .label {
        color: #94a3b8;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .status-card .value {
        color: #e2e8f0;
        font-size: 1.4rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }

    .risk-safe { color: #4ade80; }
    .risk-low { color: #a3e635; }
    .risk-medium { color: #fbbf24; }
    .risk-high { color: #f87171; }
    .risk-blocked { color: #c084fc; }

    .approval-banner {
        background: linear-gradient(135deg, #451a03 0%, #78350f 100%);
        border: 1px solid #d97706;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
    }
    .approval-banner h3 {
        color: #fbbf24;
        margin: 0 0 0.5rem 0;
        font-size: 1.1rem;
    }
    .approval-banner p {
        color: #fde68a;
        margin: 0.2rem 0;
        font-size: 0.9rem;
    }

    .tool-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.6rem;
        transition: border-color 0.2s;
    }
    .tool-card:hover {
        border-color: #4a90e2;
    }
    .tool-card .tool-name {
        color: #7dd3fc;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .tool-card .tool-desc {
        color: #94a3b8;
        font-size: 0.78rem;
        margin-top: 0.2rem;
    }

    .footer-bar {
        text-align: center;
        color: #475569;
        font-size: 0.75rem;
        padding: 1.5rem 0 0.5rem 0;
        border-top: 1px solid #1e293b;
        margin-top: 2rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────────

defaults = {
    "messages": [],
    "pending_approval": None,
    "query_count": 0,
    "read_count": 0,
    "write_count": 0,
    "mcp_connected": False,
    "mcp_tools": [],
    "db_tables": None,
    "last_error": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────
# MCP Client
# ─────────────────────────────────────────────────────────────────

MCP_SERVER_URL = "http://127.0.0.1:8100/mcp"


def get_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def call_mcp_tool(tool_name: str, arguments: dict = None) -> str:
    async def _call():
        client = Client(MCP_SERVER_URL)
        async with client:
            result = await client.call_tool(tool_name, arguments or {})
            if hasattr(result, 'content'):
                parts = result.content
                if isinstance(parts, list):
                    return "\n".join(p.text if hasattr(p, 'text') else str(p) for p in parts)
                return str(parts)
            return str(result)
    return get_event_loop().run_until_complete(_call())


def get_available_tools() -> list:
    async def _list():
        client = Client(MCP_SERVER_URL)
        async with client:
            tools = await client.list_tools()
            return [(t.name, t.description or "") for t in tools]
    return get_event_loop().run_until_complete(_list())


def check_connection() -> bool:
    try:
        tools = get_available_tools()
        st.session_state.mcp_connected = True
        st.session_state.mcp_tools = tools
        return True
    except Exception as e:
        st.session_state.mcp_connected = False
        st.session_state.last_error = str(e)
        return False


# ─────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="brand-header">
    <h1>🛡️ SafeSQL-MCP <span class="badge">v1.0</span></h1>
    <div class="subtitle">LangGraph-powered natural language SQL with human-in-the-loop approval for write operations</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🛡️ SafeSQL-MCP")
    st.caption("Secure AI Database Assistant")
    st.markdown("---")

    # Connection
    connected = check_connection()
    if connected:
        st.success(f"✅ Connected — {len(st.session_state.mcp_tools)} tools available")
    else:
        st.error("❌ MCP Server Offline")
        st.code("python app.py --mode http", language="bash")
        if st.session_state.last_error:
            st.caption(f"Error: {st.session_state.last_error[:120]}")

    st.markdown("---")

    # Session Metrics
    st.markdown("### 📊 Session Metrics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total", st.session_state.query_count)
    c2.metric("Reads", st.session_state.read_count)
    c3.metric("Writes", st.session_state.write_count)

    st.markdown("---")

    # Database Tables
    st.markdown("### 🗄️ Database")
    if connected:
        if st.button("🔄 Refresh Tables", use_container_width=True):
            try:
                st.session_state.db_tables = call_mcp_tool("get_tables")
            except Exception as e:
                st.error(str(e))
        if st.session_state.db_tables:
            tables_str = st.session_state.db_tables.replace("Available tables: ", "")
            for t in tables_str.split(", "):
                st.markdown(f"  `{t.strip()}`")

    st.markdown("---")

    # Risk Legend
    st.markdown("### ⚡ Risk Levels")
    st.markdown("""
    - 🟢 **SAFE** — SELECT queries
    - 🔵 **LOW** — INSERT operations
    - 🟡 **MEDIUM** — UPDATE operations
    - 🔴 **HIGH** — DELETE / ALTER
    - 🟣 **BLOCKED** — DROP / TRUNCATE
    """)

    st.markdown("---")

    if st.button("🗑️ Clear Session", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

    st.markdown("---")
    st.caption("Built with LangGraph + Ollama + FastMCP")


# ─────────────────────────────────────────────────────────────────
# Chat Input (must be at top level, outside tabs)
# ─────────────────────────────────────────────────────────────────

prompt = st.chat_input("Ask anything about your database...", disabled=not connected)

# ─────────────────────────────────────────────────────────────────
# Main Tabs
# ─────────────────────────────────────────────────────────────────

tab_chat, tab_schema, tab_query, tab_audit, tab_tools = st.tabs([
    "💬 Chat Assistant",
    "📋 Schema Explorer",
    "🔍 SQL Workbench",
    "📜 Audit Trail",
    "🔧 MCP Tools"
])


# ═══════════════════════════════════════════════════════════════════
# TAB 1: Chat Assistant
# ═══════════════════════════════════════════════════════════════════

with tab_chat:
    st.markdown("##### Ask questions in natural language — SafeSQL handles the rest")
    st.caption("Read queries execute instantly. Write operations require your explicit approval before execution.")

    # Chat history
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]

        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
        elif role == "agent":
            with st.chat_message("assistant", avatar="🛡️"):
                st.markdown(content)
                if message.get("metadata"):
                    meta = message["metadata"]
                    cols = st.columns(4)
                    cols[0].caption(f"⏱ {meta.get('time', '—')}s")
                    cols[1].caption(f"📝 {meta.get('operation', '—')}")
                    risk = meta.get('risk', '—')
                    cols[2].caption(f"⚡ {risk}")
                    cols[3].caption(f"🧵 {meta.get('thread', '—')}")
        elif role == "approval":
            with st.chat_message("assistant", avatar="⚠️"):
                st.warning(content)

    # Pending Approval
    if st.session_state.pending_approval:
        pending = st.session_state.pending_approval
        st.markdown("---")
        st.markdown(f"""
<div class="approval-banner">
    <h3>⏸️ Human Approval Required</h3>
    <p><strong>SQL:</strong> <code>{pending['sql']}</code></p>
    <p><strong>Risk Level:</strong> {pending['risk']} &nbsp;|&nbsp; <strong>Estimated Rows:</strong> {pending['rows']}</p>
    <p><strong>Thread:</strong> {pending['thread_id']}</p>
</div>
""", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
                with st.spinner("Executing approved operation..."):
                    try:
                        result = call_mcp_tool("approve_operation", {
                            "thread_id": pending["thread_id"],
                            "approved_by": "streamlit_user"
                        })
                        st.session_state.messages.append({
                            "role": "agent",
                            "content": f"✅ **Approved & Executed**\n\n{result}",
                            "metadata": {"operation": "WRITE", "risk": pending["risk"], "time": "—", "thread": pending["thread_id"]}
                        })
                        st.session_state.write_count += 1
                        st.session_state.pending_approval = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Execution failed: {e}")
        with col2:
            if st.button("❌ Reject", type="secondary", use_container_width=True):
                try:
                    call_mcp_tool("reject_operation", {
                        "thread_id": pending["thread_id"],
                        "reason": "Rejected via SafeSQL UI"
                    })
                    st.session_state.messages.append({
                        "role": "agent",
                        "content": "❌ **Operation Rejected** — No changes were made to the database.",
                        "metadata": {"operation": "REJECTED", "risk": pending["risk"], "time": "—", "thread": pending["thread_id"]}
                    })
                    st.session_state.pending_approval = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown("---")

# ─────────────────────────────────────────────────────────────────
# Process Chat Input (outside tabs)
# ─────────────────────────────────────────────────────────────────

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with tab_chat:
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🛡️"):
            with st.spinner("🔄 Analyzing your request..."):
                start_time = time.time()
                try:
                    result = call_mcp_tool("ask_database", {"question": prompt})
                    elapsed = round(time.time() - start_time, 1)
                    st.session_state.query_count += 1

                    if "APPROVAL REQUIRED" in result:
                        lines = result.split("\n")
                        sql = next((l.replace("SQL: ", "").strip() for l in lines if l.startswith("SQL:")), "N/A")
                        risk = next((l.replace("Risk Level: ", "").strip() for l in lines if l.startswith("Risk Level:")), "N/A")
                        rows = next((l.replace("Rows Affected: ", "").strip() for l in lines if l.startswith("Rows Affected:")), "?")
                        thread_id = next((l.replace("Thread ID: ", "").strip() for l in lines if l.startswith("Thread ID:")), "N/A")

                        st.session_state.pending_approval = {
                            "sql": sql, "risk": risk, "rows": rows, "thread_id": thread_id
                        }
                        approval_msg = (
                            f"⏸️ **Approval Required**\n\n"
                            f"```sql\n{sql}\n```\n\n"
                            f"| Risk Level | Rows Affected | Thread |\n"
                            f"|:---:|:---:|:---:|\n"
                            f"| **{risk}** | **{rows}** | `{thread_id}` |\n\n"
                            f"👆 Use the buttons above to approve or reject."
                        )
                        st.warning(approval_msg)
                        st.session_state.messages.append({"role": "approval", "content": approval_msg})
                        st.rerun()
                    else:
                        st.markdown(result)
                        st.session_state.read_count += 1
                        st.session_state.messages.append({
                            "role": "agent",
                            "content": result,
                            "metadata": {"time": elapsed, "operation": "READ", "risk": "SAFE", "thread": "—"}
                        })
                except Exception as e:
                    error_msg = f"❌ **Error:** {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "agent", "content": error_msg})


# ═══════════════════════════════════════════════════════════════════
# TAB 2: Schema Explorer
# ═══════════════════════════════════════════════════════════════════

with tab_schema:
    st.markdown("##### 📋 Explore your database schema")
    st.caption("View table structures, columns, types, and relationships.")

    if not connected:
        st.warning("Connect to MCP server to explore schema.")
    else:
        col_left, col_right = st.columns([1, 2])

        with col_left:
            st.markdown("**Available Tables**")
            if st.button("🔄 Load Tables", key="schema_load", use_container_width=True):
                try:
                    st.session_state.db_tables = call_mcp_tool("get_tables")
                except Exception as e:
                    st.error(str(e))

            if st.session_state.db_tables:
                tables_str = st.session_state.db_tables.replace("Available tables: ", "")
                table_list = [t.strip() for t in tables_str.split(",")]
                selected_table = st.selectbox("Select a table:", table_list, key="schema_table_select")
            else:
                selected_table = None
                st.info("Click 'Load Tables' to see available tables.")

        with col_right:
            if selected_table:
                st.markdown(f"**Schema for `{selected_table}`**")
                with st.spinner(f"Loading schema for {selected_table}..."):
                    try:
                        schema = call_mcp_tool("get_database_schema", {"table_names": selected_table})
                        st.code(schema, language="sql")
                    except Exception as e:
                        st.error(f"Error: {e}")

                st.markdown(f"**Detailed Description**")
                with st.spinner("Loading details..."):
                    try:
                        desc = call_mcp_tool("describe_database_table", {"table_name": selected_table})
                        st.code(desc, language="text")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # Full schema dump
        with st.expander("📄 View Full Database Schema"):
            if st.button("Generate Full Schema", key="full_schema_btn"):
                with st.spinner("Fetching complete schema..."):
                    try:
                        full_schema = call_mcp_tool("get_database_schema", {"table_names": ""})
                        st.code(full_schema, language="sql")
                    except Exception as e:
                        st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════
# TAB 3: SQL Workbench
# ═══════════════════════════════════════════════════════════════════

with tab_query:
    st.markdown("##### 🔍 SQL Workbench")
    st.caption("Run read queries, explain SQL, or preview write operations safely.")

    if not connected:
        st.warning("Connect to MCP server to use the workbench.")
    else:
        subtab_read, subtab_explain, subtab_preview = st.tabs([
            "▶️ Run Query", "📖 Explain SQL", "👁️ Preview Write"
        ])

        with subtab_read:
            st.markdown("Execute **read-only** SELECT queries directly.")
            sql_read = st.text_area(
                "SQL Query:",
                placeholder="SELECT * FROM customers LIMIT 10",
                height=100,
                key="sql_read_input"
            )
            if st.button("▶️ Execute", key="run_read_btn", type="primary"):
                if sql_read.strip():
                    with st.spinner("Executing query..."):
                        try:
                            result = call_mcp_tool("run_read_query", {"sql": sql_read.strip()})
                            st.success("Query executed successfully")
                            st.code(result, language="text")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Enter a SQL query first.")

        with subtab_explain:
            st.markdown("Get a **plain English explanation** of any SQL query.")
            sql_explain = st.text_area(
                "SQL to explain:",
                placeholder="SELECT c.name, COUNT(o.id) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name",
                height=100,
                key="sql_explain_input"
            )
            if st.button("📖 Explain", key="explain_btn", type="primary"):
                if sql_explain.strip():
                    with st.spinner("Analyzing SQL..."):
                        try:
                            explanation = call_mcp_tool("explain_sql", {"sql": sql_explain.strip()})
                            st.info(explanation)
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Enter SQL to explain.")

        with subtab_preview:
            st.markdown("Preview the **impact** of a write operation without executing it.")
            st.caption("⚠️ This does NOT execute the query — it only shows what would be affected.")
            sql_preview = st.text_area(
                "Write SQL to preview:",
                placeholder="UPDATE products SET price = price * 1.1 WHERE category_id = 1",
                height=100,
                key="sql_preview_input"
            )
            if st.button("👁️ Preview Impact", key="preview_btn", type="primary"):
                if sql_preview.strip():
                    with st.spinner("Analyzing impact..."):
                        try:
                            preview = call_mcp_tool("preview_write_operation", {"sql": sql_preview.strip()})
                            st.warning(preview)
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Enter a write SQL statement to preview.")


# ═══════════════════════════════════════════════════════════════════
# TAB 4: Audit Trail
# ═══════════════════════════════════════════════════════════════════

with tab_audit:
    st.markdown("##### 📜 Audit Trail")
    st.caption("Every operation is logged. Review the history of all database interactions.")

    if not connected:
        st.warning("Connect to MCP server to view audit logs.")
    else:
        col1, col2 = st.columns([3, 1])
        with col2:
            limit = st.selectbox("Show last:", [10, 25, 50, 100], key="audit_limit")
        with col1:
            if st.button("🔄 Refresh Audit Logs", key="refresh_audit", type="primary"):
                with st.spinner("Loading audit trail..."):
                    try:
                        logs = call_mcp_tool("get_audit_logs", {"limit": limit})
                        st.session_state["audit_logs"] = logs
                    except Exception as e:
                        st.error(f"Error: {e}")

        if "audit_logs" in st.session_state and st.session_state["audit_logs"]:
            logs = st.session_state["audit_logs"]
            if logs == "No audit logs found":
                st.info("📭 No audit logs yet. Start querying to generate history.")
            else:
                st.code(logs, language="text")
        else:
            st.info("Click 'Refresh Audit Logs' to load the execution history.")


# ═══════════════════════════════════════════════════════════════════
# TAB 5: MCP Tools
# ═══════════════════════════════════════════════════════════════════

with tab_tools:
    st.markdown("##### 🔧 Available MCP Tools")
    st.caption("These are the tools exposed by the SafeSQL-MCP server that power this interface.")

    if not connected:
        st.warning("Connect to MCP server to view tools.")
    else:
        tools = st.session_state.mcp_tools
        if tools:
            for name, desc in tools:
                st.markdown(f"""
<div class="tool-card">
    <div class="tool-name">🔹 {name}</div>
    <div class="tool-desc">{desc}</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.info("No tools discovered.")

        st.markdown("---")
        st.markdown("**Architecture**")
        st.markdown("""
        ```
        ┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
        │  Streamlit UI   │────▶│  FastMCP Server  │────▶│  LangGraph  │
        │  (This App)     │◀────│  (HTTP/SSE)      │◀────│  Agent      │
        └─────────────────┘     └──────────────────┘     └──────┬──────┘
                                                                 │
                                         ┌───────────────────────┼───────────────────────┐
                                         ▼                       ▼                       ▼
                                  ┌─────────────┐       ┌──────────────┐       ┌──────────────┐
                                  │  Northwind  │       │  Audit DB    │       │  Ollama LLM  │
                                  │  Database   │       │  (SQLite)    │       │  (Local)     │
                                  └─────────────┘       └──────────────┘       └──────────────┘
        ```
        """)


# ─────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer-bar">
    🛡️ SafeSQL-MCP v1.0 &nbsp;•&nbsp; LangGraph + Ollama + FastMCP &nbsp;•&nbsp;
    Human-in-the-loop approval for write operations &nbsp;•&nbsp;
    All operations are audited
</div>
""", unsafe_allow_html=True)
