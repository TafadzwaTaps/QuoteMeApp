# create_admin.py
from models import Base, Admin
from main import engine, SessionLocal
from passlib.context import CryptContext
import logging_setup

# ===== CONFIG =====
USERNAME = "Ruva"
PASSWORD = "Ruva123$"  # DO NOT slice passwords

logger = logging_setup.logger

# ===== FIX: proper passlib context (solves bcrypt crash) =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ===== SESSION =====
db = SessionLocal()

try:
    # Check if admin exists
    existing_admin = db.query(Admin).filter(Admin.username == USERNAME).first()
    if existing_admin:
        db.delete(existing_admin)
        db.commit()
        logger.info(f"Existing admin '{USERNAME}' deleted.")

    # FIX: safe hashing (no 72-byte crash handling needed anymore)
    hashed_password = pwd_context.hash(PASSWORD)

    # Create admin
    new_admin = Admin(
        username=USERNAME,
        password_hash=hashed_password
    )

    db.add(new_admin)
    db.commit()

    logger.info(f"Admin '{USERNAME}' created successfully.")

    print(f"✅ Admin '{USERNAME}' successfully created.")

except Exception as e:
    logger.error(f"Error creating admin: {e}")
    print(f"❌ Failed to create admin: {e}")

finally:
    db.close()