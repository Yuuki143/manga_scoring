from typing import Optional
from pydantic import BaseModel
from pydantic import ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    publisher_id: Optional[int] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    publisher_id: int
    role: str = "viewer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    publisher_id: int
    role: str
    is_active: bool
