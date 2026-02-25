from app.schemas.common import (
    TierEnum,
    GenreEnum,
    ConfidenceRating,
    AlertType,
    PaginatedResponse,
)
from app.schemas.title import (
    TitleBase,
    TitleCreate,
    TitleResponse,
)
from app.schemas.score import ScoreResponse
from app.schemas.trend import (
    TrendDataPoint,
    TrendResponse,
)
from app.schemas.ranking import (
    RankingEntry,
    GenreRankingResponse,
)
from app.schemas.affinity import (
    AffinityTitle,
    AffinityResponse,
)
from app.schemas.global_potential import (
    RegionPotential,
    GlobalPotentialResponse,
)
from app.schemas.alert import (
    AlertResponse,
    AlertListResponse,
)
from app.schemas.prediction import (
    PredictionEntry,
    PredictionResponse,
)
from app.schemas.upload import UploadResponse
from app.schemas.auth import (
    Token,
    TokenData,
    UserCreate,
    UserResponse,
)

__all__ = [
    # common
    "TierEnum",
    "GenreEnum",
    "ConfidenceRating",
    "AlertType",
    "PaginatedResponse",
    # title
    "TitleBase",
    "TitleCreate",
    "TitleResponse",
    # score
    "ScoreResponse",
    # trend
    "TrendDataPoint",
    "TrendResponse",
    # ranking
    "RankingEntry",
    "GenreRankingResponse",
    # affinity
    "AffinityTitle",
    "AffinityResponse",
    # global_potential
    "RegionPotential",
    "GlobalPotentialResponse",
    # alert
    "AlertResponse",
    "AlertListResponse",
    # prediction
    "PredictionEntry",
    "PredictionResponse",
    # upload
    "UploadResponse",
    # auth
    "Token",
    "TokenData",
    "UserCreate",
    "UserResponse",
]
