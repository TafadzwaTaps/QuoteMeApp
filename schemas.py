from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Admin login
class AdminLogin(BaseModel):
    username: str
    password: str

class AdminPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class AdminUsernameUpdate(BaseModel):
    new_username: str

class AdminSettingsUpdate(BaseModel):
    site_title: Optional[str] = None
    site_logo: Optional[str] = None
    dark_mode: Optional[int] = None
    profile_picture: Optional[str] = None

class AdminSettingsOut(BaseModel):
    site_title: str
    site_logo: Optional[str] = None
    dark_mode: int
    profile_picture: Optional[str] = None

    class Config:
        orm_mode = True

# Quote
class QuoteSchema(BaseModel):
    text: str
    author: Optional[str] = None
    image_url: Optional[str] = None

class QuoteOut(BaseModel):
    id: int
    text: str
    author: Optional[str] = None
    image_url: Optional[str] = None
    likes: int = 0

    class Config:
        orm_mode = True

# Story
class StorySchema(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None

class StoryOut(BaseModel):
    id: int
    title: str
    content: str
    image_url: Optional[str] = None
    likes: int = 0
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Blog
class BlogSchema(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None

class BlogOut(BaseModel):
    id: int
    title: str
    content: str
    image_url: Optional[str] = None
    likes: int = 0
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Comment
class CommentCreate(BaseModel):
    content: str
    username: str
    item_type: str  # quote / story / blog
    item_id: int

class CommentOut(BaseModel):
    id: int
    content: str
    username: str
    item_type: str
    item_id: int
    sentiment: str
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Forum
class ForumPostSchema(BaseModel):
    name: str
    message: str
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Contact
class ContactSchema(BaseModel):
    name: str
    email: str
    message: str

    class Config:
        orm_mode = True
