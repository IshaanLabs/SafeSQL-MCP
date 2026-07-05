from db import get_northwind_db
from logger import get_logger

logger = get_logger("tools.schema")


def list_tables() -> list:
    """Get all table names from the database."""
    db = get_northwind_db()
    tables = db.get_usable_table_names()
    logger.info(f"Listed tables: {tables}")
    return tables


def get_schema(table_names: str = None) -> str:
    """Get schema for specified tables. If None, returns all."""
    db = get_northwind_db()
    if table_names:
        tables = [t.strip() for t in table_names.split(",")]
        schema = db.get_table_info(tables)
    else:
        schema = db.get_table_info()
    logger.info(f"Retrieved schema for: {table_names or 'all tables'}")
    return schema


def describe_table(table_name: str) -> str:
    """Get detailed info for a single table."""
    db = get_northwind_db()
    schema = db.get_table_info([table_name])
    logger.info(f"Described table: {table_name}")
    return schema
