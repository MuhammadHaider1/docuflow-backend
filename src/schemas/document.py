import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FolderCreate(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    children: list["FolderResponse"] = []

    model_config = ConfigDict(from_attributes=True)


FolderResponse.model_rebuild()


class DocumentCreate(BaseModel):
    title: str
    description: str | None = None
    folder_id: uuid.UUID | None = None


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    version_number: int
    storage_key: str
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    organization_id: uuid.UUID
    processing_status: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    versions: list[DocumentVersionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentDownloadResponse(BaseModel):
    download_url: str
    expires_in_seconds: int = 900


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
