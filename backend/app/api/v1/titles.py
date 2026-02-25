"""Title intelligence endpoints for the MMIP API.

All endpoints enforce publisher isolation: the authenticated user may only
access titles that belong to their own publisher. Tier-based access control
restricts which score axes and features are exposed.

Routes
------
GET /titles/{title_id}/score     – 5-axis composite score (tier-gated axes).
GET /titles/{title_id}/trend     – 12-month time-series trend data.
GET /titles/{title_id}/affinity  – Similar titles with competitor anonymisation.
GET /titles/{title_id}/global    – Overseas market potential (Enterprise only).
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.publisher import Publisher, PublisherTier
from app.models.sales_data import SalesData
from app.models.score import TitleScore
from app.models.title import Title
from app.schemas.affinity import AffinityResponse, AffinityTitle
from app.schemas.global_potential import GlobalPotentialResponse, RegionPotential
from app.schemas.score import ScoreResponse
from app.schemas.trend import TrendDataPoint, TrendResponse
from app.scoring.engine import ScoringEngine
from app.services.title_service import TitleService

router = APIRouter()

# ---------------------------------------------------------------------------
# Tier ordering helper
# ---------------------------------------------------------------------------

_TIER_ORDER: dict[str, int] = {
    PublisherTier.BASIC: 0,
    PublisherTier.PRO: 1,
    PublisherTier.ENTERPRISE: 2,
}

# Overseas region definitions used for the global potential endpoint
_OVERSEAS_REGIONS = [
    {"region": "North America", "weight": 0.30, "market_size_indicator": "high"},
    {"region": "Europe", "weight": 0.25, "market_size_indicator": "high"},
    {"region": "Southeast Asia", "weight": 0.20, "market_size_indicator": "medium"},
    {"region": "Latin America", "weight": 0.15, "market_size_indicator": "medium"},
    {"region": "Other", "weight": 0.10, "market_size_indicator": "low"},
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_publisher(user, db: Session) -> Publisher:
    """Return the publisher associated with the authenticated user.

    Raises:
        HTTPException 404: If the publisher cannot be found or is inactive.
    """
    publisher: Publisher | None = (
        db.query(Publisher)
        .filter(Publisher.id == user.publisher_id, Publisher.is_active.is_(True))
        .first()
    )
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher account not found or inactive",
        )
    return publisher


def _resolve_title(title_id: int, publisher_id: int, db: Session) -> Title:
    """Return the title if it exists and belongs to the given publisher.

    Raises:
        HTTPException 404: If the title is not found or belongs to a different publisher.
    """
    service = TitleService(db)
    title = service.get_title(title_id, publisher_id)
    if title is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Title {title_id} not found or does not belong to your publisher",
        )
    return title


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract the client IP address from the request, respecting proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def _get_cached_score(title_id: int, db: Session) -> Optional[TitleScore]:
    """Return the most recently calculated TitleScore for a title, or None."""
    return (
        db.query(TitleScore)
        .filter(TitleScore.title_id == title_id)
        .order_by(TitleScore.calculated_at.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{title_id}/score",
    response_model=ScoreResponse,
    summary="Get the 5-axis composite score for a title",
    description=(
        "Returns the MMIP composite score for the requested title. "
        "**Basic** tier: overall score and confidence rating only. "
        "**Pro** and above: all five scoring axes plus genre percentile. "
        "**Enterprise**: additionally includes the global potential score."
    ),
)
async def get_title_score(
    title_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScoreResponse:
    """Return the composite score for *title_id*.

    Scores are computed live by the ScoringEngine when no cached snapshot
    exists. The response fields returned depend on the publisher's tier:

    * ``BASIC``      – ``overall_score``, ``confidence_rating``.
    * ``PRO``        – all five axes + ``genre_percentile``.
    * ``ENTERPRISE`` – all of the above + ``global_potential_score``.

    Args:
        title_id: Primary key of the title to score.
        request: FastAPI request object (used for IP extraction in audit log).
        current_user: Authenticated user from JWT dependency.
        db: Database session.

    Raises:
        HTTPException 404: Title not found or not owned by the user's publisher.
    """
    publisher = _get_publisher(current_user, db)
    title = _resolve_title(title_id, publisher.id, db)

    # Determine tier order for conditional field exposure
    tier_str = publisher.tier.value if hasattr(publisher.tier, "value") else str(publisher.tier)
    tier_order = _TIER_ORDER.get(tier_str.upper(), 0)
    is_pro_plus = tier_order >= _TIER_ORDER[PublisherTier.PRO]
    is_enterprise = tier_order >= _TIER_ORDER[PublisherTier.ENTERPRISE]

    # Try cached score first; fall back to live calculation
    cached: Optional[TitleScore] = _get_cached_score(title_id, db)

    if cached is not None:
        calculated_at = cached.calculated_at
        overall_score = cached.overall_score
        revenue_score = cached.revenue_score if is_pro_plus else None
        growth_score = cached.growth_score if is_pro_plus else None
        platform_distribution_score = cached.platform_distribution_score if is_pro_plus else None
        stability_score = cached.stability_score if is_pro_plus else None
        ranking_frequency_score = cached.ranking_frequency_score if is_pro_plus else None
        confidence_rating = cached.confidence_rating
        global_potential_score = cached.global_potential_score if is_enterprise else None
        genre_percentile = cached.genre_percentile if is_pro_plus else None
    else:
        # Live calculation via ScoringEngine
        engine = ScoringEngine(db)
        score_data = engine.calculate_title_score(title_id)
        calculated_at = datetime.utcnow()
        overall_score = score_data["overall_score"]
        revenue_score = score_data["revenue_score"] if is_pro_plus else None
        growth_score = score_data["growth_score"] if is_pro_plus else None
        platform_distribution_score = (
            score_data["platform_distribution_score"] if is_pro_plus else None
        )
        stability_score = score_data["stability_score"] if is_pro_plus else None
        ranking_frequency_score = (
            score_data["ranking_frequency_score"] if is_pro_plus else None
        )
        confidence_rating = score_data["confidence_rating"]
        global_potential_score = None  # Not available from live calc without extra data
        genre_percentile = score_data["genre_percentile"] if is_pro_plus else None

    log_action(
        db=db,
        action="score_view",
        resource_type="title",
        resource_id=str(title_id),
        user_id=current_user.id,
        publisher_id=publisher.id,
        ip_address=_get_client_ip(request),
        details={"tier": tier_str, "used_cache": cached is not None},
    )

    return ScoreResponse(
        title_id=title_id,
        title_name=title.name_en or title.name,
        overall_score=overall_score,
        revenue_score=revenue_score,
        growth_score=growth_score,
        platform_distribution_score=platform_distribution_score,
        stability_score=stability_score,
        ranking_frequency_score=ranking_frequency_score,
        confidence_rating=confidence_rating,
        global_potential_score=global_potential_score,
        genre_percentile=genre_percentile,
        calculated_at=calculated_at,
    )


@router.get(
    "/{title_id}/trend",
    response_model=TrendResponse,
    summary="Get time-series trend data for a title",
    description=(
        "Returns monthly aggregated sales figures and engagement data "
        "for the past 12 months. Growth rates for the 3-, 6-, and 12-month "
        "windows are also included."
    ),
)
async def get_title_trend(
    title_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrendResponse:
    """Return monthly trend data for *title_id* over the past 12 months.

    Aggregates ``SalesData`` records by calendar month, computing total
    revenue and units sold per period. Month-over-month growth rates are
    derived for the 3-, 6-, and 12-month windows.

    Args:
        title_id: Primary key of the title to analyse.
        request: FastAPI request object.
        current_user: Authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: Title not found or not owned by the user's publisher.
    """
    publisher = _get_publisher(current_user, db)
    title = _resolve_title(title_id, publisher.id, db)

    cutoff = date.today() - timedelta(days=365)

    # Aggregate monthly revenue and units sold from SalesData
    rows = (
        db.query(
            func.date_trunc("month", SalesData.period_start).label("month"),
            func.sum(SalesData.revenue).label("revenue"),
            func.sum(SalesData.units_sold).label("units_sold"),
        )
        .filter(
            SalesData.title_id == title_id,
            SalesData.period_start >= cutoff,
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    # Also pull the most recent TitleScore per month for the overall_score series
    score_rows = (
        db.query(TitleScore)
        .filter(
            TitleScore.title_id == title_id,
            TitleScore.calculated_at >= cutoff,
        )
        .order_by(TitleScore.calculated_at.asc())
        .all()
    )

    # Build a mapping month -> latest score for that month
    score_by_month: dict[date, float] = {}
    for s in score_rows:
        month_key = date(s.calculated_at.year, s.calculated_at.month, 1)
        score_by_month[month_key] = s.overall_score

    data_points: list[TrendDataPoint] = []
    for row in rows:
        # date_trunc returns a datetime; normalise to a date
        month_dt = row.month
        if hasattr(month_dt, "date"):
            month_date = month_dt.date()
        else:
            month_date = month_dt

        month_key = date(month_date.year, month_date.month, 1)
        data_points.append(
            TrendDataPoint(
                period=month_key,
                revenue=float(row.revenue) if row.revenue is not None else None,
                units_sold=int(row.units_sold) if row.units_sold is not None else None,
                overall_score=score_by_month.get(month_key),
            )
        )

    # Compute growth rates
    def _sum_recent(months: int) -> float:
        boundary = date.today() - timedelta(days=months * 30)
        return sum(
            float(dp.revenue or 0.0) for dp in data_points if dp.period >= boundary
        )

    def _sum_prior(months: int) -> float:
        recent_boundary = date.today() - timedelta(days=months * 30)
        prior_boundary = recent_boundary - timedelta(days=months * 30)
        return sum(
            float(dp.revenue or 0.0)
            for dp in data_points
            if prior_boundary <= dp.period < recent_boundary
        )

    def _growth(recent: float, prior: float) -> Optional[float]:
        if prior <= 0:
            return None
        return round((recent - prior) / prior, 4)

    growth_3m = _growth(_sum_recent(3), _sum_prior(3))
    growth_6m = _growth(_sum_recent(6), _sum_prior(6))
    growth_12m = _growth(_sum_recent(12), _sum_prior(12))

    log_action(
        db=db,
        action="trend_view",
        resource_type="title",
        resource_id=str(title_id),
        user_id=current_user.id,
        publisher_id=publisher.id,
        ip_address=_get_client_ip(request),
        details={"data_points": len(data_points)},
    )

    return TrendResponse(
        title_id=title_id,
        title_name=title.name_en or title.name,
        data_points=data_points,
        growth_rate_3m=growth_3m,
        growth_rate_6m=growth_6m,
        growth_rate_12m=growth_12m,
    )


@router.get(
    "/{title_id}/affinity",
    response_model=AffinityResponse,
    summary="Get similar titles (affinity analysis)",
    description=(
        "Returns a list of titles in the same genre with similar composite "
        "scores. Titles owned by the requesting publisher are shown with their "
        "real names; competitor titles are anonymised as 'Competitor A', "
        "'Competitor B', etc."
    ),
)
async def get_title_affinity(
    title_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AffinityResponse:
    """Return titles with similar scores in the same genre.

    Similarity is measured as the normalised absolute difference between
    overall scores (1 - |score_a - score_b| / 100). Up to 10 similar titles
    are returned, sorted by similarity descending.

    Titles from the same publisher are shown with their real names;
    all other titles are labelled 'Competitor A', 'Competitor B', etc.

    Args:
        title_id: Primary key of the reference title.
        request: FastAPI request object.
        current_user: Authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: Title not found or not owned by the user's publisher.
    """
    publisher = _get_publisher(current_user, db)
    title = _resolve_title(title_id, publisher.id, db)

    # Fetch the most recent score for the reference title
    ref_score: Optional[TitleScore] = _get_cached_score(title_id, db)
    if ref_score is None:
        engine = ScoringEngine(db)
        score_data = engine.calculate_title_score(title_id)
        ref_overall = score_data["overall_score"]
    else:
        ref_overall = ref_score.overall_score

    # Find all active titles in the same genre (excluding the reference title)
    genre_titles = (
        db.query(Title)
        .filter(
            Title.genre == title.genre,
            Title.id != title_id,
            Title.is_active.is_(True),
        )
        .all()
    )

    # Score each peer title and compute similarity
    engine = ScoringEngine(db)
    scored_peers: list[tuple[Title, float, float]] = []  # (title, overall, similarity)

    for peer in genre_titles:
        peer_score_row: Optional[TitleScore] = _get_cached_score(peer.id, db)
        if peer_score_row is not None:
            peer_overall = peer_score_row.overall_score
        else:
            try:
                peer_data = engine.calculate_title_score(peer.id)
                peer_overall = peer_data["overall_score"]
            except Exception:
                continue

        # Similarity: 1 - normalised absolute score difference
        similarity = max(0.0, 1.0 - abs(ref_overall - peer_overall) / 100.0)
        scored_peers.append((peer, peer_overall, similarity))

    # Sort by similarity descending; return top 10
    scored_peers.sort(key=lambda x: x[2], reverse=True)
    top_peers = scored_peers[:10]

    similar_titles: list[AffinityTitle] = []
    competitor_counter = 0
    competitor_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for peer_title, peer_overall, similarity in top_peers:
        is_own = peer_title.publisher_id == publisher.id

        if is_own:
            display_name: Optional[str] = peer_title.name_en or peer_title.name
            anon_label: Optional[str] = None
        else:
            display_name = None
            label_char = competitor_labels[competitor_counter % len(competitor_labels)]
            anon_label = f"Competitor {label_char}"
            competitor_counter += 1

        genre_str = (
            peer_title.genre.value
            if hasattr(peer_title.genre, "value")
            else str(peer_title.genre)
        )

        similar_titles.append(
            AffinityTitle(
                title_name=display_name,
                anonymous_label=anon_label,
                is_own_title=is_own,
                similarity_score=round(similarity, 4),
                genre=genre_str,
            )
        )

    log_action(
        db=db,
        action="affinity_view",
        resource_type="title",
        resource_id=str(title_id),
        user_id=current_user.id,
        publisher_id=publisher.id,
        ip_address=_get_client_ip(request),
        details={"similar_count": len(similar_titles)},
    )

    return AffinityResponse(
        title_id=title_id,
        title_name=title.name_en or title.name,
        similar_titles=similar_titles,
    )


@router.get(
    "/{title_id}/global",
    response_model=GlobalPotentialResponse,
    summary="Get overseas market potential (Enterprise only)",
    description=(
        "Returns a breakdown of international market opportunity across key "
        "regions. This endpoint is restricted to **Enterprise** tier publishers. "
        "Region scores are derived from the title's global_potential_score "
        "and genre-level market-size indicators."
    ),
)
async def get_title_global_potential(
    title_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GlobalPotentialResponse:
    """Return overseas market potential for *title_id*.

    Access is restricted to Enterprise tier publishers. Region-level potential
    scores are computed by distributing the title's global_potential_score
    across predefined regions according to their market-size weights.

    Args:
        title_id: Primary key of the title.
        request: FastAPI request object.
        current_user: Authenticated user.
        db: Database session.

    Raises:
        HTTPException 403: Publisher is not on the Enterprise tier.
        HTTPException 404: Title not found or not owned by the user's publisher.
    """
    publisher = _get_publisher(current_user, db)

    # Enforce Enterprise tier
    tier_str = publisher.tier.value if hasattr(publisher.tier, "value") else str(publisher.tier)
    tier_order = _TIER_ORDER.get(tier_str.upper(), 0)
    if tier_order < _TIER_ORDER[PublisherTier.ENTERPRISE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "The global market potential endpoint requires the Enterprise tier. "
                f"Current tier: {tier_str}"
            ),
        )

    title = _resolve_title(title_id, publisher.id, db)

    # Get the most recent cached score for global_potential_score
    cached: Optional[TitleScore] = _get_cached_score(title_id, db)
    global_score: float = 0.0
    if cached is not None and cached.global_potential_score is not None:
        global_score = cached.global_potential_score
    else:
        # Fall back to a heuristic estimate based on overall score
        if cached is not None:
            global_score = cached.overall_score * 0.6
        else:
            engine = ScoringEngine(db)
            score_data = engine.calculate_title_score(title_id)
            global_score = score_data["overall_score"] * 0.6

    # Build per-region breakdown
    regions: list[RegionPotential] = []
    for region_def in _OVERSEAS_REGIONS:
        region_score = round(global_score * region_def["weight"] * (100 / 0.30), 2)
        region_score = min(region_score, 100.0)

        # License recommendation based on score tier
        if region_score >= 70:
            recommendation = "High priority for licensing negotiations"
        elif region_score >= 40:
            recommendation = "Moderate potential; consider test release"
        else:
            recommendation = "Monitor market trends before committing"

        regions.append(
            RegionPotential(
                region=region_def["region"],
                potential_score=region_score,
                market_size_indicator=region_def["market_size_indicator"],
                license_recommendation=recommendation,
            )
        )

    # Anime impact multiplier estimate
    anime_multiplier: Optional[float] = None
    if title.has_anime:
        genre_str = (
            title.genre.value if hasattr(title.genre, "value") else str(title.genre)
        ).lower()
        from app.scoring.predictions import DEFAULT_GENRE_ANIME_MULTIPLIER
        anime_multiplier = DEFAULT_GENRE_ANIME_MULTIPLIER.get(genre_str, 2.0)

    log_action(
        db=db,
        action="global_potential_view",
        resource_type="title",
        resource_id=str(title_id),
        user_id=current_user.id,
        publisher_id=publisher.id,
        ip_address=_get_client_ip(request),
        details={"global_score": global_score},
    )

    return GlobalPotentialResponse(
        title_id=title_id,
        title_name=title.name_en or title.name,
        overall_global_score=round(global_score, 2),
        regions=regions,
        has_anime=title.has_anime,
        anime_impact_multiplier=anime_multiplier,
    )
