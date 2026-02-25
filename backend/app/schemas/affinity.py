from typing import Optional
from pydantic import BaseModel


class AffinityTitle(BaseModel):
    title_name: Optional[str] = None       # Only for own titles
    anonymous_label: Optional[str] = None
    is_own_title: bool
    similarity_score: float                # 0-1
    shared_reader_ratio: Optional[float] = None
    genre: str


class AffinityResponse(BaseModel):
    title_id: int
    title_name: str
    similar_titles: list[AffinityTitle]
