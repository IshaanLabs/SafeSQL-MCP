import re
from db import get_northwind_db
from logger import get_logger

logger = get_logger("tools.write")


def preview_update(sql: str) -> dict:
    """Dry run a write query - returns row count that would be affected."""
    db = get_northwind_db()
    sql_upper = sql.strip().upper()

    if sql_upper.startswith("SELECT"):
        return {"error": "preview_update is for write operations only"}

    # Build a COUNT query from the write statement
    match = re.search(r"(?:UPDATE|DELETE\s+FROM)\s+(\w+)(.*?)(WHERE.+)?$", sql, re.IGNORECASE | re.DOTALL)
    if not match:
        return {"error": "Could not parse SQL for preview", "sql": sql}

    table = match.group(1)
    where = match.group(3) or ""
    count_sql = f"SELECT COUNT(*) FROM {table} {where}".strip()

    try:
        result = db.run(count_sql)
        count = int(re.search(r"\d+", str(result)).group())
        logger.info(f"Preview: {count} rows would be affected by: {sql[:60]}")
        return {"rows_affected": count, "preview_sql": count_sql, "original_sql": sql}
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        return {"error": str(e)}


def run_sql(sql: str) -> dict:
    """Execute a write SQL statement. Should only be called after approval."""
    db = get_northwind_db()

    try:
        result = db.run(sql)
        logger.info(f"Write executed: {sql[:80]}")
        return {"success": True, "result": str(result)}
    except Exception as e:
        logger.error(f"Write failed: {e}")
        return {"success": False, "error": str(e)}
