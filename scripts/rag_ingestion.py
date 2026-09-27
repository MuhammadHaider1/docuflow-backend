import asyncio
import uuid

from dotenv import load_dotenv

from src.core.database import SessionLocal  # Aapka async DB session maker
from src.models.document import Document
from src.models.organization import Organization
from src.services.rag_service import RAGService

load_dotenv()


async def test_pipeline():
    async with SessionLocal() as db:
        # 1️⃣ Sabse pehle ek dummy Organization banao (Document isse link hoga)
        sample_org = Organization(
            id=uuid.uuid4(),
            name="Test Organization",
            slug=f"test-org-{uuid.uuid4().hex[:8]}",
        )
        db.add(sample_org)
        await db.flush()  # ID commit se pehle DB mein available karne ke liye

        # 2️⃣ Ab ek dummy Document banao, usi Organization se link kar ke
        sample_document = Document(
            id=uuid.uuid4(),
            title="Sample Document",
            organization_id=sample_org.id,
        )
        db.add(sample_document)
        await db.flush()

        await db.commit()

        # 3️⃣ Ab real document.id use karo chunk banane ke liye
        rag_service = RAGService(db_session=db)

        sample_text = (
            "DocuFlow is an AI-powered document management platform. "
            "It supports semantic search using pgvector and PostgreSQL. "
            "RAG pipelines allow users to query documents using LLMs effectively."
        )

        print("Processing sample document...")
        chunks = await rag_service.process_and_store_document(
            document_id=sample_document.id, text=sample_text
        )
        print(f"Successfully stored {len(chunks)} chunks in Database with Embeddings!")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
