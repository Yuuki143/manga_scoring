from typing import Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    records_processed: int
    records_accepted: int
    records_rejected: int
    errors: Optional[list[str]] = None
    upload_id: str
