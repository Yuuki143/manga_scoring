from datetime import date
from typing import Optional
from pydantic import BaseModel


class TrendDataPoint(BaseModel):
    period: date
    revenue: Optional[float] = None
    units_sold: Optional[int] = None
    engagement_rate: Optional[float] = None
    overall_score: Optional[float] = None


class TrendResponse(BaseModel):
    title_id: int
    title_name: str
    data_points: list[TrendDataPoint]
    growth_rate_3m: Optional[float] = None
    growth_rate_6m: Optional[float] = None
    growth_rate_12m: Optional[float] = None
