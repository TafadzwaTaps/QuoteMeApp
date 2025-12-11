from models import Base, Admin
from main import engine, SessionLocal
from passlib.hash import bcrypt
import logging_setup  # import logger

db = SessionLocal()

username = "admin"
password = "admin123"  # change to a strong password

existing_admin = db.query(Admin).filter(Admin.username == username).first()
if existing_admin:
    logging_setup.logger.info(f"Admin '{username}' already exists.")
else:
    hashed_password = bcrypt.hash(password)
    admin = Admin(username=username, password_hash=hashed_password)
    db.add(admin)
    db.commit()
    logging_setup.logger.info(f"Admin '{username}' created with default password.")
db.close()
