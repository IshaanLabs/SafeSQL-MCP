import time
from config import APPROVAL_EXPIRY_SECONDS
from logger import get_logger

logger = get_logger("tools.approval")


def approve_operation(approval_token: str, approved_by: str = "user") -> dict:
    """Approve a pending operation."""
    logger.info(f"Operation approved by {approved_by}, token: {approval_token}")
    return {
        "approved": True,
        "approved_by": approved_by,
        "approval_token": approval_token,
        "timestamp": time.time()
    }


def reject_operation(approval_token: str, rejected_by: str = "user", reason: str = "") -> dict:
    """Reject a pending operation."""
    logger.info(f"Operation rejected by {rejected_by}, reason: {reason}")
    return {
        "approved": False,
        "rejected_by": rejected_by,
        "reason": reason,
        "approval_token": approval_token
    }


def is_approval_expired(approval_timestamp: float) -> bool:
    """Check if an approval has expired."""
    elapsed = time.time() - approval_timestamp
    expired = elapsed > APPROVAL_EXPIRY_SECONDS
    if expired:
        logger.warning(f"Approval expired after {elapsed:.0f}s (limit: {APPROVAL_EXPIRY_SECONDS}s)")
    return expired
