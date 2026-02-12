"""ETL job to fetch user data from API, transform it, and save to db."""

import sqlite3
import argparse
import time
from typing import List, Dict
import schedule
import requests

from pydantic import ValidationError
from shared import get_logger, get_db_connection, User, enqueue_user


API_URL = "https://jsonplaceholder.typicode.com/users"
logger = get_logger("t2_etl")


def fetch_all_users() -> List[Dict] | None:
    """Fetch all users from the API"""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        users = response.json()

    except requests.exceptions.HTTPError as http_err:
        logger.exception("HTTP error (status %s)",
                         http_err.response.status_code if http_err.response else 500)

        return None

    except requests.exceptions.ConnectionError:
        logger.exception("Connection error")
        return None

    except requests.exceptions.Timeout:
        logger.exception("Request timeout")
        return None

    except requests.exceptions.RequestException:
        logger.exception("Unexpected error fetching data")
        return None

    logger.info("fetched %s users from API", len(users))
    return users


def _split_name(full_name: str) -> tuple:
    titles = {"mr.", "mrs.", "ms.", "dr."}
    parts = full_name.split()

    if parts and parts[0] in titles:
        parts = parts[1:]

    if not parts:
        return ("", "")

    firstname = parts[0]
    surname = " ".join(parts[1:]) if len(parts) > 1 else ""

    return (firstname, surname)

def transform_user_data(user: Dict) -> User | None:
    """Transform data by splitting name into firstname and surname"""
    try:
        user_id = user.get("id")
        name = user.get("name", "").strip()
        username = user.get("username", "").strip()
        email = user.get("email", "").strip()

        if not all([user_id, name, username, email]):
            logger.warning("User %s skipped due to missing fields", user_id)
            return None

        firstname, surname = _split_name(name)

        return User(
            id=user_id,
            username=username,
            firstname=firstname,
            surname=surname,
            email=email
        )

    except ValidationError:
        logger.exception("Validation error for user %s", user.get("id"))
        return None

    except (TypeError, ValueError):
        logger.exception("Error transforming user %s", user.get("id"))
        return None


def save_users_batch(users_data: List[User]) ->  int:
    """Save multiple users to database using executemany"""
    if not users_data:
        return 0
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            users_to_insert = [
                (user.id, user.username, user.firstname, user.surname, user.email)
                for user in users_data
            ]

            # Batch insert
            cursor.executemany("""
                INSERT OR REPLACE INTO users (id, username, firstname, surname, email)
                VALUES (?, ?, ?, ?, ?)
            """, users_to_insert)

            conn.commit()
            logger.info("Batch inserted %s users into database", len(users_to_insert))

            # Enqueue users
            for user in users_data:
                enqueue_user(user.id)

            logger.info("Enqueued %s users for processing", len(users_to_insert))
            return len(users_to_insert)

    except sqlite3.DatabaseError:
        logger.exception("Database save failed")
        return 0

def run_etl() -> None:
    """Main ETL process: fetch, transform, and save user data."""
    logger.info("ETL job started")

    users = fetch_all_users()
    if not users:
        logger.error("No data fetched from API")
        return

    transformed_users = []
    for user in users:
        transformed_user = transform_user_data(user)
        if transformed_user:
            transformed_users.append(transformed_user)

    success_count = save_users_batch(transformed_users)
    fail_count = len(users) - success_count
    logger.info("ETL job completed: %s saved, %s failed", success_count, fail_count)

if __name__ == "__main__":
     # Parse commandline arguments
    parser = argparse.ArgumentParser(description="ETL job for user data")
    parser.add_argument(
        "--schedule", # optional
        action="store_true",
        help="Run ETL on a schedule (every 15 seconds)"
    )
    args = parser.parse_args()

    if args.schedule:
        schedule.every(15).seconds.do(run_etl)
        logger.info("ETL Scheduler started, running every 15 seconds")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("ETL Scheduler stopped by user")
    else:
        run_etl() # Run once
