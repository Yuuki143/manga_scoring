from typing import Optional
from pydantic import BaseModel


class RegionPotential(BaseModel):
    region: str
    potential_score: float
    anime_viewership: Optional[float] = None
    market_size_indicator: str             # "high", "medium", "low"
    license_recommendation: Optional[str] = None


class GlobalPotentialResponse(BaseModel):
    title_id: int
    title_name: str
    overall_global_score: float
    regions: list[RegionPotential]
    has_anime: bool
    anime_impact_multiplier: Optional[float] = None
