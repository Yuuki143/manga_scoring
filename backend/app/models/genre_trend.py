"""ORM model for genre-level trend snapshots.

GenreTrend rows are computed by the analytics pipeline and capture
aggregate market signals for each manga genre on a periodic basis.
They power the genre trend charts and GENRE_TREND alert type.
"""

import enum
from datetime import date

from sqlalchemy import Date, Enum, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TrendingDirection(str, enum.Enum):
    """Directional momentum of the genre over the measured period."""

    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class GenreTrend(BaseModel):
    """Periodic aggregate trend snapshot for a manga genre.

    Attributes:
        id: Auto-incrementing primary key.
        genre: Genre identifier matching the Genre enum in title.py.
            Stored as a plain string to allow future genre additions without
            a migration on this table.
        period_date: The start date of the measurement period.
        growth_rate: Period-over-period revenue/unit growth rate as a
            decimal fraction (e.g. 0.15 = 15% growth).
        title_count: Number of active titles in the genre during the period.
        avg_engagement: Average first_episode_engagement across titles in
            the genre. Null if insufficient platform data is available.
        avg_revenue: Average revenue per title in the genre. Null if
            revenue data coverage is insufficient.
        trending_direction: Summary direction of momentum.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
    """

    __tablename__ = "genre_trends"

    genre: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    growth_rate: Mapped[float] = mapped_column(Float, nullable=False)
    title_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_engagement: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    trending_direction: Mapped[TrendingDirection] = mapped_column(
        Enum(TrendingDirection, name="trending_direction"),
        nullable=False,
        default=TrendingDirection.STABLE,
        index=True,
    )

    __table_args__ = (
        Index("ix_genre_trends_genre_period", "genre", "period_date"),
        Index("ix_genre_trends_period_date", "period_date"),
        Index("ix_genre_trends_direction", "trending_direction"),
    )

    def __repr__(self) -> str:
        return (
            f"<GenreTrend id={self.id} genre={self.genre!r} "
            f"period={self.period_date} direction={self.trending_direction}>"
        )
