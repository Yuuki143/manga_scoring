from datetime import date, datetime
from pydantic import BaseModel
from pydantic import ConfigDict
from typing import Optional

from app.schemas.common import GenreEnum


class TitleBase(BaseModel):
    name: str
    name_en: Optional[str] = None
    publisher_id: int
    genre: Optional[GenreEnum] = None
    author: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    has_anime: bool = False
    anime_start_date: Optional[date] = None
    is_active: bool = True


class TitleCreate(TitleBase):
    pass


class TitleResponse(TitleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
