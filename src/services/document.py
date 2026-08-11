import math
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.models.document import Document, DocumentVersion, Folder
from src.repositories.document import DocumentRepository, FolderRepository
from src.schemas.document import (
    DocumentCreate,
    DocumentDownloadResponse,
    FolderCreate,
    FolderResponse,
    FolderUpdate,
)
from src.services.storage import storage_manager  # MinIO client instance
from src.tasks.document_tasks import process_document_task


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.folder_repo = FolderRepository(db)
        self.document_repo = DocumentRepository(db)

    # ==========================================
    # 📂 FOLDERS OPERATIONS
    # ==========================================

    async def create_new_folder(
        self,
        payload: FolderCreate,
        org_id: uuid.UUID,
    ) -> Folder:
        if payload.parent_id is not None:
            parent = await self.folder_repo.get_folder_by_id(payload.parent_id)

            if not parent or parent.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent folder not found in this organization",
                )

        folder = await self.folder_repo.create_folder(payload, organization_id=org_id)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def get_folders_tree(self, org_id: uuid.UUID) -> list[FolderResponse]:
        flat_folders = await self.folder_repo.get_organization_folders(org_id)
        folder_map = {str(f.id): FolderResponse.model_validate(f) for f in flat_folders}

        root_folders: list[FolderResponse] = []

        for f in flat_folders:
            current_node = folder_map[str(f.id)]

            if f.parent_id is None:
                root_folders.append(current_node)
            else:
                parent_key = str(f.parent_id)
                if parent_key in folder_map:
                    parent_node = folder_map[parent_key]
                    parent_node.children.append(current_node)

        return root_folders

    async def update_folder(
        self, folder_id: uuid.UUID, payload: FolderUpdate, org_id: uuid.UUID
    ) -> Folder:
        folder = await self.folder_repo.get_folder_by_id(folder_id)
        if not folder or folder.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found in this organization",
            )

        # Cyclic dependency check if changing parent_id
        if payload.parent_id is not None:
            if payload.parent_id == folder_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A folder cannot be its own parent",
                )
            parent = await self.folder_repo.get_folder_by_id(payload.parent_id)
            if not parent or parent.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target parent folder not found in this organization",
                )

        updated_folder = await self.folder_repo.update_folder(folder, payload)
        await self.db.commit()
        await self.db.refresh(updated_folder)
        return updated_folder

    async def delete_folder(self, folder_id: uuid.UUID, org_id: uuid.UUID) -> None:
        folder = await self.folder_repo.get_folder_by_id(folder_id)
        if not folder or folder.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found in this organization",
            )

        await self.folder_repo.delete_folder(folder)
        await self.db.commit()

    # ==========================================
    # 📄 DOCUMENTS OPERATIONS
    # ==========================================

    async def create_new_document(
        self,
        payload: DocumentCreate,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        file: UploadFile,
    ) -> Document:
        if payload.folder_id is not None:
            folder = await self.folder_repo.get_folder_by_id(payload.folder_id)
            if not folder or folder.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target folder not found in this organization",
                )

        # 1. Read file buffer & metadata
        file_content = await file.read()
        file_size = len(file_content)
        mime_type = file.content_type or "application/octet-stream"
        file_name = file.filename or "unnamed_file"

        # 2. Create Master Document row
        db_document = await self.document_repo.create_document(
            obj_in=payload, organization_id=org_id, owner_id=user_id
        )

        # 3. Generate Storage Key
        storage_key = (
            f"organizations/{org_id}/documents/{db_document.id}/v1_{file_name}"
        )

        uploaded_to_minio = False

        try:
            # 4. Stream File to MinIO
            async with storage_manager.get_client() as s3:
                await s3.put_object(
                    Bucket=settings.MINIO_BUCKET_NAME,
                    Key=storage_key,
                    Body=file_content,
                    ContentType=mime_type,
                )
            uploaded_to_minio = True

            # 5. Create Version Metadata
            db_version = DocumentVersion(
                document_id=db_document.id,
                version_number=1,
                storage_key=storage_key,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                uploaded_by=user_id,
            )
            self.db.add(db_version)

            db_document.processing_status = "processing"
            await self.db.commit()

            # 6. Trigger Async Background Processing Task
            process_document_task.delay(
                document_id=str(db_document.id),
                organization_id=str(org_id),
                storage_key=storage_key,
            )

            return await self.get_document_details(db_document.id, org_id)

        except Exception as e:
            await self.db.rollback()

            if uploaded_to_minio:
                try:
                    async with storage_manager.get_client() as s3:
                        await s3.delete_object(
                            Bucket=settings.MINIO_BUCKET_NAME, Key=storage_key
                        )
                except Exception:
                    pass

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage or Version pipeline failed: {str(e)}",
            )

    async def get_document_details(
        self, doc_id: uuid.UUID, org_id: uuid.UUID
    ) -> Document:
        stmt = (
            select(Document)
            .where(Document.id == doc_id, Document.organization_id == org_id)
            .options(selectinload(Document.versions))
        )
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        return doc

    async def archive_document(self, doc_id: uuid.UUID, org_id: uuid.UUID) -> Document:
        doc = await self.get_document_details(doc_id, org_id)
        updated_doc = await self.document_repo.archive_document(doc)
        await self.db.commit()
        return await self.get_document_details(updated_doc.id, org_id)

    async def restore_document(self, doc_id: uuid.UUID, org_id: uuid.UUID) -> Document:
        doc = await self.get_document_details(doc_id, org_id)
        updated_doc = await self.document_repo.restore_document(doc)
        await self.db.commit()
        return await self.get_document_details(updated_doc.id, org_id)

    async def upload_document_version(
        self, doc_id: uuid.UUID, org_id: uuid.UUID, user_id: uuid.UUID, file: UploadFile
    ) -> DocumentVersion:
        doc = await self.get_document_details(doc_id, org_id)

        existing_version = max([v.version_number for v in doc.versions], default=0)
        new_version = existing_version + 1

        file_content = await file.read()
        file_size = len(file_content)
        mime_type = file.content_type or "application/octet-stream"
        file_name = file.filename or "unnamed_file"

        storage_key = (
            f"organizations/{org_id}/documents/{doc_id}/v{new_version}_{file_name}"
        )

        uploaded_to_minio = False

        try:
            async with storage_manager.get_client() as s3:
                await s3.put_object(
                    Bucket=settings.MINIO_BUCKET_NAME,
                    Key=storage_key,
                    Body=file_content,
                    ContentType=mime_type,
                )
            uploaded_to_minio = True

            new_document_version = DocumentVersion(
                document_id=doc_id,
                version_number=new_version,
                storage_key=storage_key,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                uploaded_by=user_id,
            )

            self.db.add(new_document_version)
            doc.processing_status = "processing"

            await self.db.commit()
            await self.db.refresh(new_document_version)

            process_document_task.delay(
                document_id=str(doc_id),
                organization_id=str(org_id),
                storage_key=storage_key,
            )

            return new_document_version

        except Exception as e:
            await self.db.rollback()

            if uploaded_to_minio:
                try:
                    async with storage_manager.get_client() as s3:
                        await s3.delete_object(
                            Bucket=settings.MINIO_BUCKET_NAME, Key=storage_key
                        )
                except Exception:
                    pass

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload document version pipeline: {str(e)}",
            )

    async def get_document_versions(
        self, doc_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[DocumentVersion]:
        await self.get_document_details(doc_id, org_id)
        return await self.document_repo.get_document_versions(doc_id)

    async def get_version_download_url(
        self,
        doc_id: uuid.UUID,
        version_id: uuid.UUID,
        org_id: uuid.UUID,
        expires_in: int = 900,
    ) -> DocumentDownloadResponse:

        await self.get_document_details(doc_id, org_id)

        stmt = select(DocumentVersion).where(
            DocumentVersion.id == version_id, DocumentVersion.document_id == doc_id
        )

        result = await self.db.execute(stmt)
        target_version = result.scalar_one_or_none()

        if not target_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested document version not found",
            )

        try:
            async with storage_manager.get_client() as s3:
                download_url = await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": settings.MINIO_BUCKET_NAME,
                        "Key": target_version.storage_key,
                    },
                    ExpiresIn=expires_in,
                )

            return DocumentDownloadResponse(
                download_url=download_url,
                expires_in_seconds=expires_in,
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download URL: {str(e)}",
            )

    async def search_documents(
        self,
        org_id: uuid.UUID,
        query: str | None = None,
        folder_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ):
        filters = [
            Document.organization_id == org_id,
            or_(Document.is_archived.is_(False), Document.is_archived.is_(None)),
        ]

        if folder_id:
            filters.append(Document.folder_id == folder_id)

        if query and query.strip():
            clean_query = query.strip()
            search_pattern = f"%{clean_query}%"
            filters.append(
                or_(
                    Document.title.ilike(search_pattern),
                    func.coalesce(Document.description, "").ilike(search_pattern),
                    func.coalesce(Document.extracted_content, "").ilike(search_pattern),
                )
            )

        count_stmt = select(func.count(Document.id)).where(*filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        sort_column = getattr(Document, sort_by, Document.created_at)
        order_clause = (
            sort_column.desc() if sort_order.lower() == "desc" else sort_column.asc()
        )

        offset_val = (page - 1) * page_size

        stmt = (
            select(Document)
            .options(selectinload(Document.versions))
            .where(*filters)
            .order_by(order_clause)
            .offset(offset_val)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
