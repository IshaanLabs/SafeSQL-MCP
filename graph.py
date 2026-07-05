from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from nodes.classify import classify_node
from nodes.generate_sql import generate_sql_node
from nodes.validate import validate_node
from nodes.risk import risk_node
from nodes.approval import approval_node
from nodes.execute import execute_node
from nodes.summarize import summarize_node
from nodes.error_handler import error_handler_node
from tools.audit import log_execution
from logger import get_logger

logger = get_logger("graph")


# --- Audit Node ---
def audit_node(state: dict) -> dict:
    """Log the execution to audit DB."""
    log_execution(
        user_question=state.get("user_question", ""),
        generated_sql=state.get("validated_sql") or state.get("generated_sql", ""),
        operation_type=state.get("operation_type", ""),
        risk_level=state.get("risk_level", ""),
        approved_by=state.get("approved_by"),
        approval_token=state.get("approval_token"),
        rows_affected=state.get("rows_affected"),
        execution_time_ms=state.get("execution_time_ms"),
        status="ERROR" if state.get("error_message") else "SUCCESS",
        error_message=state.get("error_message")
    )
    return state


# --- Routing Functions ---
def route_after_validate(state: dict) -> str:
    """Route based on validation result."""
    if state.get("error_message") or not state.get("validated_sql"):
        return "error_handler"
    return "risk"


def route_after_risk(state: dict) -> str:
    """Route based on risk level."""
    risk = state.get("risk_level", "")

    if risk == "BLOCKED":
        return "summarize"
    if risk == "SAFE":
        return "execute"
    if risk == "LOW":
        return "execute"
    # MEDIUM, HIGH → need approval
    return "approval"


def route_after_approval(state: dict) -> str:
    """Route based on approval decision."""
    if state.get("approval_status") == "APPROVED":
        return "execute"
    return "summarize"


# --- Build Graph ---
def build_graph():
    logger.info("Building LangGraph agent")

    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("classify", classify_node)
    builder.add_node("generate_sql", generate_sql_node)
    builder.add_node("validate", validate_node)
    builder.add_node("risk", risk_node)
    builder.add_node("approval", approval_node)
    builder.add_node("execute", execute_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("error_handler", error_handler_node)
    builder.add_node("audit", audit_node)

    # Edges
    builder.add_edge(START, "classify")
    builder.add_edge("classify", "generate_sql")
    builder.add_edge("generate_sql", "validate")

    # Conditional: after validate
    builder.add_conditional_edges("validate", route_after_validate, {
        "risk": "risk",
        "error_handler": "error_handler"
    })

    # Conditional: after risk
    builder.add_conditional_edges("risk", route_after_risk, {
        "execute": "execute",
        "approval": "approval",
        "summarize": "summarize"
    })

    # Conditional: after approval
    builder.add_conditional_edges("approval", route_after_approval, {
        "execute": "execute",
        "summarize": "summarize"
    })

    # Linear edges to end
    builder.add_edge("execute", "summarize")
    builder.add_edge("summarize", "audit")
    builder.add_edge("error_handler", "audit")
    builder.add_edge("audit", END)

    # Compile with checkpointer for interrupt/resume support
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    logger.info("Graph compiled successfully")
    return graph


# Singleton graph instance
agent = build_graph()
