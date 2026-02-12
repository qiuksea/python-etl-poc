"""Aggregator API to fetch user posts and comments."""

from typing import List

import requests
from fastapi import FastAPI, HTTPException, Path
import uvicorn
from pydantic import TypeAdapter

from shared import Post, Comment, UserPostsResponse, get_logger

BASE_URL = "https://jsonplaceholder.typicode.com"
logger = get_logger("t3_aggregator")

app = FastAPI(
    title="User Posts Aggregator API",
    description="Aggregates posts with comments for a user",
    version="1.0.0",
)

def fetch_user_posts(user_id: int) -> List[dict] | None:
    """Fetch all posts for a given user."""
    try:
        url = f"{BASE_URL}/posts?userId={user_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        posts = response.json()

    except requests.exceptions.HTTPError as http_err:
        logger.exception(
            "HTTP error (status %s)", http_err.response.status_code
            if http_err.response else 500)
        return None

    except requests.exceptions.RequestException:
        logger.exception("Error fetching posts for user %s", user_id)
        return None
    else:
        logger.info("Fetched %s posts for user %s", len(posts), user_id)
        return posts

def fetch_post_comments(post_id: int) -> List[dict] | None:
    """Fetch all comments for a given post."""
    try:
        url = f"{BASE_URL}/comments?postId={post_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        comments = response.json()

    except requests.exceptions.HTTPError as http_err:
        logger.exception(
            "HTTP error (status %s)", http_err.response.status_code if http_err.response else 500)
        return None
    except requests.exceptions.RequestException:
        logger.exception("Error fetching comments for post %s", post_id)
        return None
    else:
        logger.info("Fetched %s comments for post %s", len(comments), post_id)
        return comments


def aggregate_user_data(user_id: int) -> UserPostsResponse | None:
    """Aggregate posts and comments for a user by user id."""
    posts_data = fetch_user_posts(user_id)
    if posts_data is None:
        return None

    if not posts_data:
        logger.info("No posts found for user %s", user_id)
        return UserPostsResponse(user_id=user_id, posts=[])

    posts = []
    # Using TypeAdapter to validate and parse comments and posts data
    comment_adapter = TypeAdapter(List[Comment])
    post_adapter = TypeAdapter(Post)

    for post_data in posts_data:
        comments_data = fetch_post_comments(post_data["id"]) or []

        comments = comment_adapter.validate_python(comments_data)

        post_with_comments = {**post_data, "comments": comments}
        post = post_adapter.validate_python(post_with_comments)

        posts.append(post)

    logger.info(
        "Successfully aggregated %s posts for user %s", len(posts), user_id)

    return UserPostsResponse(user_id=user_id, posts=posts)


@app.get("/users/{user_id}/posts", response_model=UserPostsResponse)
def get_user_posts(user_id: int= Path(..., gt=0)) -> UserPostsResponse:
    """Get aggregated posts and comments for a user by user id."""
    try:
        user_posts = aggregate_user_data(user_id)

        if user_posts is None:
            logger.error("Failed to fetch data for user %s from external API", user_id)
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch data from external API"
            )
        num_posts = len(getattr(user_posts, "posts", []))

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected error for user %s", user_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) from exc
    else:
        logger.info("Successfully aggregated data for user %s with %s posts", user_id, num_posts)
        return user_posts


if __name__ == "__main__":
    print("Starting User Posts Aggregator API.")
    uvicorn.run(app, host="0.0.0.0", port=8001)
