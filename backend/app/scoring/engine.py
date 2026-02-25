"""
MMIP 5-Axis Scoring Engine

Computes composite scores for manga titles based on:
- Revenue Scale (25%): Percentile rank among all titles
- Growth Trend (25%): 3/6/12-month weighted growth rates
- Platform Distribution (20%): Multi-platform presence + Gini coefficient
- Sales Stability (15%): Inverse coefficient of variation
- Ranking Frequency (15%): Ranking appearances + best position

The engine is stateless between calls; every call to ``calculate_title_score``
issues fresh queries so that it reflects the latest ingested data.

Typical usage::

    from app.database import SessionLocal
    from app.scoring.engine import ScoringEngine

    with SessionLocal() as db:
        engine = ScoringEngine(db)
        result = engine.calculate_title_score(title_id=42)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.scoring.utils import (
    coefficient_of_variation,
    gini_coefficient,
    percentile_rank,
    sigmoid_normalize,
    growth_rate,
)

# ---------------------------------------------------------------------------
# Lazy model imports
# The ORM models for Title, SalesData, PlatformData and RankingData live in
# app.models but are only imported at the module level to avoid circular
# imports.  We guard each import and degrade gracefully when the tables have
# not yet been created (e.g. during early migrations).
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

try:
    from app.models.ranking_data import RankingData  # type: ignore[import]
except ImportError:  # pragma: no cover
    RankingData = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# How many platforms are considered "well distributed"
MAX_EXPECTED_PLATFORMS = 10

# Maximum number of ranking appearances considered "perfect"
MAX_RANKING_APPEARANCES = 100

# Growth rate used as the sigmoid centre point (0 % = break-even)
GROWTH_SIGMOID_CENTER = 0.0
# Scale parameter: a 50-pp growth maps roughly to sigmoid output ~0.85
GROWTH_SIGMOID_SCALE = 0.30

# Confidence thresholds
CONFIDENCE_A_THRESHOLD = 5   # all 5 axes have data
CONFIDENCE_B_THRESHOLD = 3   # 3–4 axes


class ScoringEngine:
    """Compute 5-axis composite scores for individual manga titles.

    Attributes:
        WEIGHTS: Mapping of axis name → fractional weight summing to 1.0.
        db: SQLAlchemy session used for all database queries.
    """

    WEIGHTS: dict[str, float] = {
        "revenue": 0.25,
        "growth": 0.25,
        "platform_distribution": 0.20,
        "stability": 0.15,
        "ranking_frequency": 0.15,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def calculate_title_score(self, title_id: int) -> dict:
        """Calculate all 5 axis scores and an overall composite score.

        Args:
            title_id: Primary key of the manga title to score.

        Returns:
            A dictionary with keys:
                overall_score                – Weighted composite (0–100).
                revenue_score                – Percentile rank score (0–100).
                growth_score                 – Weighted growth score (0–100).
                platform_distribution_score  – Platform breadth score (0–100).
                stability_score              – Stability score (0–100).
                ranking_frequency_score      – Ranking frequency score (0–100).
                confidence_rating            – "A", "B", or "C".
                genre_percentile             – Score relative to same genre (0–100).
        """
        revenue_score = self._calculate_revenue_score(title_id)
        growth_score = self._calculate_growth_score(title_id)
        platform_score = self._calculate_platform_distribution_score(title_id)
        stability_score = self._calculate_stability_score(title_id)
        ranking_score = self._calculate_ranking_frequency_score(title_id)

        overall = (
            self.WEIGHTS["revenue"] * revenue_score
            + self.WEIGHTS["growth"] * growth_score
            + self.WEIGHTS["platform_distribution"] * platform_score
            + self.WEIGHTS["stability"] * stability_score
            + self.WEIGHTS["ranking_frequency"] * ranking_score
        )

        confidence = self._calculate_confidence(title_id)
        genre_pct = self._calculate_genre_percentile(title_id, overall)

        return {
            "overall_score": round(overall, 2),
            "revenue_score": round(revenue_score, 2),
            "growth_score": round(growth_score, 2),
            "platform_distribution_score": round(platform_score, 2),
            "stability_score": round(stability_score, 2),
            "ranking_frequency_score": round(ranking_score, 2),
            "confidence_rating": confidence,
            "genre_percentile": round(genre_pct, 2),
        }

    # ------------------------------------------------------------------
    # Axis 1 – Revenue Scale (25 %)
    # ------------------------------------------------------------------

    def _calculate_revenue_score(self, title_id: int) -> float:
        """Percentile rank of this title's 12-month revenue among all titles.

        Steps:
        1. Sum revenue for the target title over the last 12 months.
        2. Sum revenue for every title over the same window.
        3. Return the ordinal percentile of the target title.

        Returns:
            Score in [0.0, 100.0].  Returns 0.0 when no sales data exists.
        """
        if SalesData is None:
            logger.debug("SalesData model unavailable; revenue_score=0")
            return 0.0

        cutoff = date.today() - timedelta(days=365)

        try:
            # Revenue for the target title
            title_revenue_row = self.db.execute(
                select(func.coalesce(func.sum(SalesData.revenue), 0.0)).where(
                    SalesData.title_id == title_id,
                    SalesData.period_start >= cutoff,
                )
            ).scalar()
            title_revenue = float(title_revenue_row or 0.0)

            # Revenue for each title (one row per title_id)
            rows = self.db.execute(
                select(
                    SalesData.title_id,
                    func.sum(SalesData.revenue).label("total_revenue"),
                )
                .where(SalesData.period_start >= cutoff)
                .group_by(SalesData.title_id)
            ).all()

            if not rows:
                return 0.0

            all_revenues = [float(r.total_revenue or 0.0) for r in rows]
            return percentile_rank(title_revenue, all_revenues)

        except Exception:
            logger.exception("Error calculating revenue_score for title %d", title_id)
            return 0.0

    # ------------------------------------------------------------------
    # Axis 2 – Growth Trend (25 %)
    # ------------------------------------------------------------------

    def _calculate_growth_score(self, title_id: int) -> float:
        """Weighted composite of 3/6/12-month sales growth and engagement growth.

        Sales growth weights: 3 m=0.5, 6 m=0.3, 12 m=0.2.
        Engagement growth adds a 20 % bonus on top of the sales component.
        The combined weighted growth rate is mapped to [0, 100] via a
        sigmoid centred at 0 % growth with a scale of 0.30.

        Returns:
            Score in [0.0, 100.0].  Returns 50.0 (neutral) when no data.
        """
        if SalesData is None:
            logger.debug("SalesData model unavailable; growth_score=50")
            return 50.0

        today = date.today()

        try:
            # Fetch monthly revenue buckets for the last 12 months
            cutoff_12m = today - timedelta(days=365)
            rows = self.db.execute(
                select(
                    func.date_trunc("month", SalesData.period_start).label("month"),
                    func.sum(SalesData.revenue).label("revenue"),
                )
                .where(
                    SalesData.title_id == title_id,
                    SalesData.period_start >= cutoff_12m,
                )
                .group_by("month")
                .order_by("month")
            ).all()

            if not rows:
                return 50.0

            # Build a dict: month-start -> revenue
            monthly: dict[date, float] = {
                r.month.date() if hasattr(r.month, "date") else r.month: float(r.revenue or 0.0)
                for r in rows
            }
            total_revenues = list(monthly.values())
            if not total_revenues:
                return 50.0

            total_12m = sum(total_revenues)

            def _sum_months(n_months: int) -> float:
                """Sum revenue for the most recent *n_months* months."""
                boundary = today - timedelta(days=n_months * 30)
                return sum(v for k, v in monthly.items() if k >= boundary)

            def _sum_prior_months(n_months: int) -> float:
                """Sum revenue for the *n_months* prior to the recent window."""
                recent_boundary = today - timedelta(days=n_months * 30)
                prior_boundary = recent_boundary - timedelta(days=n_months * 30)
                return sum(
                    v for k, v in monthly.items()
                    if prior_boundary <= k < recent_boundary
                )

            # Sales growth rates for each window
            gr_3m = growth_rate(_sum_months(3), _sum_prior_months(3))
            gr_6m = growth_rate(_sum_months(6), _sum_prior_months(6))
            gr_12m = growth_rate(total_12m, _sum_prior_months(12))

            # Weighted sales growth (weights sum to 1.0)
            weighted_sales_growth = 0.5 * gr_3m + 0.3 * gr_6m + 0.2 * gr_12m

            # Engagement growth from PlatformData (if available)
            engagement_growth = self._get_engagement_growth(title_id)

            # Combine: sales is 80 %, engagement is 20 %
            combined_growth = 0.80 * weighted_sales_growth + 0.20 * engagement_growth

            # Sigmoid → [0, 1] → scale to [0, 100]
            normalised = sigmoid_normalize(
                combined_growth,
                center=GROWTH_SIGMOID_CENTER,
                scale=GROWTH_SIGMOID_SCALE,
            )
            return float(normalised * 100.0)

        except Exception:
            logger.exception("Error calculating growth_score for title %d", title_id)
            return 50.0

    def _get_engagement_growth(self, title_id: int) -> float:
        """Compute engagement growth rate from PlatformData.

        Compares recent 3-month average engagement against the prior
        3-month window.

        Returns:
            Fractional growth rate.  Returns 0.0 when PlatformData is
            unavailable or has no engagement records.
        """
        if PlatformData is None:
            return 0.0

        today = date.today()
        cutoff_6m = today - timedelta(days=180)
        mid = today - timedelta(days=90)

        try:
            rows = self.db.execute(
                select(
                    PlatformData.record_date,
                    PlatformData.engagement_rate,
                )
                .where(
                    PlatformData.title_id == title_id,
                    PlatformData.record_date >= cutoff_6m,
                    PlatformData.engagement_rate.is_not(None),
                )
                .order_by(PlatformData.record_date)
            ).all()

            if not rows:
                return 0.0

            recent = [float(r.engagement_rate) for r in rows if r.record_date >= mid]
            prior = [float(r.engagement_rate) for r in rows if r.record_date < mid]

            if not recent or not prior:
                return 0.0

            return growth_rate(float(np.mean(recent)), float(np.mean(prior)))

        except Exception:
            logger.debug("Could not fetch engagement data for title %d", title_id)
            return 0.0

    # ------------------------------------------------------------------
    # Axis 3 – Platform Distribution (20 %)
    # ------------------------------------------------------------------

    def _calculate_platform_distribution_score(self, title_id: int) -> float:
        """Score based on breadth and evenness of cross-platform presence.

        Formula:
            score = (platform_count_normalised * 0.6
                     + (1 - gini_coefficient) * 0.4) * 100

        Where ``platform_count_normalised`` = min(n_platforms / MAX_EXPECTED_PLATFORMS, 1).

        The Gini coefficient of revenue across platforms penalises over-
        concentration on a single platform.

        Returns:
            Score in [0.0, 100.0].  Returns 0.0 when no platform data exists.
        """
        if SalesData is None and PlatformData is None:
            logger.debug("No platform models available; platform_distribution_score=0")
            return 0.0

        try:
            platform_revenues: dict[str, float] = {}

            # Collect per-platform revenue from SalesData
            if SalesData is not None:
                cutoff = date.today() - timedelta(days=365)
                rows = self.db.execute(
                    select(
                        SalesData.platform_name,
                        func.sum(SalesData.revenue).label("revenue"),
                    )
                    .where(
                        SalesData.title_id == title_id,
                        SalesData.period_start >= cutoff,
                    )
                    .group_by(SalesData.platform_name)
                ).all()
                for r in rows:
                    if r.platform_name:
                        platform_revenues[r.platform_name] = float(r.revenue or 0.0)

            # Supplement with PlatformData platforms (may carry engagement metrics
            # even when direct revenue rows are absent)
            if PlatformData is not None:
                cutoff = date.today() - timedelta(days=365)
                prows = self.db.execute(
                    select(PlatformData.platform_name)
                    .where(
                        PlatformData.title_id == title_id,
                        PlatformData.record_date >= cutoff,
                    )
                    .distinct()
                ).scalars().all()
                for platform_name in prows:
                    if platform_name and platform_name not in platform_revenues:
                        platform_revenues[platform_name] = 0.0

            if not platform_revenues:
                return 0.0

            n_platforms = len(platform_revenues)
            platform_count_normalised = min(n_platforms / MAX_EXPECTED_PLATFORMS, 1.0)

            revenues = list(platform_revenues.values())
            gini = gini_coefficient(revenues)

            score = (platform_count_normalised * 0.6 + (1.0 - gini) * 0.4) * 100.0
            return float(np.clip(score, 0.0, 100.0))

        except Exception:
            logger.exception(
                "Error calculating platform_distribution_score for title %d", title_id
            )
            return 0.0

    # ------------------------------------------------------------------
    # Axis 4 – Sales Stability (15 %)
    # ------------------------------------------------------------------

    def _calculate_stability_score(self, title_id: int) -> float:
        """Inverse-CV score rewarding consistent monthly sales.

        Formula:
            score = max(0, (1 - CV) * 100)

        A CV of 0 (perfectly stable) → 100.
        A CV >= 1 (high volatility)  →   0.

        Returns:
            Score in [0.0, 100.0].  Returns 50.0 (neutral) when fewer than
            3 months of data are available to compute a meaningful CV.
        """
        if SalesData is None:
            logger.debug("SalesData model unavailable; stability_score=50")
            return 50.0

        cutoff = date.today() - timedelta(days=365)

        try:
            rows = self.db.execute(
                select(
                    func.date_trunc("month", SalesData.period_start).label("month"),
                    func.sum(SalesData.revenue).label("revenue"),
                )
                .where(
                    SalesData.title_id == title_id,
                    SalesData.period_start >= cutoff,
                )
                .group_by("month")
                .order_by("month")
            ).all()

            if len(rows) < 3:
                # Too few data points to be meaningful; return neutral score
                return 50.0

            monthly_revenues = [float(r.revenue or 0.0) for r in rows]
            cv = coefficient_of_variation(monthly_revenues)
            score = max(0.0, (1.0 - cv) * 100.0)
            return float(score)

        except Exception:
            logger.exception(
                "Error calculating stability_score for title %d", title_id
            )
            return 50.0

    # ------------------------------------------------------------------
    # Axis 5 – Ranking Frequency (15 %)
    # ------------------------------------------------------------------

    def _calculate_ranking_frequency_score(self, title_id: int) -> float:
        """Score based on how often the title appears in top-100 rankings.

        Formula:
            frequency_normalised = min(appearances / MAX_RANKING_APPEARANCES, 1)
            position_score       = (100 - best_rank + 1) / 100   [rank 1 → 1.0]
            score = (frequency_normalised * 0.6 + position_score * 0.4) * 100

        Returns:
            Score in [0.0, 100.0].  Returns 0.0 when no ranking data exists.
        """
        if RankingData is None:
            logger.debug("RankingData model unavailable; ranking_frequency_score=0")
            return 0.0

        try:
            # Count appearances in any platform's top-100 ranking
            appearance_row = self.db.execute(
                select(func.count()).where(
                    RankingData.title_id == title_id,
                    RankingData.rank <= 100,
                )
            ).scalar()
            appearances = int(appearance_row or 0)

            if appearances == 0:
                return 0.0

            # Best (lowest numerical) rank achieved
            best_rank_row = self.db.execute(
                select(func.min(RankingData.rank)).where(
                    RankingData.title_id == title_id,
                )
            ).scalar()
            best_rank = int(best_rank_row or 100)

            frequency_normalised = min(appearances / MAX_RANKING_APPEARANCES, 1.0)
            # Rank 1 → position_score 1.0; rank 100 → 0.01
            position_score = max(0.0, (101 - best_rank) / 100.0)

            score = (frequency_normalised * 0.6 + position_score * 0.4) * 100.0
            return float(np.clip(score, 0.0, 100.0))

        except Exception:
            logger.exception(
                "Error calculating ranking_frequency_score for title %d", title_id
            )
            return 0.0

    # ------------------------------------------------------------------
    # Confidence rating
    # ------------------------------------------------------------------

    def _calculate_confidence(self, title_id: int) -> str:
        """Classify data confidence as A, B, or C.

        Confidence reflects how many of the 5 scoring axes have real data.
        Any axis that returned a neutral/fallback score (e.g. 0.0 or 50.0
        because the model table was unavailable) is counted as missing.

        Thresholds:
            A – all 5 axes have data
            B – 3 or 4 axes have data
            C – 0, 1, or 2 axes have data

        Returns:
            One of "A", "B", "C".
        """
        axes_with_data = 0

        # Revenue: has data if title appears in SalesData at all
        if SalesData is not None:
            try:
                cutoff = date.today() - timedelta(days=365)
                count = self.db.execute(
                    select(func.count()).where(
                        SalesData.title_id == title_id,
                        SalesData.period_start >= cutoff,
                    )
                ).scalar()
                if (count or 0) > 0:
                    axes_with_data += 1
            except Exception:
                pass

        # Growth: same SalesData rows but requires at least 6 months worth
        if SalesData is not None:
            try:
                cutoff = date.today() - timedelta(days=180)
                count = self.db.execute(
                    select(func.count()).where(
                        SalesData.title_id == title_id,
                        SalesData.period_start >= cutoff,
                    )
                ).scalar()
                if (count or 0) >= 2:
                    axes_with_data += 1
            except Exception:
                pass

        # Platform distribution: either SalesData or PlatformData with >1 platform
        if SalesData is not None:
            try:
                platforms = self.db.execute(
                    select(SalesData.platform_name)
                    .where(SalesData.title_id == title_id)
                    .distinct()
                ).scalars().all()
                if len(platforms) >= 1:
                    axes_with_data += 1
            except Exception:
                pass
        elif PlatformData is not None:
            try:
                platforms = self.db.execute(
                    select(PlatformData.platform_name)
                    .where(PlatformData.title_id == title_id)
                    .distinct()
                ).scalars().all()
                if len(platforms) >= 1:
                    axes_with_data += 1
            except Exception:
                pass

        # Stability: requires at least 3 monthly revenue points
        if SalesData is not None:
            try:
                cutoff = date.today() - timedelta(days=365)
                rows = self.db.execute(
                    select(
                        func.date_trunc("month", SalesData.period_start).label("month")
                    )
                    .where(
                        SalesData.title_id == title_id,
                        SalesData.period_start >= cutoff,
                    )
                    .group_by("month")
                ).all()
                if len(rows) >= 3:
                    axes_with_data += 1
            except Exception:
                pass

        # Ranking frequency: has at least one ranking entry
        if RankingData is not None:
            try:
                count = self.db.execute(
                    select(func.count()).where(RankingData.title_id == title_id)
                ).scalar()
                if (count or 0) > 0:
                    axes_with_data += 1
            except Exception:
                pass

        if axes_with_data >= CONFIDENCE_A_THRESHOLD:
            return "A"
        elif axes_with_data >= CONFIDENCE_B_THRESHOLD:
            return "B"
        else:
            return "C"

    # ------------------------------------------------------------------
    # Genre percentile
    # ------------------------------------------------------------------

    def _calculate_genre_percentile(self, title_id: int, overall_score: float) -> float:
        """Rank this title's overall score against same-genre titles.

        Args:
            title_id:      Target title's primary key.
            overall_score: The already-computed overall composite score.

        Returns:
            Percentile rank within the genre (0–100).  Returns 0.0 when the
            Title or SalesData model is unavailable, or when the genre cannot
            be determined.
        """
        if Title is None:
            logger.debug("Title model unavailable; genre_percentile=0")
            return 0.0

        try:
            # Fetch genre of the target title
            genre_row = self.db.execute(
                select(Title.genre).where(Title.id == title_id)
            ).scalar()

            if genre_row is None:
                return 0.0

            # Fetch all titles in the same genre
            genre_title_ids = self.db.execute(
                select(Title.id).where(
                    Title.genre == genre_row,
                    Title.id != title_id,
                )
            ).scalars().all()

            if not genre_title_ids:
                return 100.0  # Only title in genre

            # Compute overall score for each peer title using the same engine
            # To avoid N+1 explosion when there are many peers, we compute
            # revenue-only scores (fast proxy) and compare ranks.
            peer_scores = []
            for peer_id in genre_title_ids:
                try:
                    peer_score = self._fast_genre_score(peer_id)
                    peer_scores.append(peer_score)
                except Exception:
                    continue

            if not peer_scores:
                return 100.0

            return percentile_rank(overall_score, peer_scores)

        except Exception:
            logger.exception(
                "Error calculating genre_percentile for title %d", title_id
            )
            return 0.0

    def _fast_genre_score(self, title_id: int) -> float:
        """Compute a lightweight proxy score for genre percentile comparison.

        Uses only the revenue axis (cheapest query) as a fast proxy to avoid
        a full 5-axis computation for every peer title in the genre.

        Returns:
            A float representing a simplified composite score.
        """
        return self._calculate_revenue_score(title_id)
