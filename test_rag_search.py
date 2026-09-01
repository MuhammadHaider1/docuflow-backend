import asyncio

from src.core.database import SessionLocal
from src.services.rag_service import RAGService


async def main():
    async with SessionLocal() as session:
        rag_service = RAGService(db_session=session)

        # Ingested chunk ke mutabiq test query
        query = "What database does DocuFlow use for vector search?"
        print(f"User Query: {query}\n")

        results = await rag_service.search_similar_chunks(query=query, limit=2)

        print("--- Top Search Results ---")
        for idx, chunk in enumerate(results, 1):
            print(f"[{idx}] Chunk ID: {chunk.id}")
            print(f"    Text: {chunk.chunk_text}\n")


if __name__ == "__main__":
    asyncio.run(main())
