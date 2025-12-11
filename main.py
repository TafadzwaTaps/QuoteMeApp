from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from models import Base, Admin, Quote, Story, Blog
from schemas import AdminLogin, QuoteSchema, StorySchema, BlogSchema
from passlib.hash import bcrypt
import logging_setup
import jwt
import shutil, os
from typing import List

logger = logging_setup.logger

# ===== CONFIG =====
SECRET_KEY = "supersecretkey"  # replace in production
DATABASE_URL = "sqlite:///./database.db"
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
app = FastAPI(title="QuoteMe Admin Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
        logger.warning("Unauthorized access attempt detected: Invalid or missing token")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return username


@app.post("/admin/login")
def login(admin: AdminLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(Admin).filter(Admin.username == admin.username).first()
        if user and bcrypt.verify(admin.password, user.password_hash):
            token = jwt.encode({"username": user.username}, SECRET_KEY, algorithm="HS256")
            logger.info(f"Admin {admin.username} logged in successfully.")
            return {"token": token}
        logger.warning(f"Failed login attempt for admin {admin.username}.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ===== QUOTES =====
@app.get("/quotes", response_model=List[QuoteSchema])
def get_quotes(db: Session = Depends(get_db)):
    return db.query(Quote).order_by(Quote.created_at.desc()).all()

@app.post("/quotes")
def add_quote(quote: QuoteSchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    try:
        new_quote = Quote(text=quote.text)
        db.add(new_quote)
        db.commit()
        db.refresh(new_quote)
        logger.info(f"Quote added by admin: {username}")
        return {"success": True, "quote": new_quote}
    except Exception as e:
        logger.error(f"Error adding quote: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.put("/quotes/{quote_id}")
def edit_quote(quote_id: int, quote: QuoteSchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    q.text = quote.text
    db.commit()
    db.refresh(q)
    return {"success": True, "quote": q}

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
    try:
        s = db.query(Story).filter(Story.id == story_id).first()
        if not s:
            logger.warning(f"Admin {username} attempted to delete non-existent story ID {story_id}")
            raise HTTPException(status_code=404, detail="Story not found")
        db.delete(s)
        db.commit()
        logger.info(f"Story ID {story_id} deleted by admin {username}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting story ID {story_id} by admin {username}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


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

