"""Mixin providing common audit fields shared across all ORM models.

Import TimestampMixin and mix it into any model that needs automatic
created_at / updated_at tracking without a standalone primary key.
The primary key (id) is also defined here for convenience.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimestampMixin:
    """Adds created_at and updated_at columns populated by the database server.

    Attributes:
        created_at: Timestamp set once when the row is first inserted.
        updated_at: Timestamp refreshed automatically on every UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """Abstract base ORM model with integer primary key and audit timestamps.

    All concrete models should inherit from this class rather than from
    Base directly so that id, created_at, and updated_at are consistently
    defined across the schema.

    Attributes:
        id: Auto-incrementing integer primary key.
        created_at: Inherited from TimestampMixin.
        updated_at: Inherited from TimestampMixin.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
