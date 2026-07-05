import sqlparse
from config import RISK_LEVELS
from logger import get_logger

logger = get_logger("validate")

BLOCKED_KEYWORDS = {"TRUNCATE", "DROP"}


def validate_node(state: dict) -> dict:
    sql = state.get("generated_sql", "")
    logger.info(f"Validating SQL: {sql}")

    if not sql:
        logger.error("No SQL to validate")
        return {"error_message": "No SQL generated", "validated_sql": None}

    # Parse and check syntax
    parsed = sqlparse.parse(sql)
    if not parsed:
        logger.error("SQL parsing failed")
        return {"error_message": "Invalid SQL syntax", "validated_sql": None}

    # Extract the statement type
    first_token = sql.strip().split()[0].upper() if sql.strip() else ""

    # Block dangerous operations
    if first_token in BLOCKED_KEYWORDS:
        logger.warning(f"BLOCKED operation detected: {first_token}")
        return {
            "validated_sql": None,
            "operation_type": first_token,
            "risk_level": "BLOCKED",
            "error_message": f"{first_token} operations are blocked"
        }

    logger.info("SQL validation passed")
    return {"validated_sql": sql}
