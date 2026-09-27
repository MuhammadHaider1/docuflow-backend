import asyncio
import io
import uuid

from pypdf import PdfReader
from sqlalchemy import update

from src.core.config import settings
from src.core.database import SessionLocal
from src.core.minio import client as minio_client
from src.models import Document
from src.services.rag_service import RAGService
from src.tasks import celery_app


def run_async(coro):
    """Safely execute async DB operations inside a synchronous Celery worker thread."""
    return asyncio.run(coro)


async def _process_rag_and_update_status(
    document_id: str, status: str, extracted_text: str | None = None
):
    """Save RAG chunks/embeddings and update document status."""
    doc_id = uuid.UUID(document_id)

    async with SessionLocal() as session:
        # 1. Generate & Store RAG embeddings if text exists & status is completed
        if status == "completed" and extracted_text and extracted_text.strip():
            rag_service = RAGService(db_session=session)
            await rag_service.process_and_store_document(
                document_id=doc_id, text=extracted_text
            )

        # 2. Update document status and extracted content
        values_to_update = {"processing_status": status}
        if extracted_text is not None:
            values_to_update["extracted_content"] = extracted_text

        query = update(Document).where(Document.id == doc_id).values(**values_to_update)
        await session.execute(query)
        await session.commit()


@celery_app.app.task(
    name="process_document_task", bind=True, max_retries=3, default_retry_delay=5
)
def process_document_task(
    self, document_id: str, organization_id: str, storage_key: str
):
    try:
        print(f"Processing document {document_id} from MinIO...")

        # 1. Real MinIO Object Verification
        file_stat = minio_client.stat_object(
            bucket_name=settings.MINIO_BUCKET_NAME, object_name=storage_key
        )
        print(f"File verified in MinIO! Size: {file_stat.size} bytes")

        extracted_text = ""

        if storage_key.lower().endswith(".pdf"):
            print(f"Extracting text from PDF: {storage_key}...")

            response = None
            try:
                # Fetch object stream from MINIO
                response = minio_client.get_object(
                    bucket_name=settings.MINIO_BUCKET_NAME, object_name=storage_key
                )
                pdf_bytes = io.BytesIO(response.read())

                # Read PDF content using pypdf
                reader = PdfReader(pdf_bytes)
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)

                extracted_text = "\n".join(pages_text)
                print(
                    f"Extracted {len(extracted_text)} characters from {len(reader.pages)} pages."
                )
            finally:
                if response:
                    response.close()
                    response.release_conn()

        # Success path: save embeddings & set status completed
        run_async(
            _process_rag_and_update_status(document_id, "completed", extracted_text)
        )

        return {
            "status": "COMPLETED",
            "document_id": document_id,
            "organization_id": organization_id,
        }

    except Exception as exc:
        print(f"Processing document error for {document_id}: {str(exc)}")

        if self.request.retries >= self.max_retries - 1:
            print(f"Max retries reached for document {document_id}")
            # Failure path: set status failed
            run_async(_process_rag_and_update_status(document_id, "failed", None))
            raise exc

        raise self.retry(exc=exc, countdown=5)
