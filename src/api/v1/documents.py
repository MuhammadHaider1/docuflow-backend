import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import PermissionChecker
from src.core.database import get_db
from src.core.limiter import limiter  # SlowAPI limiter instance
from src.core.security import is_authenticated
from src.models.auth import User
from src.schemas.document import (
    DocumentCreate,
    DocumentDownloadResponse,
    DocumentResponse,
    DocumentVersionResponse,
    FolderCreate,
    FolderResponse,
    FolderUpdate,
)
from src.schemas.generic import PaginatedResponse
from src.services.document import DocumentService
from src.tasks.document_tasks import process_document_task

router = APIRouter()

# ==========================================
# 📂 FOLDER ENDPOINTS
# ==========================================


@router.post(
    "/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("60/minute")
async def create_new_folder(
    request: Request,
    payload: FolderCreate,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("folder:create")),
):
    service = DocumentService(db)
    return await service.create_new_folder(payload, org_id=x_organization_id)


@router.get("/folders/tree", response_model=list[FolderResponse])
@limiter.limit("120/minute")
async def get_organization_folder_tree(
    request: Request,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    service = DocumentService(db)
    return await service.get_folders_tree(org_id=x_organization_id)


@router.patch("/folders/{folder_id}", response_model=FolderResponse)
@limiter.limit("60/minute")
async def update_folder(
    request: Request,
    folder_id: uuid.UUID,
    payload: FolderUpdate,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("organization:update")),
):
    """Rename or move folder."""
    service = DocumentService(db)
    return await service.update_folder(
        folder_id=folder_id, payload=payload, org_id=x_organization_id
    )


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_folder(
    request: Request,
    folder_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("organization:update")),
):
    """Delete empty folder."""
    service = DocumentService(db)
    await service.delete_folder(folder_id=folder_id, org_id=x_organization_id)
    return None


# ==========================================
# 📄 DOCUMENT ENDPOINTS
# ==========================================


@router.post(
    "/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("30/minute")
async def create_new_document(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    folder_id: uuid.UUID = Form(None),
    file: UploadFile = File(...),
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:create")),
):
    """Creates a new document, uploads initial file version, and triggers Celery extraction."""
    payload = DocumentCreate(title=title, description=description, folder_id=folder_id)
    service = DocumentService(db)
    document = await service.create_new_document(
        payload=payload, user_id=current_user.id, org_id=x_organization_id, file=file
    )

    # 🚀 Trigger Celery Background Processing Pipeline
    latest_ver = getattr(document, "latest_version", None)
    if latest_ver and hasattr(latest_ver, "storage_key"):
        process_document_task.delay(
            document_id=str(document.id),
            organization_id=str(x_organization_id),
            storage_key=latest_ver.storage_key,
        )

    return document


@router.get("/documents/search", response_model=PaginatedResponse[DocumentResponse])
@limiter.limit("100/minute")
async def search_document(
    request: Request,
    q: str | None = Query(None, description="Search query string"),
    folder_id: uuid.UUID | None = Query(None, description="Filter by Folder ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", pattern="^(created_at|title|updated_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    """Search and list documents inside organization with pagination."""
    service = DocumentService(db)
    return await service.search_documents(
        org_id=x_organization_id,
        query=q,
        folder_id=folder_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
@limiter.limit("120/minute")
async def get_document_details(
    request: Request,
    document_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    service = DocumentService(db)
    return await service.get_document_details(
        doc_id=document_id, org_id=x_organization_id
    )


# --- VERSIONS ---


@router.post(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def upload_document_version(
    request: Request,
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:update")),
):
    service = DocumentService(db)
    version = await service.upload_document_version(
        doc_id=document_id,
        org_id=x_organization_id,
        user_id=current_user.id,
        file=file,
    )

    # 🚀 Trigger Background Processing for New Version
    process_document_task.delay(
        document_id=str(document_id),
        organization_id=str(x_organization_id),
        storage_key=version.storage_key,
    )

    return version


@router.get(
    "/documents/{document_id}/versions", response_model=list[DocumentVersionResponse]
)
@limiter.limit("120/minute")
async def list_document_versions(
    request: Request,
    document_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    """Fetch all revision history / versions of a document."""
    service = DocumentService(db)
    return await service.get_document_versions(
        doc_id=document_id, org_id=x_organization_id
    )


@router.get(
    "/documents/{document_id}/versions/{version_id}/download",
    response_model=DocumentDownloadResponse,
)
@limiter.limit("60/minute")
async def get_document_version_download_url(
    request: Request,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    expires_in: int = Query(900, ge=60, le=86400),
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    service = DocumentService(db)
    return await service.get_version_download_url(
        doc_id=document_id,
        version_id=version_id,
        expires_in=expires_in,
        org_id=x_organization_id,
    )


# --- ARCHIVE & RESTORE ---


@router.delete("/documents/{document_id}", response_model=DocumentResponse)
@limiter.limit("30/minute")
async def archive_existing_document(
    request: Request,
    document_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:delete")),
):
    service = DocumentService(db)
    return await service.archive_document(doc_id=document_id, org_id=x_organization_id)


@router.post("/documents/{document_id}/restore", response_model=DocumentResponse)
@limiter.limit("30/minute")
async def restore_archived_document(
    request: Request,
    document_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:update")),
):
    """Restore an archived / soft-deleted document."""
    service = DocumentService(db)
    return await service.restore_document(doc_id=document_id, org_id=x_organization_id)
