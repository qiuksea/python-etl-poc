"""Simple queue for user creation events."""

from pathlib import Path
from .logger import get_logger

QUEUE_DIR = Path("queue")
QUEUE_FILE = QUEUE_DIR / "user_queue.txt"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger("event_queue")

# task 2 
def enqueue_user(user_id: int) -> None:
    """Add a user ID to the queue for processing."""
    try:
        with open(QUEUE_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{user_id}\n")
            logger.info(f"Enqueued user {user_id}")
    except Exception:
        logger.exception(f"Error enqueuing user {user_id}")

# task 4
def dequeue_user() -> int | None:
    """Get user ID from queue file."""
    if not QUEUE_FILE.exists():
            return None    
    try:   
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            return None
        
        user_id = int(lines[0].strip())
        
        tmp_file = QUEUE_FILE.with_suffix(".tmp")
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.writelines(lines[1:])        
        tmp_file.replace(QUEUE_FILE)
        
        return user_id
        
    except (ValueError):
        logger.exception("Invalid user ID in queue")
        return None
    except Exception:
        logger.exception("Error dequeuing user")
        return None