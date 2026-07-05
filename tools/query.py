from langchain_ollama import ChatOllama
from db import get_northwind_db
from config import OLLAMA_BASE_URL, MODEL_NAME
from logger import get_logger

logger = get_logger("tools.query")

llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=MODEL_NAME)


def query_database(sql: str) -> str:
    """Execute a read-only SQL query and return results."""
    db = get_northwind_db()
    sql_upper = sql.strip().upper()

    if not sql_upper.startswith("SELECT"):
        logger.warning(f"query_database called with non-SELECT: {sql}")
        return "Error: query_database only supports SELECT statements"

    try:
        result = db.run(sql)
        logger.info(f"Query executed: {sql[:80]}")
        return str(result)
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return f"Error: {str(e)}"


def explain_query(sql: str) -> str:
    """Explain what a SQL query does in plain English."""
    prompt = f"""Explain this SQL query in simple, plain English. Be concise.

SQL: {sql}

Explanation:"""

    response = llm.invoke(prompt)
    explanation = response.content.strip()
    logger.info(f"Explained query: {sql[:50]}")
    return explanation
