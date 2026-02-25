from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PredictionEntry(BaseModel):
    rank: int
    title_name: Optional[str] = None
    anonymous_label: Optional[str] = None
    is_own_title: bool
    prediction_type: str  # "anime_linked", "anime_candidate", "overseas_expansion"
    predicted_growth: float
    confidence: float
    factors: list[str]


class PredictionResponse(BaseModel):
    predictions: list[PredictionEntry]
    generated_at: datetime
