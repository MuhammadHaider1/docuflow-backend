import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import PermissionChecker
from src.core.database import get_db
from src.core.limiter import limiter
from src.core.security import is_authenticated
from src.models.auth import User
from src.services.rag_service import RAGService

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    answer: str


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def query_documents(
    request: Request,
    payload: QueryRequest,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    if not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    rag_service = RAGService(db_session=db)
    # Passed org_id here to satisfy method signature
    answer = await rag_service.answer_query(
        query=payload.query, org_id=x_organization_id
    )

    return QueryResponse(query=payload.query, answer=answer)


@router.post("/query-stream", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def query_documents_stream(
    request: Request,
    payload: QueryRequest,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    if not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    rag_service = RAGService(db_session=db)

    async def generate():
        async for chunk in rag_service.answer_query_stream(
            query=payload.query, org_id=x_organization_id
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")
