"""ORM model for manga publishers.

A Publisher represents a content owner / licensee that submits sales data
and consumes intelligence reports through the MMIP platform. Each publisher
is assigned a subscription tier that gates which features and alerts are
visible to its users.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.sales_data import SalesData
    from app.models.title import Title
    from app.models.user import User


class PublisherTier(str, enum.Enum):
    """Subscription tier controlling feature access."""

    BASIC = "BASIC"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class DataProvisionFrequency(str, enum.Enum):
    """How often the publisher is expected to upload sales data."""

    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"


class Publisher(BaseModel):
    """A manga publisher registered on the MMIP platform.

    Attributes:
        id: Auto-incrementing primary key.
        name: Human-readable publisher name (unique).
        slug: URL-safe identifier used in API paths (unique, indexed).
        tier: Subscription tier governing access to premium features.
        contact_email: Primary operational contact address.
        api_key: Optional API key for programmatic data ingestion.
        is_active: Soft-delete flag; inactive publishers cannot log in.
        data_provision_frequency: Expected cadence for sales data uploads.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
        users: All User accounts belonging to this publisher.
        titles: Manga titles owned / licensed by this publisher.
        sales_data: Sales records associated with this publisher.
        alerts: Intelligence alerts generated for this publisher.
    """

    __tablename__ = "publishers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    tier: Mapped[PublisherTier] = mapped_column(
        Enum(PublisherTier, name="publisher_tier"),
        nullable=False,
        default=PublisherTier.BASIC,
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_provision_frequency: Mapped[DataProvisionFrequency] = mapped_column(
        Enum(DataProvisionFrequency, name="data_provision_frequency"),
        nullable=False,
        default=DataProvisionFrequency.MONTHLY,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="publisher", lazy="select"
    )
    titles: Mapped[list["Title"]] = relationship(
        "Title", back_populates="publisher", lazy="select"
    )
    sales_data: Mapped[list["SalesData"]] = relationship(
        "SalesData", back_populates="publisher", lazy="select"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="publisher", lazy="select"
    )

    __table_args__ = (
        Index("ix_publishers_tier", "tier"),
        Index("ix_publishers_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Publisher id={self.id} slug={self.slug!r} tier={self.tier}>"
