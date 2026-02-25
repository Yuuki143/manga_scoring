"""ORM model for audit log entries.

Each AuditLog row records a single platform action performed by a user or
a publisher API client. Audit logs are append-only; rows should never be
updated or deleted. The updated_at column inherited from BaseModel is
therefore effectively redundant but kept for schema consistency.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.publisher import Publisher
    from app.models.user import User


class AuditLog(BaseModel):
    """An append-only record of a user or API action on the MMIP platform.

    Attributes:
        id: Auto-incrementing primary key.
        user_id: Optional FK to the User who performed the action.
            Null for unauthenticated or system-initiated actions.
        publisher_id: Optional FK to the Publisher context of the action.
            Null for cross-publisher admin operations.
        action: Short verb describing what was done
            (e.g. "data_upload", "score_view", "api_access").
        resource_type: Category of the affected resource
            (e.g. "sales_data", "title", "alert").
        resource_id: String representation of the specific resource PK,
            if applicable.
        ip_address: IPv4 or IPv6 address of the request origin (max 45 chars
            to accommodate IPv6 with zone ID).
        details: Arbitrary JSON payload for additional context such as
            request parameters or diff summaries.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp (nominally the same as
            created_at for append-only logs).
        user: Many-to-one relationship to the acting User.
        publisher: Many-to-one relationship to the Publisher context.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    publisher_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("publishers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User | None"] = relationship(
        "User", lazy="select", foreign_keys=[user_id]
    )
    publisher: Mapped["Publisher | None"] = relationship(
        "Publisher", lazy="select", foreign_keys=[publisher_id]
    )

    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_publisher_id", "publisher_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action_resource", "action", "resource_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"resource_type={self.resource_type!r} user_id={self.user_id}>"
        )
