"""ORM model for per-platform engagement metrics collected for manga titles.

PlatformData stores a daily or periodic snapshot of reader engagement
signals from a digital distribution platform. These signals feed directly
into the scoring engine's platform_distribution_score and ranking
components.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.title import Title


class PlatformData(BaseModel):
    """Engagement snapshot for a title on a specific platform on a given date.

    Attributes:
        id: Auto-incrementing primary key.
        title_id: Foreign key referencing the manga title.
        platform_name: Name of the distribution platform (e.g. "MangaPlus").
        period_date: The date this snapshot was recorded.
        first_episode_engagement: Episode 1->2 transition rate (0.0–1.0).
            Null when the title has fewer than two episodes on the platform.
        retention_rate: Proportion of readers who return after their first
            session (0.0–1.0). Null if not available from the platform.
        comment_volume: Total user comments posted during the period.
        comment_sentiment: Average sentiment score across comments (-1.0 to 1.0).
            Negative values indicate critical/negative reception.
        ranking_position: Chart position at the end of the period (1 = top).
        page_views: Total page/chapter views during the period.
        unique_readers: Unique reader count during the period.
        created_at: Row creation timestamp.
    """

    __tablename__ = "platform_data"

    title_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("titles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_name: Mapped[str] = mapped_column(String(255), nullable=False)
    period_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Engagement metrics (all optional — not every platform exposes every signal)
    first_episode_engagement: Mapped[float | None] = mapped_column(Float, nullable=True)
    retention_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment_sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    ranking_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unique_readers: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    title: Mapped["Title"] = relationship(
        "Title", back_populates="platform_data", lazy="select"
    )

    __table_args__ = (
        UniqueConstraint(
            "title_id", "platform_name", "period_date",
            name="uq_platform_data_title_platform_date",
        ),
        Index("ix_platform_data_title_date", "title_id", "period_date"),
        Index("ix_platform_data_platform_date", "platform_name", "period_date"),
        Index("ix_platform_data_ranking_position", "ranking_position"),
    )

    def __repr__(self) -> str:
        return (
            f"<PlatformData id={self.id} title_id={self.title_id} "
            f"platform={self.platform_name!r} date={self.period_date}>"
        )
