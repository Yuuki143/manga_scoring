"""ORM model for platform users with role-based access control.

Users belong to a Publisher and carry a Role that determines which API
endpoints and data views they may access. Authentication is performed with
hashed passwords; raw passwords are never stored.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.publisher import Publisher


class UserRole(str, enum.Enum):
    """Role governing what a user can read and write within MMIP."""

    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class User(BaseModel):
    """A registered platform user associated with a Publisher.

    Attributes:
        id: Auto-incrementing primary key.
        email: Unique login identifier for the user (indexed).
        hashed_password: Bcrypt hash of the user's password.
        full_name: Display name shown in the UI.
        publisher_id: Foreign key linking the user to their publisher.
        role: RBAC role controlling access level.
        is_active: Soft-delete / suspension flag.
        last_login: UTC timestamp of the most recent successful login.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
        publisher: Many-to-one relationship to the owning Publisher.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.VIEWER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    publisher: Mapped["Publisher"] = relationship(
        "Publisher", back_populates="users", lazy="select"
    )

    __table_args__ = (
        Index("ix_users_publisher_role", "publisher_id", "role"),
        Index("ix_users_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
