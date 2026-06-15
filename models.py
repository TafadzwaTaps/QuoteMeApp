from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)

class AdminSettings(Base):
    __tablename__ = "admin_settings"
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), unique=True)
    profile_picture = Column(String(300), nullable=True)
    site_title = Column(String(100), default="QuoteMe ZW")
    site_logo = Column(String(300), nullable=True)
    dark_mode = Column(Integer, default=0)

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    author = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    likes = Column(Integer, default=0)

class Story(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(300), nullable=True)
    likes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Blog(Base):
    __tablename__ = "blogs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(300), nullable=True)
    likes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    username = Column(String(100), nullable=False)
    user_id = Column(Integer, nullable=True)          # FK to site_users.id
    item_type = Column(String(20), nullable=False)    # quote / story / blog
    item_id = Column(Integer, nullable=False)
    sentiment = Column(String(20), default="neutral")
    is_hidden = Column(Integer, default=0)            # 0=visible, 1=hidden by admin
    created_at = Column(DateTime, default=datetime.utcnow)

class ForumPost(Base):
    __tablename__ = "forumpost"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, nullable=True)          # FK to site_users.id
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# =========================================
# SITE USER ACCOUNTS (for comments/forum)
# =========================================
class SiteUser(Base):
    __tablename__ = "site_users"
    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(60), unique=True, nullable=False, index=True)
    email         = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role          = Column(String(20), default="user")    # user / moderator / admin
    bio           = Column(String(300), nullable=True)
    avatar_url    = Column(String(400), nullable=True)
    is_banned     = Column(Integer, default=0)   # 1 = banned/suspended
    ban_reason    = Column(String(300), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_seen     = Column(DateTime, default=datetime.utcnow)
