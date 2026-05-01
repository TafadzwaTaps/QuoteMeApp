from datetime import datetime, timedelta
import os
import uuid
import shutil
import mimetypes
import mimetypes
import logging

from fastapi import FastAPI, HTTPException, Depends, Header, File, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer


from supabase import create_client
from jose import jwt
from passlib.context import CryptContext

# =========================
# CONFIG
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
UPLOAD_DIR = "./uploads"
STATIC_DIR = "./static"
FRONTEND_HTML = "index.html"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "!QuoteMe_ZW@2026")
ALGORITHM = "HS256"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Supabase Storage bucket — create in Dashboard: Storage → New bucket → "images" → Public ON
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "images")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# =========================
# APP
# =========================
app = FastAPI(title="QuoteMe Supabase API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def handle_head_requests(request, call_next):
    if request.method == "HEAD":
        response = await call_next(request)
        return Response(
            content=None,
            status_code=response.status_code,
            headers=response.headers,
            media_type=response.media_type,
        )
    return await call_next(request)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/admin")
def admin_page():
    return FileResponse("static/admin.html")

@app.get("/dashboard")
def dashboard_page():
    return FileResponse("static/dashboard.html")

@app.get("/story/{story_id}")
def story_page(story_id: int):
    return FileResponse("static/story.html")

# =========================
# AUTH HELPERS
# =========================
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("username")
    except:
        return None


def require_admin(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("username")

    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"username": username}

# ==============================
# 💬 SENTIMENT
# ==============================
POS = {"love","great","amazing","wonderful","inspiring","beautiful","excellent","fantastic","awesome","good","brilliant","perfect","happy","joy","thank","best","outstanding"}
NEG = {"hate","terrible","awful","bad","horrible","worst","ugly","boring","disappointing","sad","angry","useless","poor","disgusting","failed","wrong"}

def sentiment(text):
    words = set(text.lower().split())
    if len(words & POS) > len(words & NEG):
        return "positive"
    elif len(words & NEG) > len(words & POS):
        return "negative"
    return "neutral"

# =========================
# ADMIN LOGIN
# =========================
@app.post("/admin/login")
def admin_login(data: dict):
    username_input = data.get("username")
    password = data.get("password")

    if not username_input or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")

    username = username_input.strip().lower()

    res = supabase.table("admins")\
        .select("*")\
        .ilike("username", username)\
        .execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = res.data[0]

    if not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode({
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=12)
    }, SECRET_KEY, algorithm=ALGORITHM)

    return {"token": token}

# =========================
# SETTINGS
# =========================



@app.get("/settings")
def settings_alias():
    res = supabase.table("admin_settings").select("*").limit(1).execute()
    return res.data[0] if res.data else {}

@app.get("/admin/settings")
def get_admin_settings(username: str = Depends(require_admin)):
    admin = supabase.table("admins").select("*").eq("username", username).execute().data

    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    admin_id = admin[0]["id"]

    res = supabase.table("admin_settings")\
        .select("*")\
        .eq("admin_id", admin_id)\
        .execute()

    return res.data[0] if res.data else {}    


@app.put("/admin/settings")
def update_settings(data: dict, username: str = Depends(require_admin)):
    # get admin id first
    admin = supabase.table("admins").select("*").eq("username", username).execute().data

    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    admin_id = admin[0]["id"]

    res = supabase.table("admin_settings")\
        .update(data)\
        .eq("admin_id", admin_id)\
        .execute()

    return {"success": True, "data": res.data}


# =========================
# STATS DASHBOARD
# =========================
@app.get("/admin/stats")
def stats(username: str = Depends(require_admin)):
    return {
        "quotes": len(supabase.table("quotes").select("*").execute().data),
        "stories": len(supabase.table("stories").select("*").execute().data),
        "blogs": len(supabase.table("blogs").select("*").execute().data),
        "comments": len(supabase.table("comments").select("*").execute().data),
        "forumpost": len(supabase.table("forumpost").select("*").execute().data),
    }

# =========================
# UPLOAD IMAGE
# =========================
@app.post("/upload-image")
async def upload(
    file: UploadFile = File(...),
    username: str = Depends(require_admin)
):
    """
    Upload image to Supabase Storage (survives Render redeploys).
    Falls back to local disk if Storage bucket not yet configured.

    One-time Supabase setup:
      Dashboard → Storage → New bucket → Name: "images" → Public: ON
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    filename     = f"{uuid.uuid4().hex}{ext}"
    file_bytes   = await file.read()
    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"

    # ── Primary: Supabase Storage (persistent) ──
    try:
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
        logger.info(f"Supabase Storage upload OK: {filename}")
        return {"success": True, "url": public_url}
    except Exception as e:
        logger.warning(f"Supabase Storage upload failed ({e}) — falling back to local disk")

    # ── Fallback: local disk (lost on redeploy, but better than nothing) ──
    path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(path, "wb") as buf:
            buf.write(file_bytes)
        logger.info(f"Local disk upload (fallback): {filename}")
        return {"success": True, "url": f"/uploads/{filename}"}
    except Exception as e:
        logger.error(f"Both upload paths failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


# =========================
# QUOTES
# =========================
@app.get("/quotes")
def get_quotes():
    try:
        res = supabase.table("quotes").select("*").execute()
        return res.data
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/quotes")
def create_quote(data: dict, username: str = Depends(require_admin)):
    res = supabase.table("quotes").insert(data).execute()
    return res.data


@app.put("/quotes/{quote_id}")
def update_quote(quote_id: int, data: dict, username: str = Depends(require_admin)):
    res = supabase.table("quotes").update(data).eq("id", quote_id).execute()
    return res.data


@app.delete("/quotes/{quote_id}")
def delete_quote(quote_id: int, username: str = Depends(require_admin)):
    supabase.table("quotes").delete().eq("id", quote_id).execute()
    return {"message": "Deleted"}


# =========================
# STORIES
# =========================
@app.get("/stories")
def get_stories():
    try:
        return supabase.table("stories").select("*").execute().data
    except Exception as e:
        logger.error(f"get_stories: {e}")
        raise HTTPException(500, str(e))


@app.get("/stories/{story_id}")
def get_story(story_id: int):
    try:
        res = supabase.table("stories").select("*").eq("id", story_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Story not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_story {story_id}: {e}")
        raise HTTPException(500, str(e))


@app.post("/stories")
def create_story(data: dict, username: str = Depends(require_admin)):
    return supabase.table("stories").insert(data).execute().data


# =========================
# BLOGS
# =========================
@app.get("/blogs")
def get_blogs():
    return supabase.table("blogs").select("*").execute().data


@app.post("/blogs")
def create_blog(data: dict, username: str = Depends(require_admin)):
    return supabase.table("blogs").insert(data).execute().data


# =========================
# LIKES
# =========================
# Maps singular item_type → correct Supabase table name
_TYPE_TO_TABLE = {
    "quote":  "quotes",
    "story":  "stories",   # NOT "storys"
    "blog":   "blogs",
}

@app.post("/like/{item_type}/{item_id}")
def like(item_type: str, item_id: int):
    table = _TYPE_TO_TABLE.get(item_type)
    if not table:
        raise HTTPException(status_code=400, detail=f"Invalid item_type '{item_type}'. Must be quote, story, or blog.")
    try:
        rows = supabase.table(table).select("id, likes").eq("id", item_id).execute().data
        if not rows:
            raise HTTPException(status_code=404, detail=f"{item_type.capitalize()} #{item_id} not found")
        current = rows[0].get("likes") or 0
        new_val = current + 1
        supabase.table(table).update({"likes": new_val}).eq("id", item_id).execute()
        logger.info(f"Like: {table} id={item_id} → {new_val}")
        return {"likes": new_val}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"like {item_type}/{item_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not update likes")


# =========================
# COMMENTS
# =========================
@app.get("/comments/{item_type}/{item_id}")
def get_comments(item_type: str, item_id: int):
    return supabase.table("comments")\
        .select("*")\
        .eq("item_type", item_type)\
        .eq("item_id", item_id)\
        .execute().data


# ── SENTIMENT & TOXICITY HELPERS ──
_POS = {"love","great","amazing","wonderful","inspiring","beautiful","excellent",
        "fantastic","awesome","good","brilliant","perfect","happy","joy","thank","best"}
_NEG = {"hate","terrible","awful","bad","horrible","worst","ugly","boring",
        "disappointing","sad","angry","useless","poor","disgusting","failed","wrong"}
_FLAGGED = {"murder","kill","attack","abuse","rape","bomb","terrorist"}
_TOXIC   = {"hate","stupid","idiot","ugly","horrible","disgusting","awful",
            "terrible","worst","dumb","moron","loser","trash"}

def _sentiment(text: str) -> str:
    words = set(text.lower().split())
    pos, neg = len(words & _POS), len(words & _NEG)
    if pos > neg: return "positive"
    if neg > pos: return "negative"
    return "neutral"

def _toxicity(text: str) -> float:
    words = set(text.lower().split())
    f = len(words & _FLAGGED)
    t = len(words & _TOXIC)
    if f > 0: return min(0.70 + f * 0.10, 1.0)
    if t > 0: return min(0.30 + t * 0.10, 0.69)
    return 0.0


@app.post("/comments")
def add_comment(data: dict):
    """
    Safe comment insert.
    Tries to save with `toxicity` first.
    If the column does not exist in Supabase it retries without it.
    Add the column with:  ALTER TABLE comments ADD COLUMN IF NOT EXISTS toxicity float4 DEFAULT 0;
    """
    text      = (data.get("content")   or "").strip()
    username  = (data.get("username")  or "").strip()
    item_type = (data.get("item_type") or "").strip()
    item_id   = data.get("item_id")

    if not text:
        raise HTTPException(status_code=400, detail="Comment content is required")
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not item_type or item_id is None:
        raise HTTPException(status_code=400, detail="item_type and item_id are required")

    payload = {
        "username":  username,
        "content":   text,
        "item_type": item_type,
        "item_id":   int(item_id),
        "sentiment": _sentiment(text),
    }

    # Attempt 1: include toxicity score
    try:
        res = supabase.table("comments").insert({**payload, "toxicity": _toxicity(text)}).execute()
        if res.data:
            logger.info(f"Comment saved (with toxicity) id={res.data[0].get('id')}")
            return res.data
    except Exception as e:
        err = str(e).lower()
        if any(kw in err for kw in ["toxicity", "column", "schema", "undefined", "does not exist", "not found"]):
            logger.warning(f"toxicity column missing, retrying without it ({e})")
        else:
            logger.error(f"add_comment error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save comment: {e}")

    # Attempt 2: without toxicity
    try:
        res = supabase.table("comments").insert(payload).execute()
        if res.data:
            logger.info(f"Comment saved (no toxicity) id={res.data[0].get('id')}")
            return res.data
        raise ValueError("Supabase returned empty data")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"add_comment retry error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save comment: {e}")


@app.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, username: str = Depends(require_admin)):
    """Delete a comment by ID. Requires admin Authorization header."""
    try:
        supabase.table("comments").delete().eq("id", comment_id).execute()
        logger.info(f"Admin '{username}' deleted comment {comment_id}")
        return {"message": "Comment deleted", "id": comment_id}
    except Exception as e:
        logger.error(f"delete_comment {comment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete comment: {e}")


# =========================
# FORUM
# =========================
@app.get("/forum/posts")
def get_posts():
    return supabase.table("forumpost").select("*").execute().data


@app.post("/forum/post")
def create_post(data: dict):
    return supabase.table("forumpost").insert(data).execute().data


# =========================
# CONTACT
# =========================
@app.post("/contact/send")
def contact(data: dict):
    """Public contact form — no auth required."""
    try:
        return supabase.table("contactmessage").insert(data).execute().data
    except Exception as e:
        logger.error(f"contact/send: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# CHATBOT
# =========================
@app.post("/chatbot")
def chatbot(data: dict):
    """
    Enhanced chatbot with 20+ command categories.
    All keyword matching is case-insensitive.
    """
    raw = (data.get("message") or "").strip()
    msg = raw.lower()

    if not msg:
        return {"reply": "Please type a message 😊 Try saying 'help' to see what I can do!"}

    # ── helpers ──
    def _quotes(limit=3):
        try:
            return supabase.table("quotes").select("*").limit(limit).execute().data or []
        except Exception:
            return []

    def _stories(limit=2):
        try:
            return supabase.table("stories").select("*").limit(limit).execute().data or []
        except Exception:
            return []

    def _blogs(limit=2):
        try:
            return supabase.table("blogs").select("*").limit(limit).execute().data or []
        except Exception:
            return []

    # =========================
    # GREETINGS
    # =========================
    if any(w in msg for w in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings", "sup", "hola"]):
        import random
        greets = [
            "Hey there 👋 Welcome to QuoteMe ZW 💖 I'm here to inspire you! Ask me about quotes, stories, blogs, or anything else.",
            "Hello beautiful soul! 🌸 How can I inspire you today?",
            "Hey hey! 💖 Welcome to QuoteMe ZW — Zimbabwe's home of daily inspiration. What can I help you with?",
            "Hi there! 👋 Ready to get inspired? Ask me about quotes, stories, or our community forum!",
        ]
        return {"reply": random.choice(greets)}

    # =========================
    # GOODBYE
    # =========================
    if any(w in msg for w in ["bye", "goodbye", "see you", "later", "ciao", "take care"]):
        return {"reply": "Goodbye! 👋 Stay inspired and keep shining! 💖 Come back anytime — QuoteMe ZW is always here for you. ✨"}

    # =========================
    # THANK YOU
    # =========================
    if any(w in msg for w in ["thank", "thanks", "thank you", "cheers", "appreciate"]):
        return {"reply": "You're so welcome! 🌸 That's what we're here for. Keep spreading that positive energy! 💖"}

    # =========================
    # HOW ARE YOU
    # =========================
    if any(w in msg for w in ["how are you", "how r u", "how are u", "you okay", "you good"]):
        return {"reply": "I'm doing amazing, thank you for asking! 💖 I'm always energised when helping people find inspiration. How are YOU doing today? 😊"}

    # =========================
    # QUOTES
    # =========================
    if any(w in msg for w in ["quote", "quotes", "inspire me", "motivation", "motivate", "inspire", "uplift"]):
        rows = _quotes(3)
        if rows:
            sample = "\n\n".join([f"💬 \"{q['text']}\"\'\n   — {q.get('author','Unknown')}" for q in rows])
            return {"reply": f"Here are some inspiring quotes just for you ✨\n\n{sample}\n\nVisit our Quotes section for more! 💖"}
        return {"reply": "We post daily inspirational quotes! ✨ Check out our Quotes section on the homepage."}

    # =========================
    # RANDOM QUOTE
    # =========================
    if any(w in msg for w in ["random quote", "surprise me", "give me a quote", "quote of the day", "qotd"]):
        import random
        rows = _quotes(10)
        if rows:
            q = random.choice(rows)
            return {"reply": f"Here's one for you today ✨\n\n💬 \"{q['text']}\"\'\n— {q.get('author','QuoteMe ZW')}"}
        local = [
            "She believed she could, so she did. 🌸",
            "Your potential is endless. Keep going! 💪",
            "Queens don't compete — they collaborate. 👑",
            "The most powerful thing you can do is believe in yourself. ✨",
        ]
        import random
        return {"reply": "💬 " + random.choice(local)}

    # =========================
    # STORIES
    # =========================
    if any(w in msg for w in ["story", "stories", "empowerment", "women", "real stories", "success story"]):
        rows = _stories(2)
        if rows:
            sample = "\n\n".join([f"📖 *{s['title']}*\n{s['content'][:100]}..." for s in rows])
            return {"reply": f"Here are some powerful empowerment stories 💖\n\n{sample}\n\nClick \'Read More\' on any story for the full version!"}
        return {"reply": "We share real women empowerment stories! 💖 Check the Stories section on our homepage."}

    # =========================
    # BLOGS
    # =========================
    if any(w in msg for w in ["blog", "blogs", "article", "read", "post", "posts"]):
        rows = _blogs(2)
        if rows:
            sample = "\n\n".join([f"📰 *{b['title']}*\n{b['content'][:100]}..." for b in rows])
            return {"reply": f"Here are some of our latest blogs 🚀\n\n{sample}\n\nHead to our Blog section for more!"}
        return {"reply": "Check our Blog section for motivational articles and tips! 🚀"}

    # =========================
    # FORUM
    # =========================
    if any(w in msg for w in ["forum", "community", "discussion", "chat", "talk", "ask", "question", "connect"]):
        return {
            "reply": (
                "Our Community Forum is the best place to connect! 🗣️\n\n"
                "You can:\n"
                "💬 Share general thoughts\n"
                "📖 Discuss stories\n"
                "❓ Ask questions\n"
                "💡 Leave feedback\n\n"
                "Scroll down to the Forum section to join the conversation!"
            )
        }

    # =========================
    # DONATE / SUPPORT US
    # =========================
    if any(w in msg for w in ["donate", "donation", "support", "contribute", "fund", "help us", "paypal"]):
        return {
            "reply": (
                "Thank you so much for wanting to support us! 💖\n\n"
                "Every donation helps us:\n"
                "💬 Create more inspiring quotes\n"
                "📖 Share more empowerment stories\n"
                "🚀 Grow our community\n\n"
                "Visit our Donate section on the homepage to contribute. Even $1 makes a difference! 🌸"
            )
        }

    # =========================
    # ABOUT
    # =========================
    if any(w in msg for w in ["about", "what is this", "who are you", "what is quoteme", "tell me about", "quoteme zw", "mission", "vision"]):
        return {
            "reply": (
                "QuoteMe ZW is Zimbabwe's home of daily inspiration! 🇿🇼💖\n\n"
                "We are a platform dedicated to:\n"
                "🌟 Empowering women and youth\n"
                "💬 Sharing daily inspirational quotes\n"
                "📖 Celebrating real success stories\n"
                "📰 Publishing motivational blogs\n"
                "🤝 Building a supportive community\n\n"
                "Founded with love and a mission to make inspiration accessible to everyone in Zimbabwe and beyond. ✨"
            )
        }

    # =========================
    # FOUNDER / TEAM
    # =========================
    if any(w in msg for w in ["founder", "team", "who made", "who created", "creator", "owner"]):
        return {
            "reply": (
                "QuoteMe ZW was founded by a passionate visionary who believes every woman and young person "
                "deserves access to daily inspiration and a community that lifts them up. 💖\n\n"
                "Our small but dedicated team curates every quote, story, and blog with love and purpose. 🌸\n\n"
                "Want to know more? Visit our About section or reach out via our Contact form!"
            )
        }

    # =========================
    # CONTACT / SUPPORT
    # =========================
    if any(w in msg for w in ["contact", "email", "reach", "reach out", "message us", "get in touch", "collaborate"]):
        return {
            "reply": (
                "We'd love to hear from you! 📩\n\n"
                "You can reach us via:\n"
                "📝 The Contact form on the homepage\n"
                "📧 Email: support@quotemezw.com\n"
                "📸 Instagram: @quoteme_zw\n\n"
                "Whether it's a collaboration, feedback, or just to say hi — we're always happy to connect! 💖"
            )
        }

    # =========================
    # INSTAGRAM / SOCIAL MEDIA
    # =========================
    if any(w in msg for w in ["instagram", "social", "social media", "follow", "ig", "insta"]):
        return {
            "reply": (
                "Follow us on Instagram for daily inspiration! 📸\n\n"
                "👉 @quoteme_zw\n\n"
                "We post:\n"
                "✨ Daily motivational quotes\n"
                "💖 Empowerment content\n"
                "🌸 Behind-the-scenes updates\n\n"
                "See you there! 💕"
            )
        }

    # =========================
    # DARK MODE
    # =========================
    if any(w in msg for w in ["dark mode", "dark theme", "night mode", "light mode"]):
        return {"reply": "You can toggle between dark and light mode using the 🌙 button in the top navigation bar! Your preference is saved automatically. 🌙✨"}

    # =========================
    # LIKES / COMMENTS
    # =========================
    if any(w in msg for w in ["like", "comment", "react", "interaction"]):
        return {
            "reply": (
                "Great question! 💖\n\n"
                "On every quote, story, and blog you can:\n"
                "❤️ Like it to show your love\n"
                "💬 Leave a comment\n"
                "😊 Comments even show a positivity score!\n\n"
                "Try it on your favourite quote now! ✨"
            )
        }

    # =========================
    # ZIMBABWE
    # =========================
    if any(w in msg for w in ["zimbabwe", "zim", "harare", "bulawayo", "african", "africa"]):
        return {
            "reply": (
                "QuoteMe ZW is proudly Zimbabwean! 🇿🇼✨\n\n"
                "We celebrate the strength, resilience, and beauty of Zimbabwean women and youth. "
                "Our content is curated with our community in mind — relatable, empowering, and real. 💖\n\n"
                "Zimbabwe rises through its people! 🌟"
            )
        }

    # =========================
    # AFFIRMATION / POSITIVITY
    # =========================
    if any(w in msg for w in ["affirmation", "positive", "positivity", "feel good", "cheer up", "sad", "down", "depressed", "struggling"]):
        import random
        affirmations = [
            "You are stronger than you think, braver than you feel, and more loved than you know. 💖",
            "Every day is a new beginning. Take a deep breath and start again. 🌸",
            "You are enough. You have always been enough. ✨",
            "Your story isn't over yet — the best chapters are still ahead! 📖",
            "Difficult roads often lead to beautiful destinations. Keep going! 🌟",
        ]
        return {"reply": "Here's a little love from QuoteMe ZW 💖\n\n🌸 " + random.choice(affirmations) + "\n\nYou've got this! 💪"}

    # =========================
    # ADMIN HELP
    # =========================
    if "admin" in msg:
        return {"reply": "The admin panel is available at /admin 🔐 Only authorised team members can log in. If you need access, please contact us via the Contact form."}

    # =========================
    # HELP / COMMANDS
    # =========================
    if any(w in msg for w in ["help", "what can you do", "commands", "menu", "options", "what do you do"]):
        return {
            "reply": (
                "Here's everything I can help you with! 💖\n\n"
                "✨ *Quotes* — Get inspiring quotes\n"
                "🎲 *Random quote* — Surprise quote just for you\n"
                "📖 *Stories* — Women empowerment stories\n"
                "📰 *Blogs* — Motivational articles\n"
                "🗣️ *Forum* — Join the community discussion\n"
                "💖 *Donate* — Support our mission\n"
                "ℹ️ *About* — Learn about QuoteMe ZW\n"
                "🌸 *Affirmation* — Need a pick-me-up?\n"
                "📩 *Contact* — Get in touch with us\n"
                "📸 *Instagram* — Find us on social media\n"
                "🇿🇼 *Zimbabwe* — Our Zimbabwean pride!\n\n"
                "Just type any of the above or ask me anything! 😊"
            )
        }

    # =========================
    # FALLBACK
    # =========================
    import random
    fallbacks = [
        f"Hmm, I'm not sure about \"{raw}\" yet 🤔\n\nTry asking about quotes, stories, blogs, our forum, or say \'help\' to see all my commands! 😊",
        f"I didn't quite catch that! 🤔 Try saying \'help\' to see everything I can do. Or ask me for a \'random quote\'! ✨",
        "I'm still learning! 🌱 Try asking about quotes, stories, or say \'help\' for a full list of things I can help you with! 💖",
    ]
    return {"reply": random.choice(fallbacks)}