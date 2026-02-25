"""ORM model registry for the MMIP application.

Importing this package ensures that all SQLAlchemy models are registered
against the shared DeclarativeBase before Alembic migrations or application
startup attempts to introspect the metadata.

All public model classes and enums are re-exported here so that other
modules can import them from a single location:

    from app.models import Publisher, Title, TitleScore, ...
"""

from app.models.alert import Alert, AlertRequiredTier, AlertSeverity, AlertType
from app.models.audit_log import AuditLog
from app.models.base import BaseModel, TimestampMixin
from app.models.genre_trend import GenreTrend, TrendingDirection
from app.models.platform_data import PlatformData
from app.models.publisher import DataProvisionFrequency, Publisher, PublisherTier
from app.models.sales_data import DataSource, SalesData
from app.models.score import ConfidenceRating, TitleScore
from app.models.title import Genre, Title, TitleStatus
from app.models.user import User, UserRole

__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    # Publisher
    "Publisher",
    "PublisherTier",
    "DataProvisionFrequency",
    # User
    "User",
    "UserRole",
    # Title
    "Title",
    "Genre",
    "TitleStatus",
    # SalesData
    "SalesData",
    "DataSource",
    # PlatformData
    "PlatformData",
    # TitleScore
    "TitleScore",
    "ConfidenceRating",
    # Alert
    "Alert",
    "AlertType",
    "AlertSeverity",
    "AlertRequiredTier",
    # GenreTrend
    "GenreTrend",
    "TrendingDirection",
    # AuditLog
    "AuditLog",
]
