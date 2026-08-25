import asyncio
import io

from pypdf import PdfReader
from sqlalchemy import update

from src.core.config import settings
from src.core.database import SessionLocal
from src.core.minio import client as minio_client
from src.models import Document
from src.tasks import celery_app


def run_async(coro):
    """Safely execute async DB updates inside a synchronous Celery worker thread."""
    return asyncio.run(coro)


async def _update_document_status(
    document_id: str, status: str, extracted_text: str | None = None
):
    async with SessionLocal() as session:
        values_to_update = {"processing_status": status}

        if extracted_text is not None:
            values_to_update["extracted_content"] = extracted_text

        query = (
            update(Document)
            .where(Document.id == document_id)
            .values(**values_to_update)
        )

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

        run_async(_update_document_status(document_id, "completed", extracted_text))

        return {
            "status": "COMPLETED",
            "document_id": document_id,
            "organization_id": organization_id,
        }

    except Exception as exc:
        print(f"Processing document error for {document_id}: {str(exc)}")

        if self.request.retries >= self.max_retries - 1:
            print(f"Max retries reached for document {document_id}")
            run_async(_update_document_status(document_id, "failed"))
            raise exc

        raise self.retry(exc=exc, countdown=5)
