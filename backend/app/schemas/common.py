from pydantic import BaseModel
from enum import Enum


class TierEnum(str, Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class GenreEnum(str, Enum):
    SHONEN = "shonen"
    SHOJO = "shojo"
    SEINEN = "seinen"
    JOSEI = "josei"
    KODOMO = "kodomo"
    BL = "bl"
    GL = "gl"
    ISEKAI = "isekai"
    HORROR = "horror"
    ROMANCE = "romance"
    ACTION = "action"
    FANTASY = "fantasy"
    COMEDY = "comedy"
    SLICE_OF_LIFE = "slice_of_life"
    SPORTS = "sports"
    MYSTERY = "mystery"
    SCI_FI = "sci_fi"
    OTHER = "other"


class ConfidenceRating(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class AlertType(str, Enum):
    BREAKOUT = "breakout"
    GENRE_TREND = "genre_trend"
    ANIME_IMPACT = "anime_impact"
    OVERSEAS_DEMAND = "overseas_demand"
    COMPETITOR_MOVEMENT = "competitor_movement"


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
