from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..database import User, ApiUsage


def check_rate_limit(user: User, db: Session) -> bool:
    """
    ユーザーのAPI利用制限をチェック

    Returns:
        True: 利用可能
        False: 制限に達している
    """
    # プレミアムユーザーは無制限
    if user.is_premium:
        # プレミアム期限をチェック
        if user.premium_expires_at and user.premium_expires_at < datetime.utcnow():
            user.is_premium = False
            db.commit()
        else:
            return True

    # 日付が変わったらカウントをリセット
    now = datetime.utcnow()
    if user.last_conversion_reset.date() < now.date():
        user.daily_conversion_count = 0
        user.last_conversion_reset = now
        db.commit()

    # 無料ユーザーは1日5回まで
    return user.daily_conversion_count < 5


def increment_usage(user: User, endpoint: str, db: Session, response_time_ms: int = None):
    """
    API使用回数をインクリメント
    """
    # 使用履歴を記録
    usage = ApiUsage(
        user_id=user.id,
        endpoint=endpoint,
        response_time_ms=response_time_ms,
        status_code=200
    )
    db.add(usage)

    # 変換エンドポイントの場合はカウントを増やす
    if endpoint == "/api/convert":
        user.daily_conversion_count += 1

    db.commit()


def get_remaining_conversions(user: User, db: Session) -> int:
    """
    残り変換回数を取得

    Returns:
        -1: 無制限（プレミアムユーザー）
        0以上: 残り回数
    """
    # 日付が変わったらカウントをリセット
    now = datetime.utcnow()
    if user.last_conversion_reset.date() < now.date():
        user.daily_conversion_count = 0
        user.last_conversion_reset = now
        db.commit()

    if user.is_premium:
        # プレミアム期限をチェック
        if user.premium_expires_at and user.premium_expires_at < datetime.utcnow():
            user.is_premium = False
            db.commit()
            return max(0, 5 - user.daily_conversion_count)
        return -1

    return max(0, 5 - user.daily_conversion_count)


def get_reset_time() -> str:
    """
    次のリセット時刻を取得（JST）
    """
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    reset_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)

    # JSTに変換（UTC+9）
    reset_time_jst = reset_time + timedelta(hours=9)

    return reset_time_jst.isoformat()