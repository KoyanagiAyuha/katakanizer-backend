from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..repositories import UserRepository


class UserService:
    """ユーザーサービス"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_or_create_user(self, firebase_uid: str, email: str) -> tuple[User, bool]:
        """Firebase ユーザーから DB ユーザーを取得または作成"""
        return await self.user_repo.get_or_create_by_firebase(firebase_uid, email)

    async def get_user_by_firebase_uid(self, firebase_uid: str) -> User | None:
        return await self.user_repo.get_by_firebase_uid(firebase_uid)

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self.user_repo.get_by_id(user_id)

    async def update_username(self, user_id: int, new_username: str) -> User | None:
        """ユーザー名を更新"""
        if len(new_username) < 3 or len(new_username) > 30:
            raise ValueError("ユーザー名は3〜30文字である必要があります")

        if await self.user_repo.is_username_taken(new_username, exclude_user_id=user_id):
            raise ValueError("このユーザー名は既に使用されています")

        return await self.user_repo.update(user_id, username=new_username)
