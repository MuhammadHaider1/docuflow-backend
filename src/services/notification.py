import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.notification import NotificationRepository
from src.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.repository = NotificationRepository(db)

    async def send_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        notification_type: str = "INFO",
        payload: Optional[dict] = None,
    ) -> NotificationResponse:
        """User ko new notification issue karna."""
        notification_data = NotificationCreate(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            payload=payload,
        )
        return await self.create_notification(notification_data)

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[NotificationResponse]:
        """User notifications list fetch karna."""
        notifications = await self.repository.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        return [NotificationResponse.model_validate(n) for n in notifications]

    async def mark_as_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[NotificationResponse]:
        """Single notification ko read mark karna."""
        notification = await self.repository.mark_as_read(
            notification_id=notification_id, user_id=user_id
        )
        if not notification:
            return None
        return NotificationResponse.model_validate(notification)

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """User ki tamaam unread notifications mark as read karna."""
        return await self.repository.mark_all_as_read(user_id=user_id)

    async def create_notification(
        self, data: NotificationCreate
    ) -> NotificationResponse:
        """Direct schema se notification create karna."""
        notification = await self.repository.create(data)
        return NotificationResponse.model_validate(notification)
