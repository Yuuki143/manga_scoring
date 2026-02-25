"""Business logic layer for intelligence alerts.

Provides tier-gated alert retrieval and the detection routines that
create new alerts when market signals are identified.
"""

import logging
import math
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertRequiredTier, AlertSeverity, AlertType
from app.models.publisher import PublisherTier
from app.models.sales_data import SalesData
from app.models.title import Title

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier access configuration
# ---------------------------------------------------------------------------

# Maps each tier to the set of alert types that tier can see
_TIER_ALLOWED_TYPES: dict[str, set[AlertType]] = {
    PublisherTier.BASIC: {
        AlertType.BREAKOUT,
    },
    PublisherTier.PRO: {
        AlertType.BREAKOUT,
        AlertType.GENRE_TREND,
        AlertType.ANIME_IMPACT,
    },
    PublisherTier.ENTERPRISE: {
        AlertType.BREAKOUT,
        AlertType.GENRE_TREND,
        AlertType.ANIME_IMPACT,
        AlertType.OVERSEAS_DEMAND,
        AlertType.COMPETITOR_MOVEMENT,
    },
}

# Maps each AlertType to the minimum tier required (stored on the model row)
_ALERT_TYPE_TO_REQUIRED_TIER: dict[AlertType, AlertRequiredTier] = {
    AlertType.BREAKOUT: AlertRequiredTier.BASIC,
    AlertType.GENRE_TREND: AlertRequiredTier.PRO,
    AlertType.ANIME_IMPACT: AlertRequiredTier.PRO,
    AlertType.OVERSEAS_DEMAND: AlertRequiredTier.ENTERPRISE,
    AlertType.COMPETITOR_MOVEMENT: AlertRequiredTier.ENTERPRISE,
}

# Thresholds for alert detection
_BREAKOUT_SCORE_INCREASE_PCT = 20.0   # >20% score increase in 30 days
_GENRE_TREND_GROWTH_STDDEV = 2.0      # Revenue growth > 2 standard deviations from genre mean


class AlertService:
    """Retrieve and generate intelligence alerts for publishers.

    Args:
        db: An active SQLAlchemy :class:`~sqlalchemy.orm.Session`.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------------------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------------------------

    def get_alerts(
        self,
        publisher_id: int,
        tier: str,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """Return paginated alerts for *publisher_id*, filtered by *tier* access.

        Tier visibility rules:

        * ``BASIC``  – only ``BREAKOUT`` alerts
        * ``PRO``    – ``BREAKOUT``, ``GENRE_TREND``, ``ANIME_IMPACT``
        * ``ENTERPRISE`` – all alert types

        Args:
            publisher_id: The publisher whose alerts are requested.
            tier: Publisher subscription tier (``"BASIC"``, ``"PRO"``,
                ``"ENTERPRISE"``).
            page: 1-based page index.
            per_page: Maximum number of alerts per page.

        Returns:
            A dict with ``total``, ``page``, ``per_page``, ``pages``, and
            ``alerts`` (list of :class:`~app.models.alert.Alert` instances).
        """
        tier_upper = tier.upper()
        allowed_types = _TIER_ALLOWED_TYPES.get(tier_upper, {AlertType.BREAKOUT})

        base_query = (
            self.db.query(Alert)
            .filter(
                Alert.publisher_id == publisher_id,
                Alert.alert_type.in_(list(allowed_types)),
            )
            .order_by(Alert.created_at.desc())
        )

        total = base_query.count()
        offset = (max(page, 1) - 1) * per_page
        alerts = base_query.offset(offset).limit(per_page).all()
        pages = max(1, math.ceil(total / per_page)) if total > 0 else 1

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "alerts": alerts,
        }

    def get_alert(self, alert_id: int, publisher_id: int) -> Alert | None:
        """Return a single alert if it belongs to *publisher_id*.

        Args:
            alert_id: Primary key of the alert.
            publisher_id: Must match the alert's ``publisher_id``.

        Returns:
            The :class:`~app.models.alert.Alert` instance or ``None``.
        """
        return (
            self.db.query(Alert)
            .filter(Alert.id == alert_id, Alert.publisher_id == publisher_id)
            .first()
        )

    def mark_read(self, alert: Alert) -> Alert:
        """Mark an alert as read.

        Args:
            alert: The alert instance to mark (must already be in session).

        Returns:
            The updated alert instance.
        """
        alert.is_read = True
        self.db.commit()
        self.db.refresh(alert)
        return alert

    # ---------------------------------------------------------------------------
    # Alert detection: breakout titles
    # ---------------------------------------------------------------------------

    def create_breakout_alerts(self) -> int:
        """Detect titles whose revenue increased >20 % in the last 30 days and
        create ``BREAKOUT`` alerts for their publishers.

        A breakout is identified by comparing total revenue across all platforms
        for the period [now-60d, now-30d] against [now-30d, now]. Only active
        titles with data in both windows are considered.

        Returns:
            Number of new alerts created.
        """
        today = date.today()
        recent_start = today - timedelta(days=30)
        prior_start = today - timedelta(days=60)

        # Aggregate revenue per title for the two windows
        # Window 1: prior 30-day period
        prior_revenue: dict[int, float] = {
            row.title_id: float(row.total_revenue)
            for row in (
                self.db.query(
                    SalesData.title_id,
                    func.sum(SalesData.revenue).label("total_revenue"),
                )
                .filter(
                    SalesData.period_start >= prior_start,
                    SalesData.period_start < recent_start,
                )
                .group_by(SalesData.title_id)
                .all()
            )
        }

        # Window 2: recent 30-day period
        recent_revenue: dict[int, float] = {
            row.title_id: float(row.total_revenue)
            for row in (
                self.db.query(
                    SalesData.title_id,
                    func.sum(SalesData.revenue).label("total_revenue"),
                )
                .filter(
                    SalesData.period_start >= recent_start,
                    SalesData.period_start <= today,
                )
                .group_by(SalesData.title_id)
                .all()
            )
        }

        # Find titles present in both windows with >20% increase
        breakout_title_ids = [
            title_id
            for title_id, recent in recent_revenue.items()
            if title_id in prior_revenue
            and prior_revenue[title_id] > 0
            and (recent - prior_revenue[title_id]) / prior_revenue[title_id] * 100
            > _BREAKOUT_SCORE_INCREASE_PCT
        ]

        if not breakout_title_ids:
            return 0

        # Load titles
        titles: list[Title] = (
            self.db.query(Title)
            .filter(Title.id.in_(breakout_title_ids), Title.is_active.is_(True))
            .all()
        )

        created_count = 0
        for title in titles:
            prior = prior_revenue.get(title.id, 0.0)
            recent = recent_revenue.get(title.id, 0.0)
            if prior <= 0:
                continue
            increase_pct = (recent - prior) / prior * 100.0

            # Avoid duplicate alerts: skip if an unread BREAKOUT alert for this
            # title was already created in the last 30 days
            existing = (
                self.db.query(Alert)
                .filter(
                    Alert.title_id == title.id,
                    Alert.publisher_id == title.publisher_id,
                    Alert.alert_type == AlertType.BREAKOUT,
                    Alert.created_at >= func.now() - timedelta(days=30),
                )
                .first()
            )
            if existing is not None:
                continue

            severity = (
                AlertSeverity.CRITICAL
                if increase_pct >= 100
                else AlertSeverity.WARNING
                if increase_pct >= 50
                else AlertSeverity.INFO
            )

            alert = Alert(
                publisher_id=title.publisher_id,
                title_id=title.id,
                alert_type=AlertType.BREAKOUT,
                severity=severity,
                required_tier=_ALERT_TYPE_TO_REQUIRED_TIER[AlertType.BREAKOUT],
                message=(
                    f"'{title.name}' has shown a {increase_pct:.1f}% revenue increase "
                    f"over the past 30 days (¥{prior:,.0f} → ¥{recent:,.0f})."
                ),
                data={
                    "title_id": title.id,
                    "title_name": title.name,
                    "prior_revenue": round(prior, 2),
                    "recent_revenue": round(recent, 2),
                    "increase_pct": round(increase_pct, 2),
                    "window_days": 30,
                },
            )
            self.db.add(alert)
            created_count += 1

        if created_count:
            self.db.commit()
            logger.info("Created %d BREAKOUT alert(s).", created_count)

        return created_count

    # ---------------------------------------------------------------------------
    # Alert detection: genre trends
    # ---------------------------------------------------------------------------

    def create_genre_trend_alerts(self) -> int:
        """Detect genres whose revenue growth rate has changed significantly and
        create ``GENRE_TREND`` alerts for all PRO+ publishers.

        A genre trend is flagged when the genre's most recent 30-day revenue
        growth rate deviates by more than ``_GENRE_TREND_GROWTH_STDDEV``
        standard deviations from the genre's 12-month mean growth rate.

        Returns:
            Number of new alerts created.
        """
        today = date.today()

        # Collect monthly revenue totals per genre over the last 13 months
        # to compute 12 month-over-month growth rates
        genre_monthly: dict[str, dict[date, float]] = {}

        for month_offset in range(13):
            period_start = date(
                today.year,
                today.month,
                1,
            ) - timedelta(days=30 * month_offset)
            period_start = date(period_start.year, period_start.month, 1)

            rows = (
                self.db.query(
                    Title.genre,
                    func.sum(SalesData.revenue).label("total_revenue"),
                )
                .join(SalesData, SalesData.title_id == Title.id)
                .filter(
                    SalesData.period_start >= period_start,
                    SalesData.period_start
                    < date(
                        period_start.year + (period_start.month // 12),
                        (period_start.month % 12) + 1,
                        1,
                    ),
                )
                .group_by(Title.genre)
                .all()
            )

            for row in rows:
                genre_key = str(row.genre)
                if genre_key not in genre_monthly:
                    genre_monthly[genre_key] = {}
                genre_monthly[genre_key][period_start] = float(row.total_revenue)

        import statistics

        created_count = 0

        for genre_key, monthly_data in genre_monthly.items():
            # Need at least 3 data points for meaningful statistics
            sorted_dates = sorted(monthly_data.keys())
            if len(sorted_dates) < 3:
                continue

            # Compute month-over-month growth rates
            growth_rates: list[float] = []
            for i in range(1, len(sorted_dates)):
                prev = monthly_data[sorted_dates[i - 1]]
                curr = monthly_data[sorted_dates[i]]
                if prev > 0:
                    growth_rates.append((curr - prev) / prev * 100.0)

            if len(growth_rates) < 2:
                continue

            mean_growth = statistics.mean(growth_rates)
            stdev_growth = statistics.stdev(growth_rates) if len(growth_rates) > 1 else 0.0

            if stdev_growth == 0:
                continue

            # The most recent growth rate is the last element
            latest_growth = growth_rates[-1]
            z_score = (latest_growth - mean_growth) / stdev_growth

            if abs(z_score) < _GENRE_TREND_GROWTH_STDDEV:
                continue

            direction = "surge" if z_score > 0 else "decline"
            severity = (
                AlertSeverity.CRITICAL
                if abs(z_score) >= 3.0
                else AlertSeverity.WARNING
                if abs(z_score) >= 2.5
                else AlertSeverity.INFO
            )

            # Create one alert per PRO+ publisher
            from app.models.publisher import Publisher

            publishers = (
                self.db.query(Publisher)
                .filter(
                    Publisher.is_active.is_(True),
                    Publisher.tier.in_([PublisherTier.PRO, PublisherTier.ENTERPRISE]),
                )
                .all()
            )

            for publisher in publishers:
                # Dedup: skip if an unread GENRE_TREND alert for this genre
                # was created in the last 30 days for this publisher
                existing = (
                    self.db.query(Alert)
                    .filter(
                        Alert.publisher_id == publisher.id,
                        Alert.alert_type == AlertType.GENRE_TREND,
                        Alert.data["genre"].as_string() == genre_key,
                        Alert.created_at >= func.now() - timedelta(days=30),
                    )
                    .first()
                )
                if existing is not None:
                    continue

                alert = Alert(
                    publisher_id=publisher.id,
                    title_id=None,
                    alert_type=AlertType.GENRE_TREND,
                    severity=severity,
                    required_tier=_ALERT_TYPE_TO_REQUIRED_TIER[AlertType.GENRE_TREND],
                    message=(
                        f"The {genre_key} genre is experiencing a significant revenue "
                        f"{direction} (z-score: {z_score:.2f}, latest growth: "
                        f"{latest_growth:.1f}%, mean: {mean_growth:.1f}%)."
                    ),
                    data={
                        "genre": genre_key,
                        "direction": direction,
                        "z_score": round(z_score, 4),
                        "latest_growth_pct": round(latest_growth, 2),
                        "mean_growth_pct": round(mean_growth, 2),
                        "stdev_growth_pct": round(stdev_growth, 2),
                    },
                )
                self.db.add(alert)
                created_count += 1

        if created_count:
            self.db.commit()
            logger.info("Created %d GENRE_TREND alert(s).", created_count)

        return created_count
