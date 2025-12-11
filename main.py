from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
from pydantic import BaseModel
from passlib.hash import bcrypt
import jwt
from typing import List

# ===== CONFIG =====
SECRET_KEY = "supersecretkey"  # Replace with strong secret in production
DATABASE_URL = "sqlite:///./database.db"

# ===== DATABASE SETUP =====
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# ===== MODELS =====
class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(200))

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True)
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Story(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    content = Column(Text)
    image_url = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Blog(Base):
    __tablename__ = "blogs"
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    content = Column(Text)
    image_url = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ===== FASTAPI APP =====
app = FastAPI(title="QuoteMe Admin Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ===== SCHEMAS =====
class AdminLogin(BaseModel):
    username: str
    password: str

class QuoteSchema(BaseModel):
    text: str

# ===== DEPENDENCY =====
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== AUTH =====
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username")
    except:
        return None

def admin_required(token: str = ""):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return username

@app.post("/admin/login")
def login(admin: AdminLogin, db: Session = Depends(get_db)):
    user = db.query(Admin).filter(Admin.username == admin.username).first()
    if user and bcrypt.verify(admin.password, user.password_hash):
        token = jwt.encode({"username": user.username}, SECRET_KEY, algorithm="HS256")
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# ===== QUOTE MANAGEMENT =====
@app.get("/quotes", response_model=List[QuoteSchema])
def get_quotes(db: Session = Depends(get_db)):
    return db.query(Quote).order_by(Quote.created_at.desc()).all()

@app.post("/quotes")
def add_quote(quote: QuoteSchema, db: Session = Depends(get_db), username: str = Depends(admin_required)):
    new_quote = Quote(text=quote.text)
    db.add(new_quote)
    db.commit()
    db.refresh(new_quote)
    return {"success": True, "quote": new_quote}

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
