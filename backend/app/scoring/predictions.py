"""
MMIP Hit Prediction Algorithm

Generates ranked lists of manga titles likely to see significant commercial
growth based on three independent pattern-detection strategies:

1. Anime-Linked Growth   – Titles that already have an anime and are
                           experiencing a measurable sales uplift since the
                           anime premiered.

2. Anime Candidates      – Popular titles without an anime whose genre has a
                           strong historical anime-lift multiplier, making
                           them strong candidates for future licensing deals.

3. Overseas Expansion    – Titles with strong domestic performance but low
                           global potential scores, indicating untapped
                           international markets.

Typical usage::

    from app.database import SessionLocal
    from app.scoring.predictions import HitPredictor

    with SessionLocal() as db:
        predictor = HitPredictor(db)
        results = predictor.get_predictions(publisher_id=7)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.scoring.utils import growth_rate, sigmoid_normalize

# ---------------------------------------------------------------------------
# Lazy model imports (identical pattern to engine.py)
# ---------------------------------------------------------------------------
try:
    from app.models.title import Title  # type: ignore[import]
except ImportError:  # pragma: no cover
    Title = None  # type: ignore[assignment]

try:
    from app.models.sales_data import SalesData  # type: ignore[import]
except ImportError:  # pragma: no cover
    SalesData = None  # type: ignore[assignment]

try:
    from app.models.platform_data import PlatformData  # type: ignore[import]
except ImportError:  # pragma: no cover
    PlatformData = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

# Minimum growth multiplier for a title to appear in anime-linked results
ANIME_GROWTH_THRESHOLD = 0.50  # 50 % uplift

# Minimum percentile (0-100) of domestic revenue score to qualify as
# "popular enough" for the anime-candidate list
ANIME_CANDIDATE_MIN_PERCENTILE = 60.0

# A title is considered "low global potential" when its global_potential_score
# is below this threshold (if the field exists on the model)
OVERSEAS_LOW_GLOBAL_THRESHOLD = 40.0

# A title is considered "high domestic" when its domestic revenue percentile
# is above this threshold
OVERSEAS_HIGH_DOMESTIC_THRESHOLD = 60.0

# Historical anime-lift multipliers by genre.  These are conservative
# estimates derived from market research; the predictor uses them when real
# historical data for a genre is sparse.
DEFAULT_GENRE_ANIME_MULTIPLIER: dict[str, float] = {
    "shonen": 3.5,
    "shojo": 2.8,
    "seinen": 2.2,
    "josei": 2.0,
    "isekai": 3.8,
    "action": 3.2,
    "fantasy": 3.0,
    "romance": 2.6,
    "sports": 2.5,
    "horror": 2.0,
    "mystery": 2.1,
    "sci_fi": 2.3,
    "comedy": 2.4,
    "slice_of_life": 2.0,
    "bl": 2.7,
    "gl": 2.5,
    "kodomo": 2.0,
    "other": 2.0,
}

# Untapped region definitions: region label → weight (used when estimating
# overseas potential).  Weights reflect rough addressable-market sizes.
OVERSEAS_REGIONS: dict[str, float] = {
    "North America": 0.30,
    "Europe": 0.25,
    "Southeast Asia": 0.20,
    "Latin America": 0.15,
    "Other": 0.10,
}


class HitPredictor:
    """Generate ranked hit-prediction lists for manga titles.

    Attributes:
        db: SQLAlchemy session used for all database queries.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_predictions(self, publisher_id: int | None = None) -> list[dict]:
        """Generate hit predictions across all three detection types.

        Each returned dictionary conforms to the ``PredictionEntry`` schema:
            - title_id
            - title_name (may be None for competitor titles)
            - anonymous_label (set when title_name is hidden)
            - is_own_title (True when publisher_id matches the title's owner)
            - prediction_type: "anime_linked" | "anime_candidate" | "overseas_expansion"
            - predicted_growth: expected percentage uplift (fractional, e.g. 1.5 = 150 %)
            - confidence: float in [0, 1]
            - factors: list of human-readable explanation strings

        Args:
            publisher_id: When provided, ``is_own_title`` flags are set
                          correctly and competitor titles are anonymised.

        Returns:
            Up to 20 predictions sorted by ``predicted_growth`` descending.
        """
        predictions: list[dict] = []

        try:
            predictions.extend(self._detect_anime_linked_growth(publisher_id))
        except Exception:
            logger.exception("Error in _detect_anime_linked_growth")

        try:
            predictions.extend(self._detect_anime_candidates(publisher_id))
        except Exception:
            logger.exception("Error in _detect_anime_candidates")

        try:
            predictions.extend(self._detect_overseas_expansion(publisher_id))
        except Exception:
            logger.exception("Error in _detect_overseas_expansion")

        # De-duplicate by (title_id, prediction_type); keep highest predicted_growth
        seen: dict[tuple[int, str], dict] = {}
        for pred in predictions:
            key = (pred["title_id"], pred["prediction_type"])
            if key not in seen or pred["predicted_growth"] > seen[key]["predicted_growth"]:
                seen[key] = pred

        unique = list(seen.values())
        unique.sort(key=lambda x: x["predicted_growth"], reverse=True)
        return unique[:20]

    # ------------------------------------------------------------------
    # Strategy 1: Anime-Linked Growth
    # ------------------------------------------------------------------

    def _detect_anime_linked_growth(
        self, publisher_id: int | None = None
    ) -> list[dict]:
        """Detect titles experiencing measurable sales uplift after anime premiere.

        Detection logic:
        1. Find all titles where ``has_anime=True`` and ``anime_start_date``
           is within the last 6 months.
        2. For each qualifying title, compare total revenue in the
           ``[anime_start_date - 90d, anime_start_date]`` window against
           ``[anime_start_date, today]``.
        3. Keep titles where the post-anime growth rate exceeds
           ``ANIME_GROWTH_THRESHOLD`` (50 %).

        Returns:
            List of prediction dicts with ``prediction_type="anime_linked"``.
        """
        if Title is None or SalesData is None:
            logger.debug("Models unavailable for anime_linked_growth detection")
            return []

        today = date.today()
        six_months_ago = today - timedelta(days=180)

        # Fetch recently-airing anime titles
        try:
            rows = self.db.execute(
                select(
                    Title.id,
                    Title.name,
                    Title.publisher_id,
                    Title.genre,
                    Title.anime_start_date,
                ).where(
                    Title.has_anime.is_(True),
                    Title.anime_start_date >= six_months_ago,
                    Title.anime_start_date <= today,
                )
            ).all()
        except Exception:
            logger.exception("Failed to query anime titles")
            return []

        results: list[dict] = []

        for row in rows:
            title_id: int = row.id
            anime_start: date = (
                row.anime_start_date
                if isinstance(row.anime_start_date, date)
                else row.anime_start_date
            )

            # Pre-anime window: 90 days before premiere
            pre_start = anime_start - timedelta(days=90)

            try:
                pre_revenue = self._sum_revenue(title_id, pre_start, anime_start)
                post_revenue = self._sum_revenue(title_id, anime_start, today)
            except Exception:
                continue

            gr = growth_rate(post_revenue, pre_revenue)

            if gr < ANIME_GROWTH_THRESHOLD:
                continue

            # Scale confidence by magnitude of growth (sigmoid-capped)
            confidence = float(
                sigmoid_normalize(gr, center=ANIME_GROWTH_THRESHOLD, scale=0.5)
            )

            days_airing = max((today - anime_start).days, 1)
            factors = [
                f"Anime premiered {days_airing} days ago",
                f"Post-anime revenue growth: {gr * 100:.1f}%",
                f"Pre-anime revenue (90 d): {pre_revenue:,.0f}",
                f"Post-anime revenue: {post_revenue:,.0f}",
            ]

            results.append(
                self._build_prediction(
                    title_id=title_id,
                    title_name=row.name,
                    title_publisher_id=row.publisher_id,
                    requesting_publisher_id=publisher_id,
                    prediction_type="anime_linked",
                    predicted_growth=gr,
                    confidence=confidence,
                    factors=factors,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Strategy 2: Anime Candidates
    # ------------------------------------------------------------------

    def _detect_anime_candidates(
        self, publisher_id: int | None = None
    ) -> list[dict]:
        """Identify popular non-anime titles with high anime-adaptation potential.

        Detection logic:
        1. Find titles where ``has_anime=False`` and the title is still active.
        2. Compute each title's 12-month revenue percentile among all titles.
        3. Keep titles above ``ANIME_CANDIDATE_MIN_PERCENTILE``.
        4. Estimate potential growth using the genre's anime-lift multiplier,
           calibrated from historical data where possible.

        Returns:
            List of prediction dicts with ``prediction_type="anime_candidate"``.
        """
        if Title is None or SalesData is None:
            logger.debug("Models unavailable for anime_candidate detection")
            return []

        today = date.today()
        cutoff_12m = today - timedelta(days=365)

        # Fetch candidate titles (no anime, still active)
        try:
            candidate_rows = self.db.execute(
                select(Title.id, Title.name, Title.publisher_id, Title.genre).where(
                    Title.has_anime.is_(False),
                    Title.is_active.is_(True),
                )
            ).all()
        except Exception:
            logger.exception("Failed to query anime candidate titles")
            return []

        if not candidate_rows:
            return []

        # Fetch 12-month revenue for every title (to build the percentile base)
        try:
            all_rev_rows = self.db.execute(
                select(
                    SalesData.title_id,
                    func.sum(SalesData.revenue).label("total_revenue"),
                )
                .where(SalesData.period_start >= cutoff_12m)
                .group_by(SalesData.title_id)
            ).all()
        except Exception:
            logger.exception("Failed to query revenues for anime candidates")
            return []

        revenue_map: dict[int, float] = {
            r.title_id: float(r.total_revenue or 0.0) for r in all_rev_rows
        }
        all_revenues = list(revenue_map.values()) if revenue_map else [0.0]

        # Compute per-genre historical anime multipliers from existing data
        genre_multiplier = self._compute_genre_anime_multipliers()

        results: list[dict] = []

        for row in candidate_rows:
            title_id: int = row.id
            title_revenue = revenue_map.get(title_id, 0.0)

            # Compute popularity percentile
            from app.scoring.utils import percentile_rank
            popularity_pct = percentile_rank(title_revenue, all_revenues)

            if popularity_pct < ANIME_CANDIDATE_MIN_PERCENTILE:
                continue

            genre_str = str(row.genre.value if hasattr(row.genre, "value") else row.genre or "other")
            multiplier = genre_multiplier.get(
                genre_str, DEFAULT_GENRE_ANIME_MULTIPLIER.get(genre_str, 2.0)
            )

            # popularity_pct is in [0,100]; normalise to [0,1]
            popularity_norm = popularity_pct / 100.0
            # predicted_growth = (multiplier - 1) scaled by popularity
            predicted_growth = (multiplier - 1.0) * popularity_norm

            confidence = float(
                sigmoid_normalize(popularity_pct, center=70.0, scale=15.0)
            )

            factors = [
                f"No anime adaptation yet",
                f"12-month revenue popularity: {popularity_pct:.1f}th percentile",
                f"Genre ({genre_str}) anime lift multiplier: {multiplier:.1f}x",
                f"Estimated post-anime growth: {predicted_growth * 100:.0f}%",
            ]

            results.append(
                self._build_prediction(
                    title_id=title_id,
                    title_name=row.name,
                    title_publisher_id=row.publisher_id,
                    requesting_publisher_id=publisher_id,
                    prediction_type="anime_candidate",
                    predicted_growth=predicted_growth,
                    confidence=confidence,
                    factors=factors,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Strategy 3: Overseas Expansion
    # ------------------------------------------------------------------

    def _detect_overseas_expansion(
        self, publisher_id: int | None = None
    ) -> list[dict]:
        """Find titles with strong domestic performance but low global penetration.

        Detection logic:
        1. Find titles where domestic revenue percentile is high
           (>= ``OVERSEAS_HIGH_DOMESTIC_THRESHOLD``) but global_potential_score
           is low (< ``OVERSEAS_LOW_GLOBAL_THRESHOLD``) — or simply absent.
        2. Estimate untapped international opportunity as a fraction of
           domestic revenue, weighted by the target region's market-size factor.

        Returns:
            List of prediction dicts with ``prediction_type="overseas_expansion"``.
        """
        if Title is None or SalesData is None:
            logger.debug("Models unavailable for overseas_expansion detection")
            return []

        today = date.today()
        cutoff_12m = today - timedelta(days=365)

        # Fetch all active titles
        try:
            title_rows = self.db.execute(
                select(
                    Title.id,
                    Title.name,
                    Title.publisher_id,
                    Title.genre,
                    # global_potential_score may not exist on older schema versions
                ).where(Title.is_active.is_(True))
            ).all()
        except Exception:
            logger.exception("Failed to query titles for overseas expansion")
            return []

        if not title_rows:
            return []

        # Per-title 12-month domestic revenue
        try:
            rev_rows = self.db.execute(
                select(
                    SalesData.title_id,
                    func.sum(SalesData.revenue).label("total_revenue"),
                )
                .where(SalesData.period_start >= cutoff_12m)
                .group_by(SalesData.title_id)
            ).all()
        except Exception:
            logger.exception("Failed to query revenues for overseas expansion")
            return []

        revenue_map: dict[int, float] = {
            r.title_id: float(r.total_revenue or 0.0) for r in rev_rows
        }
        all_revenues = list(revenue_map.values()) if revenue_map else [0.0]

        from app.scoring.utils import percentile_rank

        results: list[dict] = []

        for row in title_rows:
            title_id: int = row.id
            domestic_revenue = revenue_map.get(title_id, 0.0)
            domestic_pct = percentile_rank(domestic_revenue, all_revenues)

            if domestic_pct < OVERSEAS_HIGH_DOMESTIC_THRESHOLD:
                continue

            # Try to read global_potential_score from the row if the column exists
            global_potential: float | None = None
            try:
                global_potential = float(row.global_potential_score)  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                global_potential = None  # column absent or NULL → treat as untapped

            # If a global potential score exists and is already high, skip
            if global_potential is not None and global_potential >= OVERSEAS_LOW_GLOBAL_THRESHOLD:
                continue

            # Estimate potential: fraction of domestic revenue that could be
            # realised internationally, scaled by a conservative 30 % capture rate
            international_opportunity = domestic_revenue * 0.30
            # Predicted growth = international_opportunity / domestic_revenue
            predicted_growth = (
                international_opportunity / domestic_revenue if domestic_revenue > 0 else 0.0
            )

            confidence = float(
                sigmoid_normalize(domestic_pct, center=75.0, scale=10.0)
            )

            # Identify highest-potential untapped regions
            untapped_regions = list(OVERSEAS_REGIONS.keys())

            genre_str = str(row.genre.value if hasattr(row.genre, "value") else row.genre or "other")
            global_score_str = (
                f"{global_potential:.1f}" if global_potential is not None else "N/A"
            )

            factors = [
                f"Domestic revenue: {domestic_pct:.1f}th percentile",
                f"Current global potential score: {global_score_str}",
                f"Estimated international opportunity: {international_opportunity:,.0f}",
                f"Top untapped regions: {', '.join(untapped_regions[:3])}",
                f"Genre: {genre_str}",
            ]

            results.append(
                self._build_prediction(
                    title_id=title_id,
                    title_name=row.name,
                    title_publisher_id=row.publisher_id,
                    requesting_publisher_id=publisher_id,
                    prediction_type="overseas_expansion",
                    predicted_growth=predicted_growth,
                    confidence=confidence,
                    factors=factors,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sum_revenue(self, title_id: int, from_date: date, to_date: date) -> float:
        """Return the total revenue for a title within a half-open date range.

        Args:
            title_id:  Target title primary key.
            from_date: Start of range (inclusive).
            to_date:   End of range (exclusive).

        Returns:
            Total revenue as a float.  Returns 0.0 when no rows are found.
        """
        result = self.db.execute(
            select(func.coalesce(func.sum(SalesData.revenue), 0.0)).where(
                SalesData.title_id == title_id,
                SalesData.period_start >= from_date,
                SalesData.period_start < to_date,
            )
        ).scalar()
        return float(result or 0.0)

    def _compute_genre_anime_multipliers(self) -> dict[str, float]:
        """Derive anime-lift multipliers from historical SalesData.

        For each genre that has at least one title with a known anime start
        date, compute the median before/after revenue ratio across titles in
        that genre.  Falls back to ``DEFAULT_GENRE_ANIME_MULTIPLIER`` for
        genres with insufficient history.

        Returns:
            Mapping of genre string → estimated lift multiplier.
        """
        if Title is None or SalesData is None:
            return {}

        today = date.today()
        result: dict[str, list[float]] = {}

        try:
            anime_titles = self.db.execute(
                select(
                    Title.id,
                    Title.genre,
                    Title.anime_start_date,
                ).where(
                    Title.has_anime.is_(True),
                    Title.anime_start_date.is_not(None),
                    # Only use titles where we have both pre- and post-data
                    Title.anime_start_date >= (today - timedelta(days=730)),
                    Title.anime_start_date <= (today - timedelta(days=90)),
                )
            ).all()
        except Exception:
            logger.debug("Could not query anime titles for multiplier calculation")
            return {}

        for row in anime_titles:
            anime_start: date = (
                row.anime_start_date
                if isinstance(row.anime_start_date, date)
                else row.anime_start_date
            )
            pre_start = anime_start - timedelta(days=90)

            try:
                pre_rev = self._sum_revenue(row.id, pre_start, anime_start)
                post_rev = self._sum_revenue(row.id, anime_start, today)
            except Exception:
                continue

            if pre_rev <= 0:
                continue

            multiplier = post_rev / pre_rev
            genre_str = str(
                row.genre.value if hasattr(row.genre, "value") else row.genre or "other"
            )
            result.setdefault(genre_str, []).append(multiplier)

        return {
            genre: float(np.median(vals))
            for genre, vals in result.items()
            if vals
        }

    def _build_prediction(
        self,
        *,
        title_id: int,
        title_name: str,
        title_publisher_id: int | None,
        requesting_publisher_id: int | None,
        prediction_type: str,
        predicted_growth: float,
        confidence: float,
        factors: list[str],
    ) -> dict[str, Any]:
        """Construct a normalised prediction dictionary.

        When ``requesting_publisher_id`` is provided and does NOT match
        ``title_publisher_id``, the title name is replaced with an
        anonymised label and ``is_own_title`` is set to ``False``.

        Args:
            title_id:                  Primary key of the title.
            title_name:                Human-readable name of the title.
            title_publisher_id:        Publisher that owns the title.
            requesting_publisher_id:   Publisher making the request (or None).
            prediction_type:           One of the three strategy type strings.
            predicted_growth:          Estimated fractional revenue uplift.
            confidence:                Float in [0, 1] representing model confidence.
            factors:                   Human-readable explanation bullet points.

        Returns:
            A dict conforming to the ``PredictionEntry`` Pydantic schema.
        """
        is_own = (
            requesting_publisher_id is None
            or title_publisher_id == requesting_publisher_id
        )

        return {
            "title_id": title_id,
            "title_name": title_name if is_own else None,
            "anonymous_label": None if is_own else f"Title #{title_id % 1000:03d}",
            "is_own_title": is_own,
            "prediction_type": prediction_type,
            "predicted_growth": round(float(predicted_growth), 4),
            "confidence": round(float(np.clip(confidence, 0.0, 1.0)), 4),
            "factors": factors,
        }
