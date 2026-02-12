"""Event-driven worker to process user creation events."""

import json
import time
from pathlib import Path

import requests

from shared import dequeue_user, get_logger

API_BASE_URL = "http://localhost:8001"
OUTPUT_DIR = Path("files")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger("t4_worker")

def fetch_user_posts(user_id: int) -> dict | None:
    """Call the aggregator API to get user's posts and comments."""
    try:
        url = f"{API_BASE_URL}/users/{user_id}/posts"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.HTTPError as http_err:
        status = http_err.response.status_code if http_err.response else 500
        logger.exception(
            "HTTP error %s fetching posts for user %s", status, user_id
        )
        return None

    except requests.exceptions.ConnectionError:
        logger.exception(
            "Connection error fetching posts for user %s", user_id
        )
        return None

    except requests.exceptions.Timeout:
        logger.exception(
            "Timeout fetching posts for user %s", user_id
        )
        return None

    except requests.exceptions.RequestException:
        logger.exception(
            "Request error fetching posts for user %s", user_id
        )
        return None

    else:
        logger.info("Fetched posts for user %s from aggregator API", user_id)
        return data


def save_to_file(user_id: int, data: dict) -> bool:
    """Save user posts data to JSON file. """
    filename = OUTPUT_DIR / f"user_{user_id}_posts.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info("Saved posts to %s", filename)
        return True

    except (FileNotFoundError, PermissionError):
        logger.exception(
            "File error saving %s for user %s", filename, user_id
        )
        return False

    except OSError:
        logger.exception(
            "Unexpected OS error saving file for user %s", user_id
        )
        return False

def process_user_event(user_id: int) -> None:
    """Process a single user creation event. """
    logger.info("Processing user %s", user_id)

    posts = fetch_user_posts(user_id)
    if not posts:
        logger.error("Failed to fetch posts for user %s", user_id)
        return

    if save_to_file(user_id, posts):
        logger.info("Successfully saved posts for user %s", user_id)
    else:
        logger.error("Failed to save posts for user %s", user_id)


def main() -> None:
    """Processes user from queue."""
    logger.info("Worker started, waiting for user events...")

    try:
        while True:
            user_id = dequeue_user()

            if user_id is not None:
                process_user_event(user_id)
            else:
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Worker stopped by user presse Ctrl+C")

    except Exception as exc:
        logger.exception("Unexpected error in worker")
        raise RuntimeError("Worker failed") from exc


if __name__ == "__main__":
    main()
