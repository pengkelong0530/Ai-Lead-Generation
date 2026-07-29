"""Database layer with auto-detection factory.

Usage:
    from db import get_db
    db = get_db()
    db.connect()
    db.save_company(...)
"""

import os
from typing import Optional

from config import config


def _mysql_available() -> bool:
    """Check if MySQL is accessible."""
    try:
        import mysql.connector  # noqa: F401
    except ImportError:
        return False
    # Basic connectivity check
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=config.mysql.host,
            port=config.mysql.port,
            user=config.mysql.user,
            password=config.mysql.password,
            database=config.mysql.database,
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


def get_db() -> Any:  # noqa: ANN201
    """Factory: returns a database manager instance.

    Resolution order:
      1. DB_TYPE=mysql  -> MySQLManager (raises if unavailable)
      2. DB_TYPE=sqlite -> SQLiteManager
      3. DB_TYPE=auto   -> try MySQL, fall back to SQLite
      4. DB_TYPE unset  -> same as auto

    Returns an object with the standard interface:
      connect(), close(), _get_connection() (context manager),
      create_session(), save_company(), get_company_by_name(),
      update_company_status(), list_companies(), export_to_csv(),
      save_contact(), get_contacts_by_company(),
      save_email_sequence(), update_email_status(), get_email_sequences(),
      save_reasoning_log(), get_reasoning_logs().
    """
    db_type = config.app.db_type

    if db_type == "mysql":
        from db.mysql_manager import MySQLManager
        return MySQLManager()

    if db_type == "sqlite":
        from db.sqlite_manager import SQLiteManager
        return SQLiteManager()

    # auto: try MySQL, fall back to SQLite
    if db_type == "auto":
        if _mysql_available():
            from db.mysql_manager import MySQLManager
            return MySQLManager()
        from db.sqlite_manager import SQLiteManager
        return SQLiteManager()

    from db.sqlite_manager import SQLiteManager
    return SQLiteManager()


# Re-export for backward compatibility
from db.mysql_manager import MySQLManager  # noqa: F401, E402
from db.sqlite_manager import SQLiteManager  # noqa: F401, E402, F811

__all__ = [
    "get_db",
    "MySQLManager",
    "SQLiteManager",
]
