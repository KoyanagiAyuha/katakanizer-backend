from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """ユーザーリポジトリ"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        result = await self.db.execute(select(User).where(User.firebase_uid == firebase_uid))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def is_username_taken(self, username: str, exclude_user_id: int | None = None) -> bool:
        query = select(User).where(User.username == username)
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none() is not None

    async def get_or_create_by_firebase(
        self, firebase_uid: str, email: str
    ) -> tuple[User, bool]:
        """Firebase UID でユーザーを取得、なければ作成"""
        user = await self.get_by_firebase_uid(firebase_uid)
        if user:
            return user, False

        # ユーザー名をメールアドレスから生成
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while await self.is_username_taken(username):
            username = f"{base_username}{counter}"
            counter += 1

        user = await self.create(firebase_uid=firebase_uid, username=username)
        return user, True
