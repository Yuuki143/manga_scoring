"""Data upload endpoints for the MMIP API.

Publishers submit CSV or Excel files containing sales data via this endpoint.
The DataProcessor pipeline handles format detection, title matching, and
upsert of SalesData records.

Routes
------
POST /data/upload – Upload a sales data file (CSV or Excel).
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.publisher import Publisher
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.ingestion.processor import DataProcessor

router = APIRouter()

# Maximum upload file size: 50 MB
_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

# Accepted MIME types / file extensions
_ACCEPTED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",  # Some clients send this for any binary
}

_ACCEPTED_EXTENSIONS = {".csv", ".xls", ".xlsx"}


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


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload sales data (CSV or Excel)",
    description=(
        "Accept a CSV or Excel file containing sales data for the publisher's "
        "titles. The file is parsed, validated, and ingested into the platform. "
        "Existing records with matching ``(title, platform, period)`` keys are "
        "updated in place; new records are inserted. "
        "Requires the **EDITOR** role or above. "
        "Maximum file size: 50 MB. Accepted formats: CSV, XLS, XLSX."
    ),
)
async def upload_sales_data(
    request: Request,
    file: UploadFile = File(..., description="CSV or Excel file containing sales data"),
    current_user: User = Depends(require_role("EDITOR")),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Parse and ingest an uploaded sales data file.

    The endpoint delegates all parsing and persistence logic to
    :class:`~app.ingestion.processor.DataProcessor`. A detailed summary of
    accepted, rejected, and auto-created records is returned.

    Args:
        request: FastAPI request object (used for IP extraction in audit log).
        file: The uploaded file (multipart form data).
        current_user: Authenticated user with at least the EDITOR role.
        db: Database session.

    Raises:
        HTTPException 400: If the file type is not supported or the file is empty.
        HTTPException 413: If the file exceeds the 50 MB size limit.
        HTTPException 422: If the file cannot be parsed at all.
        HTTPException 404: If the publisher is not found or inactive.
    """
    publisher = _get_publisher(current_user, db)

    # Validate filename extension
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Accepted formats: {', '.join(sorted(_ACCEPTED_EXTENSIONS))}"
            ),
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        )
    finally:
        await file.close()

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(file_content) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size ({len(file_content) / 1024 / 1024:.1f} MB) exceeds the "
                f"50 MB limit"
            ),
        )

    # Run the ingestion pipeline
    processor = DataProcessor(db)
    try:
        result = processor.process_upload(
            file_content=file_content,
            filename=filename,
            publisher_id=publisher.id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process the uploaded file: {exc}",
        )

    # Record audit entry
    log_action(
        db=db,
        action="data_upload",
        resource_type="sales_data",
        resource_id=result.get("upload_id"),
        user_id=current_user.id,
        publisher_id=publisher.id,
        ip_address=_get_client_ip(request),
        details={
            "filename": filename,
            "file_size_bytes": len(file_content),
            "upload_id": result.get("upload_id"),
            "status": result.get("status"),
            "records_processed": result.get("records_processed", 0),
            "records_accepted": result.get("records_accepted", 0),
            "records_rejected": result.get("records_rejected", 0),
            "titles_created": result.get("titles_created", 0),
            "format_detected": result.get("format_detected"),
        },
    )

    return UploadResponse(
        status=result.get("status", "partial"),
        records_processed=result.get("records_processed", 0),
        records_accepted=result.get("records_accepted", 0),
        records_rejected=result.get("records_rejected", 0),
        errors=result.get("errors") or None,
        upload_id=result["upload_id"],
    )
