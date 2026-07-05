import sqlite3
from config import NORTHWIND_DB_PATH
from logger import get_logger

logger = get_logger("tools.rollback")


def rollback_transaction(connection: sqlite3.Connection = None) -> dict:
    """Rollback the current transaction on the given connection."""
    if connection is None:
        logger.warning("No connection provided for rollback")
        return {"success": False, "error": "No active connection to rollback"}

    try:
        connection.rollback()
        logger.info("Transaction rolled back successfully")
        return {"success": True, "message": "Transaction rolled back"}
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return {"success": False, "error": str(e)}


def execute_with_rollback(sql: str) -> dict:
    """Execute SQL with manual transaction control - rollback on failure."""
    conn = sqlite3.connect(NORTHWIND_DB_PATH)
    try:
        conn.execute("BEGIN")
        cursor = conn.execute(sql)
        rows_affected = cursor.rowcount
        conn.commit()
        logger.info(f"Executed with rollback safety: {sql[:60]} | Rows: {rows_affected}")
        return {"success": True, "rows_affected": rows_affected}
    except Exception as e:
        conn.rollback()
        logger.error(f"Execution failed, rolled back: {e}")
        return {"success": False, "error": str(e), "rolled_back": True}
    finally:
        conn.close()
