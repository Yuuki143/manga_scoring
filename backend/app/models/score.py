"""ORM model for computed MMIP scores associated with manga titles.

Each TitleScore row represents a point-in-time scoring snapshot generated
by the scoring engine. Scores are immutable once written; a new row is
inserted on every recalculation so historical trends can be tracked.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.title import Title


class ConfidenceRating(str, enum.Enum):
    """Data-quality rating that qualifies how reliable the score is.

    A  - High confidence: sufficient data from multiple sources.
    B  - Medium confidence: partial data coverage.
    C  - Low confidence: limited data; treat scores as indicative only.
    """

    A = "A"
    B = "B"
    C = "C"


class TitleScore(BaseModel):
    """Point-in-time composite score for a manga title.

    All score components are normalised to a 0–100 scale.

    Attributes:
        id: Auto-incrementing primary key.
        title_id: Foreign key referencing the scored manga title.
        calculated_at: UTC timestamp when the scoring engine ran.
        overall_score: Weighted aggregate of all component scores.
        revenue_score: Component reflecting absolute and relative revenue.
        growth_score: Component reflecting revenue and reader growth rate.
        platform_distribution_score: Component reflecting reach across
            multiple platforms.
        stability_score: Component reflecting consistency over time.
        ranking_frequency_score: Component reflecting how often the title
            appears in top-N charts.
        confidence_rating: Data-quality grade for this snapshot.
        global_potential_score: Optional estimate of international market
            potential based on overseas engagement signals.
        genre_percentile: Percentile rank within the title's genre cohort.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
        title: Many-to-one relationship to the scored Title.
    """

    __tablename__ = "title_scores"

    title_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("titles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Component scores (0–100)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    revenue_score: Mapped[float] = mapped_column(Float, nullable=False)
    growth_score: Mapped[float] = mapped_column(Float, nullable=False)
    platform_distribution_score: Mapped[float] = mapped_column(Float, nullable=False)
    stability_score: Mapped[float] = mapped_column(Float, nullable=False)
    ranking_frequency_score: Mapped[float] = mapped_column(Float, nullable=False)

    confidence_rating: Mapped[ConfidenceRating] = mapped_column(
        Enum(ConfidenceRating, name="confidence_rating"),
        nullable=False,
        default=ConfidenceRating.C,
    )
    global_potential_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    genre_percentile: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    title: Mapped["Title"] = relationship(
        "Title", back_populates="scores", lazy="select"
    )

    __table_args__ = (
        UniqueConstraint(
            "title_id", "calculated_at",
            name="uq_title_scores_title_calculated_at",
        ),
        Index("ix_title_scores_overall_score", "overall_score"),
        Index("ix_title_scores_title_calculated_at", "title_id", "calculated_at"),
        Index("ix_title_scores_confidence_rating", "confidence_rating"),
    )

    def __repr__(self) -> str:
        return (
            f"<TitleScore id={self.id} title_id={self.title_id} "
            f"overall={self.overall_score:.1f} confidence={self.confidence_rating}>"
        )
