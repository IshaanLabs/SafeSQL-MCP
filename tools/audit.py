from db import get_audit_connection
from logger import get_logger

logger = get_logger("tools.audit")


def log_execution(
    user_question: str,
    generated_sql: str,
    operation_type: str,
    risk_level: str,
    approved_by: str = None,
    approval_token: str = None,
    rows_affected: int = None,
    execution_time_ms: int = None,
    status: str = "SUCCESS",
    error_message: str = None
) -> dict:
    """Log an execution to the audit database."""
    conn = get_audit_connection()
    try:
        conn.execute("""
            INSERT INTO execution_log
            (user_question, generated_sql, operation_type, risk_level,
             approved_by, approval_token, rows_affected, execution_time_ms,
             status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_question, generated_sql, operation_type, risk_level,
            approved_by, approval_token, rows_affected, execution_time_ms,
            status, error_message
        ))
        conn.commit()
        logger.info(f"Audit logged: {operation_type} | {status} | {user_question[:50]}")
        return {"logged": True}
    except Exception as e:
        logger.error(f"Audit logging failed: {e}")
        return {"logged": False, "error": str(e)}
    finally:
        conn.close()


def get_execution_history(limit: int = 10) -> list:
    """Retrieve recent execution logs."""
    conn = get_audit_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM execution_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Retrieved {len(rows)} audit records")
        return rows
    except Exception as e:
        logger.error(f"Failed to retrieve audit history: {e}")
        return []
    finally:
        conn.close()
