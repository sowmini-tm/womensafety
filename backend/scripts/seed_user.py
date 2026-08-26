"""Simple seeding script: creates tables and an admin user."""
from app.database import engine, SessionLocal
from app.models.base import Base
from app.models.user import User
from app.utils.security import hash_password


def create_tables():
    Base.metadata.create_all(bind=engine)


def seed_admin(email: str = "admin@example.com", mobile: str = "+10000000000", password: str = "password"):
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print("Admin user already exists")
            return
        admin = User(email=email, mobile_number=mobile, password_hash=hash_password(password), is_verified=True)
        db.add(admin)
        db.commit()
        print("Admin user created:", admin.email)


if __name__ == "__main__":
    create_tables()
    seed_admin()
