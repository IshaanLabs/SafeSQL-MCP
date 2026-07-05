import time
import uuid
from langgraph.types import interrupt
from config import APPROVAL_EXPIRY_SECONDS
from logger import get_logger

logger = get_logger("approval")


def approval_node(state: dict) -> dict:
    sql = state.get("validated_sql", "")
    risk_level = state.get("risk_level", "")
    dry_run_count = state.get("dry_run_count")

    logger.info(f"Requesting approval for {risk_level} risk operation")

    approval_request = {
        "sql": sql,
        "risk_level": risk_level,
        "rows_affected": dry_run_count,
        "message": f"Approve this {risk_level} risk operation?"
    }

    # LangGraph interrupt - pauses execution, waits for human
    response = interrupt(approval_request)

    # Response comes back after human resumes
    approved = response.get("approved", False)
    approved_by = response.get("approved_by", "unknown")

    if not approved:
        logger.info(f"Operation rejected by {approved_by}")
        return {"approval_status": "REJECTED", "approved_by": approved_by}

    token = str(uuid.uuid4())
    logger.info(f"Operation approved by {approved_by}, token: {token}")

    return {
        "approval_status": "APPROVED",
        "approved_by": approved_by,
        "approval_token": token,
        "approval_timestamp": time.time()
    }


def check_approval_expiry(state: dict) -> bool:
    timestamp = state.get("approval_timestamp")
    if not timestamp:
        return False
    elapsed = time.time() - timestamp
    if elapsed > APPROVAL_EXPIRY_SECONDS:
        logger.warning(f"Approval expired after {elapsed:.0f}s")
        return True
    return False
