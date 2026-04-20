# QuoteMeApp 🚀

QuoteMeApp is a full-stack quote generator and management system built with FastAPI and a modern web frontend.

## ✨ Features
- Random inspirational quote generator
- Save favorite quotes
- Copy & share functionality
- Admin quote management system
- REST API backend

## 🛠 Tech Stack
- FastAPI (Python)
- SQLite
- HTML, CSS, JavaScript
- Bootstrap (recommended upgrade)

## 📡 API Endpoints
- GET /api/quotes/random
- GET /api/quotes
- POST /api/quotes
- POST /api/favorites

## 🚀 Future Improvements
- AI-generated quotes
- User authentication (JWT)
- Cloud database migration
- Mobile responsive redesign
- Daily quote notifications

## 📦 Setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload
