import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import ConversionHistory, User
from ..repositories import ApiUsageRepository, ConversionRepository, UserRepository
from .convert_utils import fill_missing_conversions
from .openai_service import converter

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversion_repo = ConversionRepository(db)
        self.user_repo = UserRepository(db)
        self.api_usage_repo = ApiUsageRepository(db)

    async def _get_daily_usage(self, user_id: int) -> int:
        """今日の変換回数を api_usage テーブルから取得"""
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        return await self.api_usage_repo.count_user_requests(
            user_id=user_id,
            start_date=today_start,
            endpoint="/api/convert",
        )

    async def check_rate_limit(self, user: User) -> bool:
        """レート制限チェック"""
        if user.is_premium:
            if user.premium_expires_at and user.premium_expires_at < datetime.utcnow():
                await self.user_repo.update(user.id, is_premium=False)
            else:
                return True

        daily_usage = await self._get_daily_usage(user.id)
        return daily_usage < settings.free_user_daily_limit

    async def get_conversion_status(self, user: User) -> dict:
        """変換ステータスを取得"""
        daily_usage = await self._get_daily_usage(user.id)
        remaining = await self._get_remaining_conversions(user, daily_usage)
        reset_time = self._get_reset_time()

        return {
            "remaining_conversions": remaining,
            "daily_limit": -1 if user.is_premium else settings.free_user_daily_limit,
            "is_premium": user.is_premium,
            "reset_time": reset_time,
            "daily_usage": daily_usage,
        }

    async def convert_text(
        self,
        text: str,
        title: str,
        language: str,
        user: User,
    ) -> dict:
        if not await self.check_rate_limit(user):
            daily_usage = await self._get_daily_usage(user.id)
            remaining = await self._get_remaining_conversions(user, daily_usage)
            reset_time = self._get_reset_time()
            raise RuntimeError(
                {
                    "message": "本日の変換回数制限に達しました",
                    "remaining_conversions": remaining,
                    "reset_time": reset_time,
                    "is_premium": False,
                    "upgrade_message": "プレミアムプランにアップグレードすると無制限に変換できます",
                }
            )

        text = text.strip()
        title = title.strip() or "無題"

        try:
            conversion_result = converter.convert_text_complete(text, language)

            if not conversion_result:
                logger.warning(f"GPT conversion failed for text: {text[:50]}...")
                conversion_result = {"phrase_mappings": []}

            initial_mappings = conversion_result["phrase_mappings"]
            word_mappings = fill_missing_conversions(text, initial_mappings)

            conversion = await self.conversion_repo.create_with_mappings(
                title=title,
                original_text=text,
                language=language,
                user_id=user.id,
                word_mappings=word_mappings,
            )

            await self._record_usage(user.id, "/api/convert")

            return {
                "id": conversion.id,
                "title": title,
                "word_mappings": word_mappings,
            }

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            raise RuntimeError("変換処理中にエラーが発生しました")

    async def convert_text_test(self, text: str, title: str, language: str) -> dict:
        """テスト用（認証不要）"""
        text = text.strip()

        try:
            conversion_result = converter.convert_text_complete(text, language)

            if not conversion_result:
                conversion_result = {"phrase_mappings": []}

            initial_mappings = conversion_result["phrase_mappings"]
            word_mappings = fill_missing_conversions(text, initial_mappings)

            return {"title": title, "word_mappings": word_mappings}

        except Exception as e:
            logger.error(f"Test conversion failed: {e}")
            return {"title": title, "word_mappings": []}

    async def get_conversion_history(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ConversionHistory]:
        return await self.conversion_repo.get_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            include_mappings=True,
        )

    async def get_conversion_by_id(self, conversion_id: int) -> ConversionHistory | None:
        return await self.conversion_repo.get_with_mappings(conversion_id)

    async def get_public_conversions(
        self, skip: int = 0, limit: int = 100
    ) -> list[ConversionHistory]:
        return await self.conversion_repo.get_public_conversions(
            skip=skip,
            limit=limit,
            include_mappings=True,
        )

    async def delete_conversion(self, conversion_id: int, user_id: int) -> bool:
        conversion = await self.conversion_repo.get_by_id(conversion_id)
        if not conversion:
            return False

        if conversion.user_id != user_id:
            raise RuntimeError("この変換履歴を削除する権限がありません")

        return await self.conversion_repo.delete(conversion_id)

    async def _record_usage(
        self, user_id: int, endpoint: str, response_time_ms: int | None = None
    ) -> None:
        """API 使用を記録"""
        await self.api_usage_repo.record_usage(
            user_id=user_id,
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            status_code=200,
        )

    async def _get_remaining_conversions(self, user: User, daily_usage: int) -> int:
        """残り変換回数を取得"""
        if user.is_premium:
            if user.premium_expires_at and user.premium_expires_at < datetime.utcnow():
                return max(0, settings.free_user_daily_limit - daily_usage)
            return -1
        return max(0, settings.free_user_daily_limit - daily_usage)

    def _get_reset_time(self) -> str:
        """リセット時刻を取得（JST 0:00）"""
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        reset_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
        reset_time_jst = reset_time + timedelta(hours=9)
        return reset_time_jst.isoformat()
