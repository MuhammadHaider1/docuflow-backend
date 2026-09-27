import asyncio
import os
import uuid

from src.core.database import SessionLocal
from src.services.rag_service import RAGService


async def main():
    # search_similar_chunks is tenant-scoped, so an org id is required.
    org_id = os.getenv("DOCUFLOW_ORG_ID")
    if not org_id:
        print("Set DOCUFLOW_ORG_ID to the organization whose chunks to search.")
        return

    async with SessionLocal() as session:
        rag_service = RAGService(db_session=session)

        # Ingested chunk ke mutabiq test query
        query = "What database does DocuFlow use for vector search?"
        print(f"User Query: {query}\n")

        results = await rag_service.search_similar_chunks(
            query=query, org_id=uuid.UUID(org_id), limit=2
        )

        print("--- Top Search Results ---")
        for idx, chunk in enumerate(results, 1):
            print(f"[{idx}] Chunk ID: {chunk.id}")
            print(f"    Text: {chunk.chunk_text}\n")


if __name__ == "__main__":
    asyncio.run(main())
