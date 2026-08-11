import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import is_authenticated
from src.models.auth import User
from src.schemas.notification import NotificationCreate, NotificationResponse
from src.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse])
async def get_my_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    notification_service = NotificationService(db)
    return await notification_service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    notification_service = NotificationService(db)
    updated = await notification_service.mark_as_read(
        notification_id=notification_id, user_id=current_user.id
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied",
        )
    return updated


@router.post("/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    notification_service = NotificationService(db)
    count = await notification_service.mark_all_as_read(user_id=current_user.id)
    return {
        "message": f"Successfully marked {count} notifications as read",
        "updated_count": count,
    }


@router.post(
    "/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED
)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    """
    Create a new notification for a specific user
    """
    notification_service = NotificationService(db)
    return await notification_service.create_notification(data)
