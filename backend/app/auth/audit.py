"""Audit logging helpers for recording platform actions.

Each call to ``log_action`` appends an immutable record to the audit_logs
table.  The function commits immediately so that audit records are
persisted even if the surrounding request transaction later rolls back.
"""

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: int | None = None,
    publisher_id: int | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Record an audit log entry and commit it to the database.

    Args:
        db: Active SQLAlchemy session.
        action: Short verb describing what happened (e.g. ``"login"``,
            ``"upload"``, ``"delete"``).
        resource_type: Category of the affected resource (e.g.
            ``"user"``, ``"sales_data"``, ``"title"``).
        resource_id: Optional string identifier of the specific resource
            instance (e.g. a row id or slug).
        user_id: ID of the User who triggered the action, if applicable.
        publisher_id: ID of the Publisher context, if applicable.
        ip_address: IPv4 or IPv6 address of the originating request.
        details: Arbitrary JSON-serialisable dict with additional context
            (e.g. changed field values, upload statistics).

    Returns:
        The persisted :class:`~app.models.audit_log.AuditLog` instance.
    """
    log_entry = AuditLog(
        user_id=user_id,
        publisher_id=publisher_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
