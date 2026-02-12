"""Database connection utilities and configuration."""

import sqlite3
from typing import Generator
from contextlib import contextmanager
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_DIR / "db"
DATABASE_PATH = DB_DIR / "users.db"

DB_DIR.mkdir(parents=True, exist_ok=True)

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()        
    except sqlite3.Error as e:
        print(f"Database error: {e}") 
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()