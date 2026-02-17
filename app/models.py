from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class ReviewCreate(BaseModel):
    business_slug: str = Field(min_length=1, max_length=60)
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)
    contact_email: Optional[EmailStr] = None
