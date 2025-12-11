from pydantic import BaseModel

class StorySchema(BaseModel):
    title: str
    content: str
    image_url: str = None  # Optional image URL

class BlogSchema(BaseModel):
    title: str
    content: str
    image_url: str = None  # Optional image URL
