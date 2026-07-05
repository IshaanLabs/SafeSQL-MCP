import time
import re
from db import get_northwind_db
from nodes.approval import check_approval_expiry
from config import DRY_RUN_ENABLED
from logger import get_logger

logger = get_logger("execute")


def _build_dry_run_query(sql: str) -> str:
    """Convert a write query into a SELECT COUNT(*) to preview impact."""
    sql_upper = sql.strip().upper()

    if sql_upper.startswith("UPDATE") or sql_upper.startswith("DELETE"):
        # Extract the table and WHERE clause
        match = re.search(r"(?:UPDATE|DELETE\s+FROM)\s+(\w+)(.*?)(WHERE.+)?$", sql, re.IGNORECASE | re.DOTALL)
        if match:
            table = match.group(1)
            where = match.group(3) or ""
            return f"SELECT COUNT(*) FROM {table} {where}".strip()

    return None


def execute_node(state: dict) -> dict:
    sql = state.get("validated_sql", "")
    risk_level = state.get("risk_level", "SAFE")
    approval_status = state.get("approval_status")

    if not sql:
        return {"error_message": "No SQL to execute"}

    # Check approval expiry for write operations
    if risk_level not in ("SAFE", "LOW") and approval_status == "APPROVED":
        if check_approval_expiry(state):
            return {"error_message": "Approval expired", "approval_status": "EXPIRED"}

    db = get_northwind_db()

    # Dry run for write operations
    if DRY_RUN_ENABLED and risk_level not in ("SAFE",):
        dry_query = _build_dry_run_query(sql)
        if dry_query:
            try:
                count_result = db.run(dry_query)
                logger.info(f"Dry run result: {count_result} rows affected")
                state_update = {"dry_run_count": int(re.search(r"\d+", str(count_result)).group())}
                # If approval not yet given, return with dry run count only
                if approval_status != "APPROVED" and risk_level not in ("LOW",):
                    return state_update
            except Exception as e:
                logger.warning(f"Dry run failed: {e}")

    # Execute the actual query
    logger.info(f"Executing SQL: {sql}")
    start_time = time.time()

    try:
        result = db.run(sql)
        execution_time = int((time.time() - start_time) * 1000)

        # Try to get rows affected
        rows = None
        if result:
            match = re.search(r"\d+", str(result))
            rows = int(match.group()) if match else None

        logger.info(f"Execution complete in {execution_time}ms")
        return {
            "query_result": str(result),
            "rows_affected": rows,
            "execution_time_ms": execution_time,
            "error_message": None
        }

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return {"error_message": str(e), "query_result": None}
