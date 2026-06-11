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


# =========================================
# STORY SUBMISSION & PARTNERSHIP PACKAGES
# =========================================

PACKAGE_CONFIG = {
    "bronze":      {"label": "Bronze",       "amount": 15,  "duration_days": 14, "ig": 0, "fb": 0, "partner_badge": False},
    "silver":      {"label": "Silver",       "amount": 30,  "duration_days": 30, "ig": 1, "fb": 1, "partner_badge": True},
    "gold":        {"label": "Gold",         "amount": 45,  "duration_days": 42, "ig": 3, "fb": 3, "partner_badge": True},
}

PAYMENT_STATUSES = [
    "pending_payment", "paid", "under_review", "approved", "rejected", "published"
]


class StorySubmissionCreate(BaseModel):
    full_name: str
    organization: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    story_title: str
    story_content: str
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    social_links: Optional[str] = None
    notes: Optional[str] = None
    package: str  # bronze | silver | gold


class StorySubmissionOut(BaseModel):
    id: int
    tracking_number: str
    full_name: str
    organization: Optional[str] = None
    email: str
    phone: Optional[str] = None
    story_title: str
    story_content: str
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    social_links: Optional[str] = None
    notes: Optional[str] = None
    package: str
    amount: int = 0
    payment_status: str = "pending_payment"
    paypal_order_id: Optional[str] = None
    paypal_txn_id: Optional[str] = None
    published_story_id: Optional[int] = None
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    duration_days: int = 14
    instagram_promos_total: int = 0
    instagram_promos_done: int = 0
    facebook_promos_total: int = 0
    facebook_promos_done: int = 0
    is_partner_badge: int = 0
    is_active: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class StorySubmissionUpdate(BaseModel):
    payment_status: Optional[str] = None
    paypal_order_id: Optional[str] = None
    paypal_txn_id: Optional[str] = None
    story_title: Optional[str] = None
    story_content: Optional[str] = None
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    notes: Optional[str] = None
    duration_days: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_partner_badge: Optional[int] = None
    is_active: Optional[int] = None
    instagram_promos_done: Optional[int] = None
    facebook_promos_done: Optional[int] = None


# Partners
class PartnerOut(BaseModel):
    id: int
    submission_id: Optional[int] = None
    organization: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    status: str = "active"
    is_featured: int = 0
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        orm_mode = True
