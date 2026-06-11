from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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
    dark_mode = Column(Integer, default=0)  # 0=light, 1=dark

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
    item_type = Column(String(20), nullable=False)  # quote / story / blog
    item_id = Column(Integer, nullable=False)
    sentiment = Column(String(20), default="neutral")  # positive / neutral / negative
    created_at = Column(DateTime, default=datetime.utcnow)

class ForumPost(Base):
    __tablename__ = "forumpost"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
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
# STORY SUBMISSION & PARTNERSHIP PACKAGES
# =========================================
class StorySubmission(Base):
    __tablename__ = "story_submissions"
    id = Column(Integer, primary_key=True, index=True)

    # Tracking
    tracking_number = Column(String(40), unique=True, nullable=False, index=True)

    # Submitter info
    full_name     = Column(String(150), nullable=False)
    organization  = Column(String(200), nullable=True)
    email         = Column(String(200), nullable=False)
    phone         = Column(String(40), nullable=True)

    # Story content
    story_title   = Column(String(250), nullable=False)
    story_content = Column(Text, nullable=False)
    image_url     = Column(String(400), nullable=True)
    logo_url      = Column(String(400), nullable=True)
    social_links  = Column(Text, nullable=True)   # JSON-encoded list/dict
    notes         = Column(Text, nullable=True)

    # Package
    package = Column(String(30), nullable=False)  # bronze / silver / gold / partnership
    amount  = Column(Integer, default=0)           # USD, whole dollars

    # Payment
    payment_status = Column(String(30), default="pending_payment")
    # pending_payment | paid | under_review | approved | rejected | published
    paypal_order_id = Column(String(120), nullable=True)
    paypal_txn_id    = Column(String(120), nullable=True)

    # Publication lifecycle
    published_story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)
    published_at  = Column(DateTime, nullable=True)
    expires_at    = Column(DateTime, nullable=True)
    duration_days = Column(Integer, default=14)

    # Promotions
    instagram_promos_total = Column(Integer, default=0)
    instagram_promos_done  = Column(Integer, default=0)
    facebook_promos_total  = Column(Integer, default=0)
    facebook_promos_done   = Column(Integer, default=0)

    is_partner_badge = Column(Integer, default=0)  # 1 = show "Featured Partner" badge
    is_active        = Column(Integer, default=1)  # 0 = expired/removed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Partner(Base):
    __tablename__ = "partners"
    id = Column(Integer, primary_key=True, index=True)
    submission_id   = Column(Integer, ForeignKey("story_submissions.id"), nullable=True)
    organization    = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    logo_url        = Column(String(400), nullable=True)
    website         = Column(String(300), nullable=True)
    status          = Column(String(30), default="active")  # active / expired / paused
    is_featured     = Column(Integer, default=0)
    started_at      = Column(DateTime, default=datetime.utcnow)
    expires_at      = Column(DateTime, nullable=True)
