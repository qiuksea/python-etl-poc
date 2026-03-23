# Data Integration Pipeline - Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Setup & Installation](#setup--installation)
5. [Usage](#usage)
6. [API Reference](#api-reference)
7. [Data Models](#data-models)
8. [Error Handling & Logging](#error-handling--logging)
9. [Directory Structure](#directory-structure)

---

## Overview

A complete event-driven data integration pipeline that demonstrates ETL processes, REST API integration, and asynchronous event processing. The system fetches user data from JSONPlaceholder API, transforms it, stores it in SQLite, and provides aggregated user posts and comments through a REST API.

### Key Features
- **ETL Pipeline**: Automated data extraction, transformation, and loading
- **REST API Aggregator**: FastAPI service for fetching aggregated user posts with comments
- **Event-Driven Architecture**: Queue-based processing of user creation events
- **Data Validation**: Pydantic models for robust data validation
- **Logging**: Comprehensive logging system for monitoring and debugging
- **Scheduling**: Support for scheduled ETL jobs

---

## Architecture

```
┌─────────────────┐
│  External API   │
│ (JSONPlaceholder)│
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         v              v
    ┌────────┐    ┌──────────┐
    │ T2 ETL │    │T3 Aggregator│
    │        │    │   API       │
    └───┬────┘    └──────┬──────┘
        │                │
        v                v
    ┌─────────┐    ┌──────────┐
    │SQLite DB│    │ JSON Files│
    └─────────┘    └──────────┘
        │
        v
    ┌─────────┐
    │ Queue   │
    └────┬────┘
         │
         v
    ┌─────────┐
    │T4 Worker│
    └─────────┘
```

### Workflow
1. **Database Initialization** ([t1_db.py](function/t1_db.py)): Creates SQLite database schema
2. **ETL Process** ([t2_etl.py](function/t2_etl.py)):
   - Fetches user data from API
   - Transforms data (splits names, validates)
   - Saves to database
   - Enqueues user IDs for processing
3. **Aggregator API** ([t3_aggregator.py](function/t3_aggregator.py)):
   - Provides REST endpoint for user posts
   - Fetches posts and comments from external API
   - Returns aggregated data
4. **Worker Process** ([t4_worker.py](function/t4_worker.py)):
   - Dequeues user IDs
   - Calls aggregator API
   - Saves aggregated data to JSON files

---

## Components

### 1. Database Initializer ([t1_db.py](function/t1_db.py))

Initializes the SQLite database with the users table schema.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    firstname TEXT NOT NULL,
    surname TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
)
```

**Functions:**
- `init_db()`: Creates database and users table

**Usage:**
```bash
python -m function.t1_db
```

---

### 2. ETL Pipeline ([t2_etl.py](function/t2_etl.py))

Extracts user data from JSONPlaceholder API, transforms it, and loads it into the database.

**Key Functions:**

#### `fetch_all_users() -> List[Dict] | None`
- Fetches all users from `https://jsonplaceholder.typicode.com/users`
- Returns list of user dictionaries or None on error
- Handles HTTP, connection, and timeout errors

#### `transform_user_data(user: Dict) -> User | None`
- Transforms raw API data into validated User model
- Splits full name into firstname and surname
- Removes titles (Mr., Mrs., Ms., Dr.)
- Validates email format using Pydantic

#### `save_users_batch(users_data: List[User]) -> int`
- Batch inserts/updates users in database
- Uses `INSERT OR REPLACE` for idempotency
- Enqueues user IDs for worker processing
- Returns count of successfully saved users

#### `run_etl() -> None`
- Main ETL orchestration function
- Executes fetch → transform → save pipeline

**Usage:**
```bash
# Run once
python -m function.t2_etl

# Run on schedule (every 15 seconds)
python -m function.t2_etl --schedule
```

**Error Handling:**
- HTTP errors (4xx, 5xx status codes)
- Network connection errors
- Request timeouts (10 second timeout)
- Data validation errors
- Database errors

---

### 3. Aggregator API ([t3_aggregator.py](function/t3_aggregator.py))

FastAPI service that aggregates user posts with their comments.

**Endpoints:**

#### `GET /users/{user_id}/posts`
Returns all posts and comments for a specific user.

**Parameters:**
- `user_id` (path parameter): Integer > 0

**Response Model:** `UserPostsResponse`
```json
{
  "user_id": 1,
  "posts": [
    {
      "id": 1,
      "userId": 1,
      "title": "Post title",
      "body": "Post content",
      "comments": [
        {
          "id": 1,
          "postId": 1,
          "name": "Comment title",
          "email": "user@example.com",
          "body": "Comment content"
        }
      ]
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `503`: External API unavailable
- `500`: Internal server error

**Key Functions:**

#### `fetch_user_posts(user_id: int) -> List[dict] | None`
- Fetches posts for a user from JSONPlaceholder
- Endpoint: `GET /posts?userId={user_id}`

#### `fetch_post_comments(post_id: int) -> List[dict] | None`
- Fetches comments for a post
- Endpoint: `GET /comments?postId={post_id}`

#### `aggregate_user_data(user_id: int) -> UserPostsResponse | None`
- Orchestrates fetching posts and comments
- Uses Pydantic TypeAdapter for validation
- Returns aggregated data structure

**Usage:**
```bash
python -m function.t3_aggregator
```

Access API at:
- http://localhost:8001/users/1/posts
- http://localhost:8001/docs (Swagger UI)

---

### 4. Event Worker ([t4_worker.py](function/t4_worker.py))

Event-driven worker that processes user creation events from the queue.

**Key Functions:**

#### `fetch_user_posts(user_id: int) -> dict | None`
- Calls local aggregator API at `http://localhost:8001`
- Retrieves aggregated posts and comments

#### `save_to_file(user_id: int, data: dict) -> bool`
- Saves aggregated data to `files/user_{user_id}_posts.json`
- Uses UTF-8 encoding with indentation for readability

#### `process_user_event(user_id: int) -> None`
- Main event processing function
- Fetches posts from aggregator
- Saves to JSON file

#### `main() -> None`
- Continuous polling loop
- Dequeues user IDs and processes them
- Sleeps 1 second when queue is empty

**Usage:**
```bash
python -m function.t4_worker
```

**Output:**
- JSON files saved to [files/](files/) directory
- Format: `user_{user_id}_posts.json`

---

## Shared Modules

### Models ([shared/models.py](shared/models.py))

Pydantic models for data validation.

#### `User`
```python
class User(BaseModel):
    id: int                # Must be > 0
    username: str          # Auto-stripped
    firstname: str         # Auto-stripped
    surname: str           # Auto-stripped
    email: EmailStr        # Validated email format
```

#### `Comment`
```python
class Comment(BaseModel):
    id: int
    postId: int
    name: str
    email: EmailStr
    body: str
```

#### `Post`
```python
class Post(BaseModel):
    id: int
    userId: int
    title: str
    body: str
    comments: List[Comment]  # Default: empty list
```

#### `UserPostsResponse`
```python
class UserPostsResponse(BaseModel):
    user_id: int
    posts: List[Post]
```

### Database ([shared/database.py](shared/database.py))

#### `get_db_connection() -> Generator[sqlite3.Connection, None, None]`
Context manager for database connections.

**Features:**
- Automatic connection management
- Auto-commit on success
- Auto-rollback on error
- Row factory enabled for dict-like access

**Usage:**
```python
from shared import get_db_connection

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
```

### Event Queue ([shared/event_queue.py](shared/event_queue.py))

File-based queue for user creation events.

#### `enqueue_user(user_id: int) -> None`
- Appends user ID to [queue/user_queue.txt](queue/user_queue.txt)
- Called by ETL process after saving users

#### `dequeue_user() -> int | None`
- Reads first line from queue file
- Removes processed entry atomically using temporary file
- Returns user ID or None if queue is empty

**Queue File Format:**
```
1
2
3
```

### Logger ([shared/logger.py](shared/logger.py))

#### `get_logger(task_name: str) -> logging.Logger`
Creates a logger that writes to both console and file.

**Features:**
- Console and file output
- Task-specific log files in [logs/](logs/) directory
- ISO format timestamps
- INFO level by default

**Log Files:**
- `logs/t2_etl.log`
- `logs/t3_aggregator.log`
- `logs/t4_worker.log`
- `logs/event_queue.log`

**Format:**
```
2026-02-15 10:30:45 - INFO - ETL job started
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### Installation Steps

1. **Clone the repository**
```bash
cd python_developer_task
```

2. **Create virtual environment**
```bash
python -m venv .venv
```

3. **Activate virtual environment**
```bash
# Windows
.venv\Scripts\activate

# Unix/MacOS
source .venv/bin/activate
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Dependencies
- `requests`: HTTP client for API calls
- `fastapi`: Web framework for REST API
- `uvicorn`: ASGI server for FastAPI
- `pydantic`: Data validation
- `email-validator`: Email validation for Pydantic
- `schedule`: Job scheduling
- `pylint`: Code linting (development)

---

## Usage

### Complete Workflow

Execute in this order:

#### Step 1: Initialize Database
```bash
python -m function.t1_db
```

#### Step 2: Start Aggregator API
```bash
python -m function.t3_aggregator
```
Leave this running in a separate terminal.

#### Step 3: Start Event Worker
```bash
python -m function.t4_worker
```
Leave this running in a separate terminal.

#### Step 4: Run ETL Process
```bash
# One-time run
python -m function.t2_etl

# Scheduled run (every 15 seconds)
python -m function.t2_etl --schedule
```

### Expected Output

1. **ETL logs:** Users fetched, transformed, and saved
2. **Queue:** User IDs added to `queue/user_queue.txt`
3. **Worker logs:** Users dequeued and processed
4. **Files created:** `files/user_1_posts.json`, `files/user_2_posts.json`, etc.
5. **Database:** User records in `db/users.db`

---

## API Reference

### Aggregator API Endpoints

Base URL: `http://localhost:8001`

#### Get User Posts
```http
GET /users/{user_id}/posts
```

**Parameters:**
| Name | Type | Location | Description |
|------|------|----------|-------------|
| user_id | integer | path | User ID (must be > 0) |

**Response 200:**
```json
{
  "user_id": 1,
  "posts": [
    {
      "id": 1,
      "userId": 1,
      "title": "sunt aut facere repellat provident",
      "body": "quia et suscipit\nsuscipit...",
      "comments": [
        {
          "id": 1,
          "postId": 1,
          "name": "id labore ex et quam laborum",
          "email": "Eliseo@gardner.biz",
          "body": "laudantium enim quasi..."
        }
      ]
    }
  ]
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 503 | External API unavailable |
| 500 | Internal server error |

**Interactive Documentation:**
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

---

## Data Models

### User Transformation Logic

#### Name Splitting
The ETL process splits full names into firstname and surname:

**Input:** `"Dr. John Smith"`
**Output:**
- `firstname`: `"John"`
- `surname`: `"Smith"`

**Titles Removed:** Mr., Mrs., Ms., Dr.

**Edge Cases:**
- Single name: `firstname = "John"`, `surname = ""`
- Empty name: `firstname = ""`, `surname = ""`

#### Validation Rules

**User:**
- `id`: Must be greater than 0
- `email`: Must be valid email format
- `username`, `firstname`, `surname`: Automatically stripped of whitespace

**Comment:**
- `email`: Must be valid email format

---

## Error Handling & Logging

### Error Categories

#### Network Errors
- **HTTP errors**: Logged with status codes
- **Connection errors**: Retry not implemented (logged and skipped)
- **Timeouts**: 10-second timeout on all requests

#### Data Validation Errors
- Invalid user data: Logged and skipped (user not saved)
- Missing required fields: Logged and skipped

#### Database Errors
- Connection errors: Logged and raised
- Transaction rollback: Automatic on error

#### File System Errors
- Queue file errors: Logged, returns None
- JSON file write errors: Logged, returns False

### Logging Levels

- **INFO**: Normal operations (fetched N users, saved to file, etc.)
- **WARNING**: Skipped records due to validation
- **ERROR**: Failed operations (API errors, file errors)
- **EXCEPTION**: Unexpected errors with stack traces

### Log File Locations

All logs are stored in [logs/](logs/) directory:
- `t2_etl.log`: ETL process logs
- `t3_aggregator.log`: API request/response logs
- `t4_worker.log`: Worker processing logs
- `event_queue.log`: Queue operations logs

---

## Directory Structure

```
python_developer_task/
├── db/                          # SQLite database storage
│   └── users.db                 # User data database
├── files/                       # Output JSON files
│   └── user_{id}_posts.json     # Aggregated user posts
├── function/                    # Main application modules
│   ├── __init__.py
│   ├── t1_db.py                 # Database initialization
│   ├── t2_etl.py                # ETL pipeline
│   ├── t3_aggregator.py         # REST API aggregator
│   └── t4_worker.py             # Event-driven worker
├── logs/                        # Application logs
│   ├── t2_etl.log
│   ├── t3_aggregator.log
│   ├── t4_worker.log
│   └── event_queue.log
├── queue/                       # Event queue storage
│   └── user_queue.txt           # User IDs to process
├── shared/                      # Shared utilities
│   ├── __init__.py
│   ├── database.py              # Database connection
│   ├── event_queue.py           # Queue operations
│   ├── logger.py                # Logging utilities
│   └── models.py                # Pydantic models
├── .gitignore
├── README.md                    # Quick start guide
├── DOCUMENTATION.md             # This file
└── requirements.txt             # Python dependencies
```

---

## Code Quality

### Linting

Code quality is maintained using Pylint:

```bash
# Lint specific file
pylint function/t2_etl.py

# Lint all files
pylint function/*.py shared/*.py
```

### Code Standards
- Type hints on all function signatures
- Docstrings for all public functions
- Error handling for all external operations
- Logging for all significant operations

---

## External APIs

### JSONPlaceholder API

**Base URL:** `https://jsonplaceholder.typicode.com`

**Endpoints Used:**
- `GET /users`: Fetch all users
- `GET /posts?userId={id}`: Fetch posts for user
- `GET /comments?postId={id}`: Fetch comments for post

**Rate Limiting:** None (public testing API)

**Documentation:** https://jsonplaceholder.typicode.com/guide/

---

## Troubleshooting

### Common Issues

#### 1. Worker can't connect to aggregator API
**Error:** `Connection error fetching posts for user X`

**Solution:**
- Ensure aggregator API is running: `python -m function.t3_aggregator`
- Check API is accessible at http://localhost:8001

#### 2. Database locked errors
**Error:** `database is locked`

**Solution:**
- Only one process should write to database at a time
- Don't run multiple ETL instances simultaneously

#### 3. Queue file permission errors
**Solution:**
- Ensure `queue/` directory has write permissions
- Check file is not open in another program

#### 4. Import errors
**Error:** `ModuleNotFoundError: No module named 'shared'`

**Solution:**
- Run commands as modules: `python -m function.t2_etl`
- Don't run files directly: ~~`python function/t2_etl.py`~~

---

## Future Enhancements

Potential improvements:
- Add retry logic for failed API requests
- Implement message queue (RabbitMQ, Redis) instead of file-based queue
- Add authentication to aggregator API
- Implement caching for frequently accessed data
- Add database migrations support
- Add comprehensive test suite
- Add monitoring/metrics (Prometheus, Grafana)
- Containerize with Docker
- Add configuration file support (YAML/JSON)

---

## License

This is a practice project for Python development tasks.

---

## Support

For issues or questions, review the logs in the [logs/](logs/) directory for detailed error information.
