from logger import get_logger

logger = get_logger("error_handler")


def error_handler_node(state: dict) -> dict:
    error = state.get("error_message", "Unknown error occurred")
    sql = state.get("generated_sql", "")
    operation = state.get("operation_type", "")

    logger.error(f"Error in pipeline | Operation: {operation} | SQL: {sql} | Error: {error}")

    return {
        "final_response": f"Something went wrong: {error}",
        "query_result": None,
        "rows_affected": None
    }
