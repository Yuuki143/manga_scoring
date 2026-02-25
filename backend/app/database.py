"""Database engine and session configuration for the MMIP application.

Provides SQLAlchemy 2.0-style engine setup, session factory, and the
declarative base used by all ORM models. The get_db() function is a
FastAPI dependency that yields a transactional session and ensures it is
closed after each request.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request.

    The session is committed on success and rolled back on exception,
    then closed in the finally block regardless of outcome.

    Yields:
        Session: An active SQLAlchemy ORM session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
