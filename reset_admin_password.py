from models import Base, Admin
from main import engine, SessionLocal
from passlib.hash import bcrypt
import logging_setup
import getpass

db = SessionLocal()

# Ask which admin to reset
username = input("Enter the admin username to reset password: ").strip()
admin = db.query(Admin).filter(Admin.username == username).first()

if not admin:
    print(f"No admin found with username '{username}'")
    logging_setup.logger.warning(f"Attempted to reset password for non-existent admin '{username}'")
else:
    # Ask for new password securely
    password = getpass.getpass("Enter new password: ").strip()
    if not password:
        print("No password entered. Operation cancelled.")
        logging_setup.logger.warning(f"Password reset cancelled for admin '{username}'")
    else:
        # Truncate for bcrypt 72-byte limit
        password = password[:72]
        admin.password_hash = bcrypt.hash(password)
        db.commit()
        print(f"Password successfully reset for admin '{username}'")
        logging_setup.logger.info(f"Admin '{username}' password reset successfully.")

db.close()
