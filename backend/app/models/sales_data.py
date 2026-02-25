"""ORM model for sales data records submitted by publishers.

Each SalesData row captures aggregated revenue and unit sales for a single
title on a specific platform over a defined reporting period. The unique
constraint on (title_id, platform_name, period_start) prevents duplicate
ingestion for the same window.
"""

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.publisher import Publisher
    from app.models.title import Title


class DataSource(str, enum.Enum):
    """Origin of the sales figures for provenance tracking."""

    PUBLISHER = "PUBLISHER"
    LINKU = "LINKU"
    ESTIMATED = "ESTIMATED"


class SalesData(BaseModel):
    """Sales record for a title on a platform within a reporting period.

    Attributes:
        id: Auto-incrementing primary key.
        title_id: Foreign key referencing the manga title.
        publisher_id: Foreign key referencing the reporting publisher.
        platform_name: Distribution platform (e.g. "Kindle", "BookWalker").
            Null indicates an aggregate across all platforms.
        period_start: First day of the reporting period (inclusive).
        period_end: Last day of the reporting period (inclusive).
        revenue: Gross revenue in the publisher's reporting currency.
        units_sold: Number of individual copies / chapters sold.
        data_source: Provenance classification of the figures.
        created_at: Row creation timestamp (no updated_at; records are immutable).
    """

    __tablename__ = "sales_data"

    title_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("titles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publisher_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    data_source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, name="data_source"),
        nullable=False,
        default=DataSource.PUBLISHER,
    )

    # Relationships
    title: Mapped["Title"] = relationship(
        "Title", back_populates="sales_data", lazy="select"
    )
    publisher: Mapped["Publisher"] = relationship(
        "Publisher", back_populates="sales_data", lazy="select"
    )

    __table_args__ = (
        UniqueConstraint(
            "title_id", "platform_name", "period_start",
            name="uq_sales_data_title_platform_period",
        ),
        Index("ix_sales_data_period_start", "period_start"),
        Index("ix_sales_data_title_period", "title_id", "period_start"),
        Index("ix_sales_data_publisher_period", "publisher_id", "period_start"),
    )

    def __repr__(self) -> str:
        return (
            f"<SalesData id={self.id} title_id={self.title_id} "
            f"platform={self.platform_name!r} period_start={self.period_start}>"
        )
