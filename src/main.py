from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.v1 import comment
from src.api.v1.audit import router as audit_router
from src.api.v1.auth import router as auth_router
from src.api.v1.documents import router as doc_router
from src.api.v1.notification import router as notification_router
from src.api.v1.organizations import router as org_router
from src.api.v1.rbac import router as rbac_router
from src.core.database import engine
from src.core.limiter import limiter
from src.models import Base
from src.services.storage import storage_manager


# 1. Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Database tables schema verification
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Storage bucket initialization
    await storage_manager.initialize_bucket()

    yield
    # Shutdown logic (if needed in future)


# 2. FastAPI Application Instance Setup
app = FastAPI(title="DocuFlow API", lifespan=lifespan)

# SlowAPI Limiter Middleware & Exception Handlers
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# 3. Router Inclusions
app.include_router(org_router, prefix="/api/v1", tags=["Organizations"])
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(doc_router, prefix="/api/v1", tags=["Documents & Folders"])
app.include_router(rbac_router, prefix="/api/v1", tags=["RBAC"])
app.include_router(comment.router, prefix="/api/v1", tags=["Comments"])
app.include_router(audit_router, prefix="/api/v1", tags=["Audit Logs"])
app.include_router(notification_router, prefix="/api/v1", tags=["Notifications"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "DocuFlow API"}
