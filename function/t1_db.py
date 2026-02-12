""""Database initialization script for user data storage."""

import sqlite3
from shared import get_db_connection

def init_db() -> None:
    """Initialize the database and create users table if it doesn't exist."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    firstname TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                )
            """)
            print("Database initialized successfully")

    except sqlite3.Error as error:
        print(f"Error initializing database: {error}")
        raise

if __name__ == "__main__":
    init_db()
