import uuid
from typing import List

from sqlalchemy import asc, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.document import Document, DocumentVersion, Folder
from src.schemas.document import DocumentCreate, FolderCreate, FolderUpdate


class FolderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_folder(
        self, obj_in: FolderCreate, organization_id: uuid.UUID
    ) -> Folder:
        db_obj = Folder(
            name=obj_in.name,
            parent_id=obj_in.parent_id,
            organization_id=organization_id,
        )

        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_folder_by_id(self, folder_id: uuid.UUID) -> Folder | None:
        result = await self.db.execute(select(Folder).where(Folder.id == folder_id))
        return result.scalar_one_or_none()

    async def get_organization_folders(self, org_id: uuid.UUID) -> list[Folder]:
        query = select(Folder).where(Folder.organization_id == org_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # 👈 Missing: Update Folder
    async def update_folder(self, db_obj: Folder, obj_in: FolderUpdate) -> Folder:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await self.db.flush()
        return db_obj

    # 👈 Missing: Delete Folder
    async def delete_folder(self, db_obj: Folder) -> None:
        await self.db.delete(db_obj)
        await self.db.flush()


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self, obj_in: DocumentCreate, organization_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Document:
        db_obj = Document(
            title=obj_in.title,
            folder_id=obj_in.folder_id,
            description=obj_in.description,
            organization_id=organization_id,
            owner_id=owner_id,
            processing_status="pending",
        )

        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_document_by_id(self, document_id: uuid.UUID) -> Document | None:
        query = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.versions))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # 👈 Missing: Search and Paginate Documents
    async def search_documents(
        self,
        org_id: uuid.UUID,
        query: str | None = None,
        folder_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[List[Document], int]:
        stmt = select(Document).where(
            Document.organization_id == org_id, Document.is_archived.is_(False)
        )

        if folder_id:
            stmt = stmt.where(Document.folder_id == folder_id)

        if query:
            stmt = stmt.where(
                or_(
                    Document.title.ilike(f"%{query}%"),
                    Document.description.ilike(f"%{query}%"),
                )
            )

        # Sorting
        order_col = getattr(Document, sort_by, Document.created_at)
        stmt = stmt.order_by(
            desc(order_col) if sort_order == "desc" else asc(order_col)
        )

        # Total count query (before limit/offset)
        res_all = await self.db.execute(stmt)
        total_items = len(res_all.scalars().all())

        # Pagination Limit/Offset
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total_items

    async def archive_document(self, document: Document) -> Document:
        document.is_archived = True
        await self.db.flush()
        return document

    # 👈 Missing: Restore Document
    async def restore_document(self, document: Document) -> Document:
        document.is_archived = False
        await self.db.flush()
        return document

    # 👈 Missing: Get All Versions of a Document
    async def get_document_versions(
        self, document_id: uuid.UUID
    ) -> List[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(desc(DocumentVersion.version_number))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
