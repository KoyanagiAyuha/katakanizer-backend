"""
API使用履歴リポジトリ

API使用履歴エンティティに関するデータベースアクセスを管理します。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from .base import BaseRepository
from ..database import ApiUsage


class ApiUsageRepository(BaseRepository[ApiUsage]):
    """API使用履歴リポジトリクラス"""

    def __init__(self, db: Session):
        super().__init__(db, ApiUsage)

    def record_usage(
        self,
        user_id: int,
        endpoint: str,
        response_time_ms: Optional[int] = None,
        status_code: Optional[int] = None
    ) -> ApiUsage:
        """
        API使用履歴を記録

        Args:
            user_id: ユーザーID
            endpoint: エンドポイント
            response_time_ms: レスポンス時間（ミリ秒）
            status_code: ステータスコード

        Returns:
            作成されたAPI使用履歴

        Raises:
            SQLAlchemyError: データベースエラー
        """
        return self.create(
            user_id=user_id,
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            status_code=status_code
        )

    def get_user_usage(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        endpoint: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ApiUsage]:
        """
        ユーザーのAPI使用履歴を取得

        Args:
            user_id: ユーザーID
            start_date: 開始日時
            end_date: 終了日時
            endpoint: エンドポイント（フィルタ用）
            skip: スキップ数
            limit: 取得上限

        Returns:
            API使用履歴リスト
        """
        query = self.db.query(ApiUsage).filter(ApiUsage.user_id == user_id)

        if start_date:
            query = query.filter(ApiUsage.request_date >= start_date)
        if end_date:
            query = query.filter(ApiUsage.request_date <= end_date)
        if endpoint:
            query = query.filter(ApiUsage.endpoint == endpoint)

        return query.order_by(desc(ApiUsage.request_date)).offset(skip).limit(limit).all()

    def count_user_requests(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        endpoint: Optional[str] = None
    ) -> int:
        """
        ユーザーのAPI使用回数を取得

        Args:
            user_id: ユーザーID
            start_date: 開始日時
            end_date: 終了日時
            endpoint: エンドポイント（フィルタ用）

        Returns:
            API使用回数
        """
        query = self.db.query(ApiUsage).filter(ApiUsage.user_id == user_id)

        if start_date:
            query = query.filter(ApiUsage.request_date >= start_date)
        if end_date:
            query = query.filter(ApiUsage.request_date <= end_date)
        if endpoint:
            query = query.filter(ApiUsage.endpoint == endpoint)

        return query.count()

    def get_daily_usage_count(
        self,
        user_id: int,
        date: Optional[datetime] = None,
        endpoint: Optional[str] = None
    ) -> int:
        """
        ユーザーの日次API使用回数を取得

        Args:
            user_id: ユーザーID
            date: 対象日（未指定なら今日）
            endpoint: エンドポイント（フィルタ用）

        Returns:
            日次API使用回数
        """
        if not date:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return self.count_user_requests(
            user_id=user_id,
            start_date=start_of_day,
            end_date=end_of_day,
            endpoint=endpoint
        )

    def get_usage_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        API使用統計を取得

        Args:
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            使用統計データ
        """
        query = self.db.query(ApiUsage)

        if start_date:
            query = query.filter(ApiUsage.request_date >= start_date)
        if end_date:
            query = query.filter(ApiUsage.request_date <= end_date)

        # 総リクエスト数
        total_requests = query.count()

        # エンドポイント別統計
        endpoint_stats = query.with_entities(
            ApiUsage.endpoint,
            func.count(ApiUsage.id).label('count'),
            func.avg(ApiUsage.response_time_ms).label('avg_response_time')
        ).group_by(ApiUsage.endpoint).all()

        # ユーザー別統計
        user_stats = query.with_entities(
            ApiUsage.user_id,
            func.count(ApiUsage.id).label('count')
        ).group_by(ApiUsage.user_id).order_by(desc(func.count(ApiUsage.id))).limit(10).all()

        return {
            'total_requests': total_requests,
            'endpoint_statistics': [
                {
                    'endpoint': stat.endpoint,
                    'count': stat.count,
                    'avg_response_time_ms': float(stat.avg_response_time) if stat.avg_response_time else None
                }
                for stat in endpoint_stats
            ],
            'top_users': [
                {
                    'user_id': stat.user_id,
                    'request_count': stat.count
                }
                for stat in user_stats
            ]
        }

    def cleanup_old_usage(self, older_than_days: int = 90) -> int:
        """
        古いAPI使用履歴を削除

        Args:
            older_than_days: 何日より古い履歴を削除するか

        Returns:
            削除された履歴数
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        try:
            result = self.db.query(ApiUsage).filter(
                ApiUsage.request_date <= cutoff_date
            ).delete()
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def get_peak_usage_hours(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        ピーク使用時間帯を取得

        Args:
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            時間別使用統計
        """
        query = self.db.query(
            func.extract('hour', ApiUsage.request_date).label('hour'),
            func.count(ApiUsage.id).label('count')
        )

        if start_date:
            query = query.filter(ApiUsage.request_date >= start_date)
        if end_date:
            query = query.filter(ApiUsage.request_date <= end_date)

        results = query.group_by(func.extract('hour', ApiUsage.request_date)).order_by('hour').all()

        return [
            {
                'hour': int(result.hour),
                'request_count': result.count
            }
            for result in results
        ]