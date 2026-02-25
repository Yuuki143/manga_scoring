"""ORM model for manga titles (series).

A Title is the central entity of MMIP. Sales data, platform engagement
metrics, scoring results, and alerts all link back to a single Title row.
"""

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.platform_data import PlatformData
    from app.models.publisher import Publisher
    from app.models.sales_data import SalesData
    from app.models.score import TitleScore


class Genre(str, enum.Enum):
    """Manga genre classification used for trend analysis and filtering."""

    SHONEN = "SHONEN"
    SHOJO = "SHOJO"
    SEINEN = "SEINEN"
    JOSEI = "JOSEI"
    KODOMO = "KODOMO"
    BL = "BL"
    GL = "GL"
    ISEKAI = "ISEKAI"
    HORROR = "HORROR"
    ROMANCE = "ROMANCE"
    ACTION = "ACTION"
    FANTASY = "FANTASY"
    COMEDY = "COMEDY"
    SLICE_OF_LIFE = "SLICE_OF_LIFE"
    SPORTS = "SPORTS"
    MYSTERY = "MYSTERY"
    SCI_FI = "SCI_FI"
    OTHER = "OTHER"


class TitleStatus(str, enum.Enum):
    """Publication status of the title."""

    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    HIATUS = "HIATUS"
    CANCELLED = "CANCELLED"


class Title(BaseModel):
    """A manga series tracked within MMIP.

    Attributes:
        id: Auto-incrementing primary key.
        name: Original title name (usually Japanese).
        name_en: English localised title, if available.
        publisher_id: Foreign key to the owning Publisher.
        genre: Primary genre for scoring and trend grouping.
        author: Creator(s) of the series.
        status: Current publication status.
        start_date: Date of first chapter publication.
        end_date: Date of final chapter publication (null if not completed).
        has_anime: Whether the title has an anime adaptation.
        anime_start_date: Air date of the first anime episode, if applicable.
        is_active: Soft-delete flag; inactive titles are hidden from reports.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
        publisher: Many-to-one relationship to the owning Publisher.
        scores: All TitleScore records calculated for this title.
        sales_data: All SalesData records for this title.
        platform_data: All PlatformData records for this title.
        alerts: All Alert records referencing this title.
    """

    __tablename__ = "titles"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publisher_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    genre: Mapped[Genre] = mapped_column(
        Enum(Genre, name="genre"),
        nullable=False,
        index=True,
    )
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TitleStatus] = mapped_column(
        Enum(TitleStatus, name="title_status"),
        nullable=False,
        default=TitleStatus.ONGOING,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    has_anime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anime_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    publisher: Mapped["Publisher"] = relationship(
        "Publisher", back_populates="titles", lazy="select"
    )
    scores: Mapped[list["TitleScore"]] = relationship(
        "TitleScore", back_populates="title", lazy="select"
    )
    sales_data: Mapped[list["SalesData"]] = relationship(
        "SalesData", back_populates="title", lazy="select"
    )
    platform_data: Mapped[list["PlatformData"]] = relationship(
        "PlatformData", back_populates="title", lazy="select"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="title", lazy="select"
    )

    __table_args__ = (
        Index("ix_titles_publisher_genre", "publisher_id", "genre"),
        Index("ix_titles_publisher_status", "publisher_id", "status"),
        Index("ix_titles_is_active", "is_active"),
        Index("ix_titles_has_anime", "has_anime"),
    )

    def __repr__(self) -> str:
        return f"<Title id={self.id} name={self.name!r} genre={self.genre} status={self.status}>"
