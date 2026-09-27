import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    parent_id: uuid.UUID | None = None


# 👈 Missing Schema for Comment Editing
class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class UserMinResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    parent_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    user: UserMinResponse
    replies: list["CommentResponse"] = []

    model_config = ConfigDict(from_attributes=True)
