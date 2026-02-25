from typing import Optional
from pydantic import BaseModel


class RankingEntry(BaseModel):
    rank: int
    title_name: Optional[str] = None       # Only shown for own titles
    title_id: Optional[int] = None         # Only shown for own titles
    is_own_title: bool
    anonymous_label: Optional[str] = None  # "Competitor A", etc.
    overall_score: float
    genre_percentile: float


class GenreRankingResponse(BaseModel):
    genre: str
    total_titles: int
    rankings: list[RankingEntry]
    genre_growth_rate: Optional[float] = None
