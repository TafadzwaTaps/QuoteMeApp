from pydantic import BaseModel
from typing import Optional

# Admin login
class AdminLogin(BaseModel):
    username: str
    password: str

# Quote
class QuoteSchema(BaseModel):
    text: str

# Story
class StorySchema(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None

# Blog
class BlogSchema(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None

class ForumPostSchema(BaseModel):
    name: str
    message: str

    class Config:
        orm_mode = True

class ContactSchema(BaseModel):
    name: str
    email: str
    message: str

    class Config:
        orm_mode = True
    
