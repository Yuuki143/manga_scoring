"""ORM model for platform ranking snapshots.

Each RankingData row records a title's rank position on a specific platform
at a given point in time.  Rankings are collected periodically from platform
APIs / scrapes and used by Axis 5 (Ranking Frequency) of the scoring engine.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.title import Title


class RankingData(BaseModel):
    """Ranking snapshot for a title on a specific platform.

    Attributes:
        id: Auto-incrementing primary key.
        title_id: Foreign key referencing the manga title.
        platform_name: Platform where the ranking was observed.
        rank: Numerical rank position (1 = top).
        ranking_type: Category of ranking (e.g. "sales", "trending").
        record_date: Date the ranking was observed.
    """

    __tablename__ = "ranking_data"

    title_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("titles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    ranking_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="sales"
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    title: Mapped["Title"] = relationship("Title", lazy="select")

    __table_args__ = (
        Index("ix_ranking_data_title_rank", "title_id", "rank"),
        Index("ix_ranking_data_date", "record_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<RankingData id={self.id} title_id={self.title_id} "
            f"platform={self.platform_name!r} rank={self.rank}>"
        )
