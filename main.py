from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from models import Base, Admin, AdminSettings, Quote, Story, Blog, ForumPost, ContactMessage, Comment
from schemas import (AdminLogin, AdminPasswordUpdate, AdminUsernameUpdate, AdminSettingsUpdate, AdminSettingsOut,
                     QuoteOut, StoryOut, BlogOut, CommentCreate, CommentOut,
                     ForumPostSchema, ContactSchema)
from passlib.hash import bcrypt
import logging_setup
import jwt
import shutil, os, uuid
from typing import List, Optional
from datetime import datetime

logger = logging_setup.logger

# ===== CONFIG =====
SECRET_KEY = "supersecretkey"  # Replace with environment variable in production
DATABASE_URL = "sqlite:///./database.db"
UPLOAD_DIR = "./uploads"
STATIC_DIR = "./static"
FRONTEND_HTML = "index.html"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ===== DATABASE =====
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)

def init_db():
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

    # Ensure likes column exists on quotes, stories, blogs
    for table_name in ("quotes", "stories", "blogs"):
        columns = {col["name"] for col in inspector.get_columns(table_name)}
        if "likes" not in columns:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN likes INTEGER DEFAULT 0"))

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== SENTIMENT ANALYSIS (rule-based) =====
POSITIVE_WORDS = {"love","great","amazing","wonderful","inspiring","beautiful","excellent","fantastic","awesome","good","brilliant","perfect","happy","joy","thank","best","outstanding"}
NEGATIVE_WORDS = {"hate","terrible","awful","bad","horrible","worst","ugly","boring","disappointing","sad","angry","useless","poor","disgusting","failed","wrong"}

def analyze_sentiment(text: str) -> str:
    words = set(text.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"

# ===== FASTAPI APP =====
app = FastAPI(title="QuoteMe App Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ===== STATIC FILES =====
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
def serve_home():
    if os.path.exists(FRONTEND_HTML):
        return FileResponse(FRONTEND_HTML)
    raise HTTPException(status_code=404, detail="Frontend HTML not found")

@app.get("/admin.html")
def admin_page():
    return FileResponse("static/admin.html")

@app.get("/dashboard.html")
def dashboard_page():
    return FileResponse("static/dashboard.html")

# ===== AUTH =====
def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username")
    except:
        return None

def extract_token(authorization: str) -> str:
    if authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]
    return authorization  # fallback: raw token

def require_admin(authorization: str = Header(...)) -> str:
    token = extract_token(authorization)
    username = verify_token(token)
    if not username:
        logger.warning("Unauthorized access attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return username

# ===== ADMIN LOGIN =====
@app.post("/admin/login")
def login(admin: AdminLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(Admin).filter(Admin.username == admin.username).first()
        if not user:
            logger.warning(f"Failed login attempt for admin {admin.username}.")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not bcrypt.verify(admin.password, user.password_hash):
            logger.warning(f"Failed login attempt for admin {admin.username}.")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = jwt.encode({"username": user.username}, SECRET_KEY, algorithm="HS256")
        logger.info(f"Admin '{admin.username}' logged in successfully.")
        return {"token": token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error for admin '{admin.username}': {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ===== ADMIN SETTINGS =====
@app.get("/admin/settings", response_model=AdminSettingsOut)
def get_settings(username: str = Depends(require_admin), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == username).first()
    settings = db.query(AdminSettings).filter(AdminSettings.admin_id == admin.id).first()
    if not settings:
        settings = AdminSettings(admin_id=admin.id, site_title="QuoteMe ZW")
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@app.put("/admin/settings")
def update_settings(data: AdminSettingsUpdate, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == username).first()
    settings = db.query(AdminSettings).filter(AdminSettings.admin_id == admin.id).first()
    if not settings:
        settings = AdminSettings(admin_id=admin.id)
        db.add(settings)
    if data.site_title is not None:
        settings.site_title = data.site_title
    if data.site_logo is not None:
        settings.site_logo = data.site_logo
    if data.dark_mode is not None:
        settings.dark_mode = data.dark_mode
    if data.profile_picture is not None:
        settings.profile_picture = data.profile_picture
    db.commit()
    db.refresh(settings)
    return {"success": True, "settings": settings}

@app.put("/admin/change-password")
def change_password(data: AdminPasswordUpdate, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not bcrypt.verify(data.current_password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    admin.password_hash = bcrypt.hash(data.new_password[:72])
    db.commit()
    logger.info(f"Admin '{username}' changed their password.")
    return {"success": True, "message": "Password updated"}

@app.put("/admin/change-username")
def change_username(data: AdminUsernameUpdate, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    existing = db.query(Admin).filter(Admin.username == data.new_username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    admin = db.query(Admin).filter(Admin.username == username).first()
    admin.username = data.new_username
    db.commit()
    new_token = jwt.encode({"username": data.new_username}, SECRET_KEY, algorithm="HS256")
    logger.info(f"Admin '{username}' changed username to '{data.new_username}'.")
    return {"success": True, "token": new_token}

# ===== IMAGE UPLOAD =====
@app.post("/upload-image")
def upload_image(file: UploadFile = File(...), username: str = Depends(require_admin)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Image uploaded by admin {username}: {file.filename} -> {safe_name}")
        return {"url": f"/uploads/{safe_name}", "original_name": file.filename}
    except Exception as e:
        logger.error(f"Image upload error by admin {username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")

# ===== QUOTES =====
@app.get("/quotes", response_model=List[QuoteOut])
def get_quotes(page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    return db.query(Quote).offset(offset).limit(limit).all()

@app.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: int, db: Session = Depends(get_db)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return q

@app.post("/quotes", response_model=QuoteOut)
def create_quote(data: dict, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    text = data.get("text")
    if not text:
        raise HTTPException(status_code=422, detail="Quote text is required")
    quote = Quote(text=text, author=data.get("author"), image_url=data.get("image_url"))
    db.add(quote)
    db.commit()
    db.refresh(quote)
    logger.info(f"Quote added by admin: {username}")
    return quote

@app.put("/quotes/{quote_id}", response_model=QuoteOut)
def update_quote(quote_id: int, data: dict, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    quote.text = data.get("text", quote.text)
    quote.author = data.get("author", quote.author)
    quote.image_url = data.get("image_url", quote.image_url)
    db.commit()
    db.refresh(quote)
    return quote

@app.delete("/quotes/{quote_id}")
def delete_quote(quote_id: int, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    db.delete(quote)
    db.commit()
    logger.info(f"Quote ID {quote_id} deleted by admin {username}")
    return {"message": "Deleted successfully"}

# ===== STORIES =====
@app.get("/stories", response_model=List[StoryOut])
def get_stories(page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    return db.query(Story).order_by(Story.created_at.desc()).offset(offset).limit(limit).all()

@app.get("/stories/{story_id}", response_model=StoryOut)
def get_story(story_id: int, db: Session = Depends(get_db)):
    s = db.query(Story).filter(Story.id == story_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Story not found")
    return s

@app.post("/stories", response_model=StoryOut)
def create_story(data: dict, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    if not data.get("title") or not data.get("content"):
        raise HTTPException(status_code=422, detail="Title and content are required")
    story = Story(title=data["title"], content=data["content"], image_url=data.get("image_url"))
    db.add(story)
    db.commit()
    db.refresh(story)
    logger.info(f"Story added by admin: {username}")
    return story

@app.put("/stories/{story_id}", response_model=StoryOut)
def update_story(story_id: int, data: dict, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.title = data.get("title", story.title)
    story.content = data.get("content", story.content)
    story.image_url = data.get("image_url", story.image_url)
    db.commit()
    db.refresh(story)
    return story

@app.delete("/stories/{story_id}")
def delete_story(story_id: int, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    db.delete(story)
    db.commit()
    logger.info(f"Story ID {story_id} deleted by admin {username}")
    return {"message": "Deleted successfully"}

# ===== BLOGS =====
@app.get("/blogs", response_model=List[BlogOut])
def get_blogs(page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    return db.query(Blog).order_by(Blog.created_at.desc()).offset(offset).limit(limit).all()

@app.get("/blogs/{blog_id}", response_model=BlogOut)
def get_blog(blog_id: int, db: Session = Depends(get_db)):
    b = db.query(Blog).filter(Blog.id == blog_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Blog not found")
    return b

@app.post("/blogs", response_model=BlogOut)
def create_blog(data: dict, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    if not data.get("title") or not data.get("content"):
        raise HTTPException(status_code=422, detail="Title and content are required")
    blog = Blog(title=data["title"], content=data["content"], image_url=data.get("image_url"))
    db.add(blog)
    db.commit()
    db.refresh(blog)
    logger.info(f"Blog added by admin: {username}")
    return blog

@app.put("/blogs/{blog_id}", response_model=BlogOut)
def update_blog(blog_id: int, data: dict, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    blog.title = data.get("title", blog.title)
    blog.content = data.get("content", blog.content)
    blog.image_url = data.get("image_url", blog.image_url)
    db.commit()
    db.refresh(blog)
    return blog

@app.delete("/blogs/{blog_id}")
def delete_blog(blog_id: int, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    db.delete(blog)
    db.commit()
    logger.info(f"Blog ID {blog_id} deleted by admin {username}")
    return {"message": "Deleted successfully"}

# ===== LIKES =====
@app.post("/like/{item_type}/{item_id}")
def like_item(item_type: str, item_id: int, db: Session = Depends(get_db)):
    model_map = {"quote": Quote, "story": Story, "blog": Blog}
    model = model_map.get(item_type)
    if not model:
        raise HTTPException(status_code=400, detail="Invalid item type")
    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.likes = (item.likes or 0) + 1
    db.commit()
    return {"likes": item.likes}

# ===== COMMENTS =====
@app.get("/comments/{item_type}/{item_id}", response_model=List[CommentOut])
def get_comments(item_type: str, item_id: int, db: Session = Depends(get_db)):
    return db.query(Comment).filter(
        Comment.item_type == item_type,
        Comment.item_id == item_id
    ).order_by(Comment.created_at.desc()).all()

@app.post("/comments", response_model=CommentOut)
def post_comment(data: CommentCreate, db: Session = Depends(get_db)):
    if data.item_type not in ("quote", "story", "blog"):
        raise HTTPException(status_code=400, detail="Invalid item_type")
    sentiment = analyze_sentiment(data.content)
    comment = Comment(
        content=data.content,
        username=data.username,
        item_type=data.item_type,
        item_id=data.item_id,
        sentiment=sentiment
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

@app.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, username: str = Depends(require_admin), db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(comment)
    db.commit()
    logger.info(f"Comment ID {comment_id} deleted by admin {username}")
    return {"message": "Deleted"}

# ===== CHATBOT =====
FAQ = {
    "quote": "We post daily quotes to inspire and motivate. Browse our Quotes section!",
    "story": "Our Stories section features real empowerment stories from women across Zimbabwe.",
    "blog": "Check out our Blog for motivational articles and tips.",
    "contact": "You can reach us via the Contact section on our homepage.",
    "instagram": "Follow us on Instagram @quoteme_zw for daily inspiration!",
    "admin": "Admin login is available at /admin.html for authorized personnel only.",
}

@app.post("/chatbot")
def chatbot(data: dict):
    message = (data.get("message") or "").lower().strip()
    for keyword, response in FAQ.items():
        if keyword in message:
            return {"reply": response}
    # Fallback response
    if any(w in message for w in ["hello", "hi", "hey"]):
        return {"reply": "Hello! 👋 Welcome to QuoteMe ZW! How can I help you today? You can ask me about quotes, stories, blogs, or how to contact us."}
    if any(w in message for w in ["help", "what", "how"]):
        return {"reply": "I can help you find quotes, stories, blogs, or contact info. Just ask! 😊"}
    return {"reply": "Thanks for reaching out! For more help, use our Contact form or follow us @quoteme_zw on Instagram. 💖"}

# ===== FORUM =====
@app.get("/forum/posts", response_model=List[ForumPostSchema])
def get_forum_posts(db: Session = Depends(get_db)):
    return db.query(ForumPost).order_by(ForumPost.created_at.desc()).all()

@app.post("/forum/post")
def post_forum_message(post: ForumPostSchema, db: Session = Depends(get_db)):
    new_post = ForumPost(name=post.name, message=post.message)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return {"success": True, "post": new_post}

# ===== CONTACT =====
@app.post("/contact/send")
def send_contact(message: ContactSchema, db: Session = Depends(get_db)):
    new_msg = ContactMessage(name=message.name, email=message.email, message=message.message)
    db.add(new_msg)
    db.commit()
    return {"success": True}
