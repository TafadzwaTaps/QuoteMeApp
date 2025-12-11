from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from models import Base, Admin, Quote, Story, Blog, ForumPost, ContactMessage
from schemas import AdminLogin, QuoteSchema, StorySchema, BlogSchema, ForumPostSchema, ContactSchema, QuoteOut
from passlib.hash import bcrypt
import logging_setup
import jwt
import shutil, os
from typing import List
from datetime import datetime

logger = logging_setup.logger

# ===== CONFIG =====
SECRET_KEY = "supersecretkey"  # Replace with environment variable in production
DATABASE_URL = "sqlite:///./database.db"
UPLOAD_DIR = "./uploads"
STATIC_DIR = "./static"
FRONTEND_HTML = "index.html"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ===== DATABASE =====
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== FASTAPI APP =====
app = FastAPI(title="QuoteMe App Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ===== STATIC FILES =====
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Serve homepage
@app.get("/")
def serve_home():
    if os.path.exists(FRONTEND_HTML):
        return FileResponse(FRONTEND_HTML)
    else:
        raise HTTPException(status_code=404, detail="Frontend HTML not found")
    
@app.get("/admin.html")
def admin_page():
    return FileResponse("static/admin.html")

@app.get("/dashboard.html")
def dashboard_page():
    return FileResponse("static/dashboard.html")

# ===== AUTH =====
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username")
    except:
        return None

def admin_required(token: str):
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
            # Admin username not found
            logger.warning(f"Failed login attempt for unknown admin '{admin.username}'.")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        if not bcrypt.verify(admin.password, user.password_hash):
            logger.warning(f"Failed login attempt for admin '{admin.username}': Wrong password.")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Successful login
        token = jwt.encode({"username": user.username}, SECRET_KEY, algorithm="HS256")
        logger.info(f"Admin '{admin.username}' logged in successfully.")
        return {"token": token}

    except HTTPException:
        # Re-raise HTTP exceptions without turning them into 500
        raise

    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected login error for admin '{admin.username}': {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ===== QUOTES =====
@app.get("/quotes", response_model=list[QuoteOut])
def get_quotes(db: Session = Depends(get_db)):
    return db.query(Quote).all()


@app.post("/quotes", response_model=QuoteOut)
def add_quote(quote: QuoteSchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    new_quote = Quote(text=quote.text)
    db.add(new_quote)
    db.commit()
    db.refresh(new_quote)
    return new_quote


@app.delete("/quotes/{quote_id}")
def delete_quote(quote_id: int, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    db.delete(q)
    db.commit()
    return {"success": True}

# ===== STORIES =====
@app.get("/stories", response_model=List[StorySchema])
def get_stories(db: Session = Depends(get_db)):
    return db.query(Story).order_by(Story.created_at.desc()).all()

@app.post("/stories")
def add_story(story: StorySchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    new_story = Story(title=story.title, content=story.content, image_url=story.image_url)
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    return {"success": True, "story": new_story}

@app.put("/stories/{story_id}")
def edit_story(story_id: int, story: StorySchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    s = db.query(Story).filter(Story.id == story_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Story not found")
    s.title = story.title
    s.content = story.content
    s.image_url = story.image_url
    db.commit()
    db.refresh(s)
    return {"success": True, "story": s}

@app.delete("/stories/{story_id}")
def delete_story(story_id: int, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    s = db.query(Story).filter(Story.id == story_id).first()
    if not s:
        logger.warning(f"Admin {username} attempted to delete non-existent story ID {story_id}")
        raise HTTPException(status_code=404, detail="Story not found")
    db.delete(s)
    db.commit()
    logger.info(f"Story ID {story_id} deleted by admin {username}")
    return {"success": True}

# ===== BLOGS =====
@app.get("/blogs", response_model=List[BlogSchema])
def get_blogs(db: Session = Depends(get_db)):
    return db.query(Blog).order_by(Blog.created_at.desc()).all()

@app.post("/blogs")
def add_blog(blog: BlogSchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    new_blog = Blog(title=blog.title, content=blog.content, image_url=blog.image_url)
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)
    return {"success": True, "blog": new_blog}

@app.put("/blogs/{blog_id}")
def edit_blog(blog_id: int, blog: BlogSchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    b = db.query(Blog).filter(Blog.id == blog_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Blog not found")
    b.title = blog.title
    b.content = blog.content
    b.image_url = blog.image_url
    db.commit()
    db.refresh(b)
    return {"success": True, "blog": b}

@app.delete("/blogs/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    b = db.query(Blog).filter(Blog.id == blog_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Blog not found")
    db.delete(b)
    db.commit()
    return {"success": True}

# ===== IMAGE UPLOAD =====
@app.post("/upload-image")
def upload_image(file: UploadFile = File(...), username: str = Depends(admin_required)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Image uploaded by admin {username}: {file.filename}")
        return {"url": f"/uploads/{file.filename}"}
    except Exception as e:
        logger.error(f"Image upload error by admin {username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")

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
    db.refresh(new_msg)
    return {"success": True}
