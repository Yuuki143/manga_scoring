"""Genre intelligence endpoints for the MMIP API.

Routes
------
GET /genres/{genre}/ranking – Ranked list of titles in a genre with
                              competitor anonymisation.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.genre_trend import GenreTrend
from app.models.publisher import Publisher
from app.models.score import TitleScore
from app.models.title import Genre, Title
from app.schemas.ranking import GenreRankingResponse, RankingEntry
from app.scoring.engine import ScoringEngine
from app.services.title_service import TitleService

router = APIRouter()


def _get_publisher(user, db: Session) -> Publisher:
    """Return the active publisher for the authenticated user.

    Raises:
        HTTPException 404: If the publisher is not found or inactive.
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


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract the originating client IP address."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def _get_cached_score(title_id: int, db: Session) -> Optional[TitleScore]:
    """Return the most recent TitleScore for a title, or None."""
    return (
        db.query(TitleScore)
        .filter(TitleScore.title_id == title_id)
        .order_by(TitleScore.calculated_at.desc())
        .first()
    )


@router.get(
    "/{genre}/ranking",
    response_model=GenreRankingResponse,
    summary="Get the genre leaderboard",
    description=(
        "Returns a ranked list of all active titles within the requested "
        "genre, ordered by overall composite score. "
        "Titles owned by the requesting publisher are shown with their real "
        "names and IDs; all other publishers' titles are anonymised as "
        "'Competitor A', 'Competitor B', etc. "
        "The genre growth rate from the most recent GenreTrend snapshot is "
        "included when available."
    ),
)
async def get_genre_ranking(
    genre: str,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenreRankingResponse:
    """Return the leaderboard for *genre* with anonymised competitors.

    All active titles in the specified genre are scored (using cached scores
    where available) and ranked from highest to lowest overall score. The
    caller's own titles are shown with full details; competitors are shown
    only with an anonymised label.

    Args:
        genre: Genre identifier matching the ``Genre`` enum
            (case-insensitive, e.g. ``"shonen"`` or ``"SHONEN"``).
        request: FastAPI request object.
        current_user: Authenticated user.
        db: Database session.

    Raises:
        HTTPException 400: If *genre* is not a recognised genre value.
    """
    publisher = _get_publisher(current_user, db)

    # Validate and normalise genre
    genre_upper = genre.upper()
    try:
        genre_enum = Genre(genre_upper)
    except ValueError:
        valid = [g.value for g in Genre]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{genre}' is not a valid genre. Valid genres: {valid}",
        )

    # Retrieve all active titles in this genre
    service = TitleService(db)
    try:
        all_titles = service.get_genre_titles(genre_upper)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not all_titles:
        return GenreRankingResponse(
            genre=genre_upper,
            total_titles=0,
            rankings=[],
            genre_growth_rate=None,
        )

    # Score every title (cached where possible, live otherwise)
    engine = ScoringEngine(db)
    scored: list[tuple[Title, float, float]] = []  # (title, overall, genre_percentile)

    for t in all_titles:
        cached = _get_cached_score(t.id, db)
        if cached is not None:
            overall = cached.overall_score
            genre_pct = cached.genre_percentile
        else:
            try:
                data = engine.calculate_title_score(t.id)
                overall = data["overall_score"]
                genre_pct = data["genre_percentile"]
            except Exception:
                overall = 0.0
                genre_pct = 0.0

        scored.append((t, overall, genre_pct))

    # Sort by overall score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Build ranking entries with competitor anonymisation
    rankings: list[RankingEntry] = []
    competitor_counter = 0
    competitor_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for rank_num, (t, overall, genre_pct) in enumerate(scored, start=1):
        is_own = t.publisher_id == publisher.id

        if is_own:
            entry_name: Optional[str] = t.name_en or t.name
            entry_title_id: Optional[int] = t.id
            anon_label: Optional[str] = None
        else:
            entry_name = None
            entry_title_id = None
            label_char = competitor_labels[competitor_counter % len(competitor_labels)]
            anon_label = f"Competitor {label_char}"
            competitor_counter += 1

        rankings.append(
            RankingEntry(
                rank=rank_num,
                title_name=entry_name,
                title_id=entry_title_id,
                is_own_title=is_own,
                anonymous_label=anon_label,
                overall_score=round(overall, 2),
                genre_percentile=round(genre_pct, 2),
            )
        )

    # Retrieve the most recent genre growth rate
    genre_growth_rate: Optional[float] = None
    latest_trend = (
        db.query(GenreTrend)
        .filter(GenreTrend.genre == genre_upper)
        .order_by(GenreTrend.period_date.desc())
        .first()
    )
    if latest_trend is not None:
        genre_growth_rate = latest_trend.growth_rate

    log_action(
        db=db,
        action="genre_ranking_view",
        resource_type="genre",
        resource_id=genre_upper,
        user_id=current_user.id,
        publisher_id=publisher.id,
        ip_address=_get_client_ip(request),
        details={"total_titles": len(all_titles)},
    )

    return GenreRankingResponse(
        genre=genre_upper,
        total_titles=len(all_titles),
        rankings=rankings,
        genre_growth_rate=genre_growth_rate,
    )
