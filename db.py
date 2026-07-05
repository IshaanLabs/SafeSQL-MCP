import sqlite3
from langchain_community.utilities import SQLDatabase
from config import NORTHWIND_DB_URI, AUDIT_DB_PATH
from logger.custom_logger import get_logger

logger = get_logger("db")

# --- Northwind (read/write via LangChain) ---
def get_northwind_db() -> SQLDatabase:
    logger.info("Connecting to Northwind database")
    return SQLDatabase.from_uri(NORTHWIND_DB_URI)

# --- Audit DB (raw sqlite3) ---
def get_audit_connection() -> sqlite3.Connection:
    logger.info("Connecting to Audit database")
    conn = sqlite3.connect(AUDIT_DB_PATH)
    return conn

def setup_audit_db():
    logger.info("Setting up audit database schema")
    conn = get_audit_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_question   TEXT,
            generated_sql   TEXT,
            operation_type  TEXT,
            risk_level      TEXT,
            approved_by     TEXT,
            approval_token  TEXT,
            rows_affected   INTEGER,
            execution_time_ms INTEGER,
            status          TEXT,
            error_message   TEXT,
            timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Audit database ready")
