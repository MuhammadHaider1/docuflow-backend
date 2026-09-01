import asyncio

from src.core.database import SessionLocal
from src.services.rag_service import RAGService


async def main():
    async with SessionLocal() as session:
        rag_service = RAGService(db_session=session)

        query = "What database and vector search mechanism does DocuFlow rely on?"
        print(f"Query: {query}\n")

        answer = await rag_service.answer_query(query=query)
        print("--- LLM Generated Answer ---")
        print(answer)


if __name__ == "__main__":
    asyncio.run(main())
