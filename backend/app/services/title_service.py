"""Business logic layer for manga title operations.

Provides authorisation-aware queries so that route handlers do not
need to embed publisher-scoping logic directly.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.title import Genre, Title

logger = logging.getLogger(__name__)


class TitleService:
    """Read and write operations for :class:`~app.models.title.Title` records.

    Args:
        db: An active SQLAlchemy :class:`~sqlalchemy.orm.Session`.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------------------------------------------------------------------
    # Retrieval helpers
    # ---------------------------------------------------------------------------

    def get_title(self, title_id: int, publisher_id: int) -> Optional[Title]:
        """Return the title with *title_id* if it belongs to *publisher_id*.

        Enforces publisher isolation: a publisher cannot access another
        publisher's titles through this method.

        Args:
            title_id: Primary key of the requested title.
            publisher_id: ID of the requesting publisher.

        Returns:
            The :class:`~app.models.title.Title` instance, or ``None`` if
            it does not exist or belongs to a different publisher.
        """
        return (
            self.db.query(Title)
            .filter(
                Title.id == title_id,
                Title.publisher_id == publisher_id,
                Title.is_active.is_(True),
            )
            .first()
        )

    def get_publisher_titles(self, publisher_id: int) -> list[Title]:
        """Return all active titles that belong to *publisher_id*.

        Results are ordered by title name for stable pagination.

        Args:
            publisher_id: ID of the publisher whose catalogue is requested.

        Returns:
            List of :class:`~app.models.title.Title` instances, possibly empty.
        """
        return (
            self.db.query(Title)
            .filter(
                Title.publisher_id == publisher_id,
                Title.is_active.is_(True),
            )
            .order_by(Title.name)
            .all()
        )

    def get_genre_titles(self, genre: str) -> list[Title]:
        """Return all active titles in *genre* across all publishers.

        This is a cross-publisher read used for genre trend analysis and
        should only be called from internal scoring / analytics code, not
        from publisher-facing API routes.

        Args:
            genre: Genre string matching one of the
                :class:`~app.models.title.Genre` enum values (case-insensitive).

        Returns:
            List of matching active :class:`~app.models.title.Title` instances.

        Raises:
            ValueError: If *genre* is not a recognised
                :class:`~app.models.title.Genre` value.
        """
        # Normalise and validate the genre string
        genre_upper = genre.upper()
        try:
            genre_enum = Genre(genre_upper)
        except ValueError:
            valid = [g.value for g in Genre]
            raise ValueError(
                f"'{genre}' is not a valid genre. Valid genres: {valid}"
            )

        return (
            self.db.query(Title)
            .filter(
                Title.genre == genre_enum,
                Title.is_active.is_(True),
            )
            .order_by(Title.name)
            .all()
        )

    # ---------------------------------------------------------------------------
    # Mutation helpers
    # ---------------------------------------------------------------------------

    def create_title(self, **kwargs) -> Title:
        """Create and persist a new :class:`~app.models.title.Title`.

        All keyword arguments are passed directly to the model constructor.
        The caller is responsible for supplying all required fields
        (``name``, ``publisher_id``, ``genre``, ``author``, ``start_date``).

        Returns:
            The newly created and refreshed title instance.
        """
        title = Title(**kwargs)
        self.db.add(title)
        self.db.commit()
        self.db.refresh(title)
        logger.info("Created title id=%s name=%r for publisher_id=%s",
                    title.id, title.name, title.publisher_id)
        return title

    def update_title(self, title: Title, **kwargs) -> Title:
        """Apply *kwargs* as attribute updates to an existing *title*.

        The session is flushed and committed after applying changes.

        Args:
            title: The title instance to update (must already be in session).
            **kwargs: Attribute name / value pairs to update.

        Returns:
            The refreshed title instance.
        """
        for attr, value in kwargs.items():
            setattr(title, attr, value)
        self.db.commit()
        self.db.refresh(title)
        return title

    def deactivate_title(self, title: Title) -> Title:
        """Soft-delete a title by setting ``is_active = False``.

        Args:
            title: The title to deactivate.

        Returns:
            The updated title instance.
        """
        title.is_active = False
        self.db.commit()
        self.db.refresh(title)
        logger.info("Deactivated title id=%s", title.id)
        return title
