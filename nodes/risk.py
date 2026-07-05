from config import RISK_LEVELS
from logger import get_logger

logger = get_logger("risk")


def risk_node(state: dict) -> dict:
    sql = state.get("validated_sql", "")
    operation_type = state.get("operation_type", "")

    if not sql:
        return state

    # Determine operation from SQL if not already classified
    if not operation_type:
        first_token = sql.strip().split()[0].upper()
        operation_type = first_token

    risk_level = RISK_LEVELS.get(operation_type, "HIGH")

    logger.info(f"Operation: {operation_type} | Risk: {risk_level}")
    return {"operation_type": operation_type, "risk_level": risk_level}
