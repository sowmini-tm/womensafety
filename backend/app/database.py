from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Base

engine = create_engine(str(settings.DATABASE_URL), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> tuple[bool, str | None]:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True, None
    except SQLAlchemyError:
        # Never leak connection strings/credentials in health responses.
        return False, "Database connection failed"
    except Exception:
        return False, "Database connection failed"
