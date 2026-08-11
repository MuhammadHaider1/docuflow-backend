from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1 import comment
from src.api.v1.audit import router as audit_router
from src.api.v1.auth import router as auth_router
from src.api.v1.documents import router as doc_router
from src.api.v1.notification import router as notification_router
from src.api.v1.organizations import router as org_router
from src.api.v1.rbac import router as rbac_router
from src.core.database import SessionLocal, engine

# Teeno seeders import karein
from src.models import Base, Membership, Organization, RefreshToken, Role, User
from src.services.storage import storage_manager


# 1. Lifespan context manager define karein
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: Database tables create karna
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Database seeding and initialization

        # Bucket initialization
        await storage_manager.initialize_bucket()

    yield


# 2. app instance mein lifespan pass karein
app = FastAPI(title="DocuFlow Api", lifespan=lifespan)

# 3. Routers include karein
app.include_router(org_router, prefix="/api/v1", tags=["Organizations"])
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(doc_router, prefix="/api/v1", tags=["Documents & Folders"])
app.include_router(rbac_router, prefix="/api/v1", tags=["RBAC"])
# src/api/v1/api.py (ya jahan aap ke baaki routers registered hain)

app.include_router(comment.router, tags=["Comments"])

app.include_router(audit_router, prefix="/api/v1", tags=["Audit Logs"])
app.include_router(notification_router, prefix="/api/v1", tags=["Notifications"])
