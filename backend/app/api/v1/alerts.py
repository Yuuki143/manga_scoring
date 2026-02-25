"""Intelligence alert endpoints for the MMIP API.

Alert visibility is gated by the publisher's subscription tier:

* **Basic**      – ``BREAKOUT`` alerts only.
* **Pro**        – ``BREAKOUT``, ``GENRE_TREND``, ``ANIME_IMPACT``.
* **Enterprise** – All alert types including ``OVERSEAS_DEMAND`` and
  ``COMPETITOR_MOVEMENT``.

Routes
------
GET /alerts – Paginated list of alerts for the authenticated publisher.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.publisher import Publisher
from app.models.title import Title
from app.schemas.alert import AlertListResponse, AlertResponse
from app.schemas.common import AlertType as SchemaAlertType
from app.services.alert_service import AlertService

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


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List intelligence alerts for the publisher",
    description=(
        "Returns a paginated list of alerts for the authenticated publisher, "
        "filtered according to subscription tier. "
        "**Basic**: BREAKOUT only. "
        "**Pro**: BREAKOUT + GENRE_TREND + ANIME_IMPACT. "
        "**Enterprise**: all alert types. "
        "Alerts are returned in reverse-chronological order."
    ),
)
async def list_alerts(
    request: Request,
    page: int = Query(default=1, ge=1, description="1-based page number"),
    per_page: int = Query(
        default=20, ge=1, le=100, description="Number of alerts per page (max 100)"
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    """Return paginated alerts for the authenticated publisher.

    The tier of the requesting publisher determines which alert types are
    returned. Alerts are ordered newest-first.

    Args:
        request: FastAPI request object.
        page: 1-based page index. Defaults to 1.
        per_page: Maximum alerts per page. Defaults to 20, capped at 100.
        current_user: Authenticated user from JWT dependency.
        db: Database session.

    Raises:
        HTTPException 404: Publisher not found or inactive.
    """
    publisher = _get_publisher(current_user, db)

    tier_str = (
        publisher.tier.value if hasattr(publisher.tier, "value") else str(publisher.tier)
    )

    service = AlertService(db)
    result = service.get_alerts(
        publisher_id=publisher.id,
        tier=tier_str,
        page=page,
        per_page=per_page,
    )

    # Build alert response objects, enriching with title name where available
    alert_responses: list[AlertResponse] = []
    for alert in result["alerts"]:
        title_name: Optional[str] = None
        if alert.title_id is not None:
            title = db.query(Title).filter(Title.id == alert.title_id).first()
            if title is not None:
                title_name = title.name_en or title.name

        # Normalise alert_type to the schema enum value (lowercase)
        raw_type = (
            alert.alert_type.value
            if hasattr(alert.alert_type, "value")
            else str(alert.alert_type)
        )
        try:
            schema_alert_type = SchemaAlertType(raw_type.lower())
        except ValueError:
            # Fallback: match by normalised name
            schema_alert_type = SchemaAlertType.BREAKOUT

        # Normalise severity to string
        severity_str = (
            alert.severity.value
            if hasattr(alert.severity, "value")
            else str(alert.severity)
        )

        alert_responses.append(
            AlertResponse(
                id=alert.id,
                alert_type=schema_alert_type,
                severity=severity_str,
                message=alert.message,
                title_name=title_name,
                data=alert.data,
                is_read=alert.is_read,
                created_at=alert.created_at,
            )
        )

    log_action(
        db=db,
        action="alerts_list",
        resource_type="alert",
        user_id=current_user.id,
        publisher_id=publisher.id,
        ip_address=_get_client_ip(request),
        details={
            "tier": tier_str,
            "page": page,
            "per_page": per_page,
            "total": result["total"],
        },
    )

    return AlertListResponse(
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        pages=result["pages"],
        alerts=alert_responses,
    )
