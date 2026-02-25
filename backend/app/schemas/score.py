from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.schemas.common import ConfidenceRating


class ScoreResponse(BaseModel):
    title_id: int
    title_name: str
    overall_score: float
    revenue_score: Optional[float] = None                    # Pro+ only
    growth_score: Optional[float] = None                     # Pro+ only
    platform_distribution_score: Optional[float] = None      # Pro+ only
    stability_score: Optional[float] = None                  # Pro+ only
    ranking_frequency_score: Optional[float] = None          # Pro+ only
    confidence_rating: ConfidenceRating
    global_potential_score: Optional[float] = None           # Enterprise only
    genre_percentile: Optional[float] = None
    calculated_at: datetime
