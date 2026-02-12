"""Pydantic models for data validation."""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List


class User(BaseModel):
    """User model with common fields."""
    id: int  = Field(..., gt=0, description="User ID must be greater than 0")
    username: str 
    firstname: str
    surname: str
    email: EmailStr
    
    @field_validator('username', 'firstname', 'surname')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove whitespace from string fields."""
        return v.strip()
    
class Comment(BaseModel):
    """Comment model from API."""    
    id: int
    postId: int
    name: str
    email: EmailStr
    body: str

class Post(BaseModel):
    """Post model with nested comments."""    
    id: int
    userId: int
    title: str
    body: str
    comments: List[Comment] = Field(default_factory=list)


class UserPostsResponse(BaseModel):
    """Aggregated response for user's posts and comments."""    
    user_id: int
    posts: List[Post]
    


