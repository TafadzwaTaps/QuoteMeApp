# create_admin.py
from models import Base, Admin
from main import engine, SessionLocal
from passlib.hash import bcrypt
import logging_setup  # your logger

# ===== CONFIG =====
USERNAME = "Ruva"
PASSWORD = "Ruva123$"  # <=72 chars
PASSWORD = PASSWORD[:72]

logger = logging_setup.logger

# ===== CREATE SESSION =====
db = SessionLocal()

try:
    # Check if admin exists
    existing_admin = db.query(Admin).filter(Admin.username == USERNAME).first()
    if existing_admin:
        db.delete(existing_admin)
        db.commit()
        logger.info(f"Existing admin '{USERNAME}' deleted.")

    # Hash the password
    hashed_password = bcrypt.hash(PASSWORD)

    # Create new admin
    new_admin = Admin(username=USERNAME, password_hash=hashed_password)
    db.add(new_admin)
    db.commit()
    logger.info(f"Admin '{USERNAME}' created with password '{PASSWORD}'.")

    print(f"✅ Admin '{USERNAME}' successfully created with password '{PASSWORD}'.")

except Exception as e:
    logger.error(f"Error creating admin: {e}")
    print(f"❌ Failed to create admin: {e}")

finally:
    db.close()
