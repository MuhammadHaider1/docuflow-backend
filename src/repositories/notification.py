import uuid
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import Notification
from src.schemas.notification import NotificationCreate


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, notification_in: NotificationCreate) -> Notification:
        db_notification = Notification(**notification_in.model_dump())
        self.db.add(db_notification)
        await self.db.commit()
        await self.db.refresh(db_notification)
        return db_notification

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = (
            query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Notification]:
        query = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
            .returning(Notification)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        query = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        return getattr(result, "rowcount", 0)
