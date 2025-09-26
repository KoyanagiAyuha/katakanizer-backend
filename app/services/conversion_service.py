"""
変換サービス

テキスト変換関連のビジネスロジックを管理します。
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .base_service import BaseService
from ..repositories import ConversionRepository, UserRepository, ApiUsageRepository
from ..database import User, ConversionHistory
from ..config import get_settings
from ..openai_service import converter
from .convert_utils import fill_missing_conversions

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversionService(BaseService):
    """変換サービスクラス"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.conversion_repo = self._get_repository(ConversionRepository)
        self.user_repo = self._get_repository(UserRepository)
        self.api_usage_repo = self._get_repository(ApiUsageRepository)

    def check_rate_limit(self, user: User) -> bool:
        """
        ユーザーのAPI利用制限をチェック

        Args:
            user: ユーザー

        Returns:
            利用可能フラグ
        """
        # プレミアムユーザーは無制限
        if user.is_premium:
            # プレミアム期限をチェック
            if user.premium_expires_at and user.premium_expires_at < datetime.utcnow():
                self.user_repo.update(user.id, is_premium=False)
            else:
                return True

        # 日付が変わったらカウントをリセット
        now = datetime.utcnow()
        if user.last_conversion_reset.date() < now.date():
            self.user_repo.update_daily_conversion_count(user.id, 0)
            user.daily_conversion_count = 0

        # 無料ユーザーは制限チェック
        return user.daily_conversion_count < settings.free_user_daily_limit

    def get_conversion_status(self, user: User) -> Dict[str, Any]:
        """
        変換API利用状況を取得

        Args:
            user: ユーザー

        Returns:
            利用状況情報
        """
        # 日次制限のリセットチェック
        now = datetime.utcnow()
        if user.last_conversion_reset.date() < now.date():
            self.user_repo.update_daily_conversion_count(user.id, 0)
            user.daily_conversion_count = 0

        remaining = self._get_remaining_conversions(user)
        reset_time = self._get_reset_time()

        return {
            "remaining_conversions": remaining,
            "daily_limit": -1 if user.is_premium else settings.free_user_daily_limit,
            "is_premium": user.is_premium,
            "reset_time": reset_time,
            "daily_conversion_count": user.daily_conversion_count
        }

    async def convert_text(
        self,
        text: str,
        title: str,
        language: str,
        user: User
    ) -> Dict[str, Any]:
        """
        テキストを変換

        Args:
            text: 変換するテキスト
            title: タイトル
            language: 言語
            user: ユーザー

        Returns:
            変換結果

        Raises:
            RuntimeError: レート制限エラーや変換エラー
        """
        # レート制限チェック
        if not self.check_rate_limit(user):
            remaining = self._get_remaining_conversions(user)
            reset_time = self._get_reset_time()
            raise RuntimeError({
                "message": "本日の変換回数制限に達しました",
                "remaining_conversions": remaining,
                "reset_time": reset_time,
                "is_premium": False,
                "upgrade_message": "プレミアムプランにアップグレードすると無制限に変換できます"
            })

        text = text.strip()
        title = title.strip() or "無題"

        try:
            # GPT変換実行
            conversion_result = converter.convert_text_complete(text, language)

            if not conversion_result:
                logger.warning(f"GPT conversion failed for text: {text[:50]}...")
                conversion_result = {"phrase_mappings": []}

            # 初期マッピング取得
            initial_mappings = conversion_result["phrase_mappings"]

            # 抜け漏れをチェックして補完
            word_mappings = fill_missing_conversions(text, initial_mappings)

            # 変換履歴を保存
            conversion = self.conversion_repo.create_with_mappings(
                title=title,
                original_text=text,
                language=language,
                user_id=user.id,
                word_mappings=word_mappings
            )

            # 使用回数をインクリメント
            self._increment_usage(user, "/api/convert")

            logger.debug(f"Conversion successful for text length: {len(text)}, mappings: {len(word_mappings)}")

            return {
                "id": conversion.id,
                "title": title,
                "word_mappings": word_mappings
            }

        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise RuntimeError("変換処理中にエラーが発生しました")

    async def convert_text_test(
        self,
        text: str,
        title: str,
        language: str
    ) -> Dict[str, Any]:
        """
        テキストを変換（テスト用、認証不要）

        Args:
            text: 変換するテキスト
            title: タイトル
            language: 言語

        Returns:
            変換結果
        """
        text = text.strip()
        logger.debug(f"=== TEST CONVERT DEBUG ===")
        logger.debug(f"Input text: {text}")

        try:
            # GPT変換実行
            conversion_result = converter.convert_text_complete(text, language)
            logger.debug(f"GPT result: {conversion_result}")

            if not conversion_result:
                logger.warning(f"GPT conversion failed, using empty result for testing: {text[:50]}...")
                conversion_result = {"phrase_mappings": []}

            # 初期マッピング取得
            initial_mappings = conversion_result["phrase_mappings"]
            logger.debug(f"Initial mappings: {initial_mappings}")

            # 抜け漏れをチェックして補完
            word_mappings = fill_missing_conversions(text, initial_mappings)
            logger.debug(f"Final word mappings: {word_mappings}")

            return {"title": title, "word_mappings": word_mappings}

        except Exception as e:
            logger.error(f"Test conversion failed: {str(e)}")
            return {"title": title, "word_mappings": []}

    def get_conversion_history(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        ユーザーの変換履歴を取得

        Args:
            user_id: ユーザーID
            skip: スキップ数
            limit: 取得上限

        Returns:
            変換履歴リスト
        """
        return self.conversion_repo.get_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            include_mappings=True
        )

    def get_conversion_by_id(self, conversion_id: int) -> Optional[ConversionHistory]:
        """
        変換履歴をIDで取得

        Args:
            conversion_id: 変換履歴ID

        Returns:
            変換履歴またはNone
        """
        return self.conversion_repo.get_with_mappings(conversion_id)

    def get_public_conversions(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        公開変換履歴を取得

        Args:
            skip: スキップ数
            limit: 取得上限

        Returns:
            公開変換履歴リスト
        """
        return self.conversion_repo.get_public_conversions(
            skip=skip,
            limit=limit,
            include_mappings=True
        )

    def search_conversions(
        self,
        query: str,
        user_id: Optional[int] = None,
        public_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversionHistory]:
        """
        変換履歴を検索

        Args:
            query: 検索クエリ
            user_id: ユーザーID（指定時はそのユーザーの履歴のみ）
            public_only: 公開履歴のみかどうか
            skip: スキップ数
            limit: 取得上限

        Returns:
            検索結果リスト
        """
        return self.conversion_repo.search_conversions(
            search_query=query,
            user_id=user_id,
            public_only=public_only,
            skip=skip,
            limit=limit
        )

    def update_conversion_visibility(
        self,
        conversion_id: int,
        user_id: int,
        is_public: bool
    ) -> Optional[ConversionHistory]:
        """
        変換履歴の公開設定を更新

        Args:
            conversion_id: 変換履歴ID
            user_id: ユーザーID（所有者確認用）
            is_public: 公開フラグ

        Returns:
            更新された変換履歴またはNone

        Raises:
            RuntimeError: 権限エラー
        """
        conversion = self.conversion_repo.get_by_id(conversion_id)
        if not conversion:
            return None

        if conversion.user_id != user_id:
            raise RuntimeError("この変換履歴を変更する権限がありません")

        return self.conversion_repo.update_visibility(conversion_id, is_public)

    def delete_conversion(self, conversion_id: int, user_id: int) -> bool:
        """
        変換履歴を削除

        Args:
            conversion_id: 変換履歴ID
            user_id: ユーザーID（所有者確認用）

        Returns:
            削除成功フラグ

        Raises:
            RuntimeError: 権限エラー
        """
        conversion = self.conversion_repo.get_by_id(conversion_id)
        if not conversion:
            return False

        if conversion.user_id != user_id:
            raise RuntimeError("この変換履歴を削除する権限がありません")

        return self.conversion_repo.delete(conversion_id)

    def _increment_usage(self, user: User, endpoint: str, response_time_ms: Optional[int] = None) -> None:
        """API使用回数をインクリメント"""
        # 使用履歴を記録
        self.api_usage_repo.record_usage(
            user_id=user.id,
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            status_code=200
        )

        # 変換エンドポイントの場合はカウントを増やす
        if endpoint == "/api/convert":
            self.user_repo.increment_conversion_count(user.id)

    def _get_remaining_conversions(self, user: User) -> int:
        """残り変換回数を取得"""
        if user.is_premium:
            # プレミアム期限をチェック
            if user.premium_expires_at and user.premium_expires_at < datetime.utcnow():
                self.user_repo.update(user.id, is_premium=False)
                return max(0, settings.free_user_daily_limit - user.daily_conversion_count)
            return -1  # 無制限

        return max(0, settings.free_user_daily_limit - user.daily_conversion_count)

    def _get_reset_time(self) -> str:
        """次のリセット時刻を取得（JST）"""
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        reset_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)

        # JSTに変換（UTC+9）
        reset_time_jst = reset_time + timedelta(hours=9)

        return reset_time_jst.isoformat()