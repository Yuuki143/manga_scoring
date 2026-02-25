"""Data processing pipeline for sales data uploads.

Orchestrates the full parse → validate → title-match → upsert pipeline
and returns a detailed summary that the API layer exposes to callers.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.parsers import SalesDataParser
from app.models.sales_data import DataSource, SalesData
from app.models.title import Genre, Title, TitleStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default placeholder values for auto-created titles
# ---------------------------------------------------------------------------
_DEFAULT_GENRE = Genre.OTHER
_DEFAULT_STATUS = TitleStatus.ONGOING
_DEFAULT_AUTHOR = "Unknown"
_DEFAULT_START_DATE = date(2000, 1, 1)


class DataProcessor:
    """Orchestrate the ingestion pipeline from raw file to persisted records.

    Args:
        db: An active SQLAlchemy :class:`~sqlalchemy.orm.Session`.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.parser = SalesDataParser()

    # ---------------------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------------------

    def process_upload(
        self,
        file_content: bytes,
        filename: str,
        publisher_id: int,
    ) -> dict:
        """Run the full ingestion pipeline for a single uploaded file.

        Steps:

        1. Parse the file into raw record dicts.
        2. For each record, resolve the title name to an existing
           :class:`~app.models.title.Title` row (case-insensitive match
           within the publisher's catalogue).
        3. If no matching title exists, create a placeholder title.
        4. Upsert the :class:`~app.models.sales_data.SalesData` row
           (update revenue/units if ``(title_id, platform_name, period_start)``
           already exists; insert otherwise).
        5. Return a summary dict.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Original filename (used for format detection).
            publisher_id: ID of the publisher performing the upload.

        Returns:
            A dict with keys:

            * ``"upload_id"`` – unique identifier for this upload batch
            * ``"status"`` – ``"success"`` or ``"partial"``
            * ``"records_processed"`` – total rows in the parsed result
            * ``"records_accepted"`` – rows successfully written to the DB
            * ``"records_rejected"`` – rows that failed validation or DB write
            * ``"titles_created"`` – number of auto-created placeholder titles
            * ``"format_detected"`` – platform format key from the parser
            * ``"errors"`` – list of human-readable error strings
        """
        upload_id = str(uuid.uuid4())
        all_errors: list[str] = []
        records_accepted = 0
        records_rejected = 0
        titles_created = 0

        # --- Step 1: Parse ---
        parsed = self.parser.parse(file_content, filename, publisher_id)
        all_errors.extend(parsed["errors"])
        format_detected = parsed["format_detected"]
        raw_records: list[dict] = parsed["records"]
        records_processed = len(raw_records)

        if not raw_records:
            return {
                "upload_id": upload_id,
                "status": "partial" if all_errors else "success",
                "records_processed": records_processed,
                "records_accepted": 0,
                "records_rejected": 0,
                "titles_created": 0,
                "format_detected": format_detected,
                "errors": all_errors,
            }

        # --- Steps 2-4: Title matching + upsert ---
        # Cache title lookups within this upload to avoid repeated DB queries
        title_cache: dict[str, Title] = {}

        for raw in raw_records:
            try:
                title, created = self._get_or_create_title(
                    title_name=raw["title_name"],
                    publisher_id=publisher_id,
                    cache=title_cache,
                )
                if created:
                    titles_created += 1

                self._upsert_sales_data(
                    title_id=title.id,
                    publisher_id=publisher_id,
                    platform_name=raw["platform_name"],
                    period_start=raw["period_start"],
                    period_end=raw["period_end"],
                    revenue=raw["revenue"],
                    units_sold=raw["units_sold"],
                )
                records_accepted += 1

            except IntegrityError as exc:
                self.db.rollback()
                logger.warning("IntegrityError on record for title '%s': %s", raw.get("title_name"), exc)
                all_errors.append(
                    f"Database integrity error for title '{raw.get('title_name')}' "
                    f"({raw.get('period_start')}): {exc.orig}"
                )
                records_rejected += 1

            except Exception as exc:
                self.db.rollback()
                logger.exception("Unexpected error processing record: %s", exc)
                all_errors.append(
                    f"Unexpected error for title '{raw.get('title_name')}': {exc}"
                )
                records_rejected += 1

        # Final commit for any pending work
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception("Failed to commit upload batch: %s", exc)
            all_errors.append(f"Batch commit failed: {exc}")

        status = "success" if records_rejected == 0 else "partial"

        return {
            "upload_id": upload_id,
            "status": status,
            "records_processed": records_processed,
            "records_accepted": records_accepted,
            "records_rejected": records_rejected,
            "titles_created": titles_created,
            "format_detected": format_detected,
            "errors": all_errors,
        }

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _get_or_create_title(
        self,
        title_name: str,
        publisher_id: int,
        cache: dict[str, Title],
    ) -> tuple[Title, bool]:
        """Return the :class:`~app.models.title.Title` for *title_name*, creating
        it as a placeholder if it does not exist.

        Args:
            title_name: Raw title string from the uploaded file.
            publisher_id: Publisher that owns the title.
            cache: In-memory dict keyed by ``"{publisher_id}:{lower_name}"``
                to avoid redundant DB queries within a single upload batch.

        Returns:
            ``(title, was_created)`` tuple.
        """
        cache_key = f"{publisher_id}:{title_name.lower()}"
        if cache_key in cache:
            return cache[cache_key], False

        # Case-insensitive lookup
        title: Title | None = (
            self.db.query(Title)
            .filter(
                Title.publisher_id == publisher_id,
                Title.name.ilike(title_name),
            )
            .first()
        )

        if title is not None:
            cache[cache_key] = title
            return title, False

        # Also try English name
        title = (
            self.db.query(Title)
            .filter(
                Title.publisher_id == publisher_id,
                Title.name_en.ilike(title_name),
            )
            .first()
        )

        if title is not None:
            cache[cache_key] = title
            return title, False

        # Create placeholder title
        title = Title(
            name=title_name,
            publisher_id=publisher_id,
            genre=_DEFAULT_GENRE,
            author=_DEFAULT_AUTHOR,
            status=_DEFAULT_STATUS,
            start_date=_DEFAULT_START_DATE,
            is_active=True,
        )
        self.db.add(title)
        self.db.flush()  # Populate title.id without committing the transaction

        cache[cache_key] = title
        logger.info(
            "Auto-created placeholder title '%s' for publisher_id=%s",
            title_name,
            publisher_id,
        )
        return title, True

    def _upsert_sales_data(
        self,
        title_id: int,
        publisher_id: int,
        platform_name: str | None,
        period_start: date,
        period_end: date,
        revenue: float,
        units_sold: int,
    ) -> SalesData:
        """Insert or update a :class:`~app.models.sales_data.SalesData` record.

        The unique key is ``(title_id, platform_name, period_start)``.  If a
        matching row already exists its ``revenue`` and ``units_sold`` are
        updated in place; otherwise a new row is inserted.

        Args:
            title_id: FK to the resolved title.
            publisher_id: FK to the uploading publisher.
            platform_name: Distribution platform name (may be ``None`` for
                aggregate records).
            period_start: First day of the reporting period.
            period_end: Last day of the reporting period.
            revenue: Gross revenue figure.
            units_sold: Number of units sold.

        Returns:
            The persisted :class:`~app.models.sales_data.SalesData` instance.
        """
        existing: SalesData | None = (
            self.db.query(SalesData)
            .filter(
                and_(
                    SalesData.title_id == title_id,
                    SalesData.platform_name == platform_name,
                    SalesData.period_start == period_start,
                )
            )
            .first()
        )

        if existing is not None:
            existing.revenue = revenue
            existing.units_sold = units_sold
            existing.period_end = period_end
            self.db.flush()
            return existing

        record = SalesData(
            title_id=title_id,
            publisher_id=publisher_id,
            platform_name=platform_name,
            period_start=period_start,
            period_end=period_end,
            revenue=revenue,
            units_sold=units_sold,
            data_source=DataSource.PUBLISHER,
        )
        self.db.add(record)
        self.db.flush()
        return record
