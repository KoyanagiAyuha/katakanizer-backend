from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database import get_db, User, ApiUsage
from ..auth import (
    get_current_user, get_password_hash, verify_password,
    validate_password, validate_email, validate_username,
    get_user_by_username, get_user_by_email
)
from ..models import (
    UpdateUsernameRequest, UpdateEmailRequest, UpdatePasswordRequest,
    UserProfileResponse
)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=UserProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """現在のユーザープロフィール情報を取得"""

    # 1日の利用制限をチェック
    now = datetime.utcnow()
    if current_user.last_conversion_reset.date() < now.date():
        # 日付が変わったらリセット
        current_user.daily_conversion_count = 0
        current_user.last_conversion_reset = now
        db.commit()

    # 残り変換回数を計算
    if current_user.is_premium:
        remaining = -1  # 無制限
    else:
        remaining = max(0, 5 - current_user.daily_conversion_count)

    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        is_premium=current_user.is_premium,
        premium_expires_at=current_user.premium_expires_at.isoformat() if current_user.premium_expires_at else None,
        daily_conversion_count=current_user.daily_conversion_count,
        remaining_conversions=remaining,
        created_at=current_user.created_at.isoformat()
    )


@router.put("/username")
def update_username(
    request: UpdateUsernameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """ユーザー名を更新"""

    # バリデーション
    if not validate_username(request.new_username):
        raise HTTPException(
            status_code=400,
            detail="ユーザー名は3〜30文字で、英数字とアンダースコアのみ使用可能です"
        )

    # 重複チェック
    if request.new_username != current_user.username:
        existing_user = get_user_by_username(db, request.new_username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="このユーザー名は既に使用されています"
            )

    # 更新
    current_user.username = request.new_username
    db.commit()

    return {"message": "ユーザー名を更新しました", "username": current_user.username}


@router.put("/email")
def update_email(
    request: UpdateEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """メールアドレスを更新"""

    # パスワード確認
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="パスワードが正しくありません"
        )

    # バリデーション
    if not validate_email(request.new_email):
        raise HTTPException(
            status_code=400,
            detail="無効なメールアドレス形式です"
        )

    # 重複チェック
    if request.new_email != current_user.email:
        existing_user = get_user_by_email(db, request.new_email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="このメールアドレスは既に登録されています"
            )

    # 更新
    current_user.email = request.new_email
    current_user.is_email_verified = False  # 再検証が必要
    db.commit()

    return {
        "message": "メールアドレスを更新しました。新しいメールアドレスの確認が必要です。",
        "email": current_user.email
    }


@router.put("/password")
def update_password(
    request: UpdatePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """パスワードを更新"""

    # 現在のパスワード確認
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="現在のパスワードが正しくありません"
        )

    # 新しいパスワードのバリデーション
    if not validate_password(request.new_password):
        raise HTTPException(
            status_code=400,
            detail="パスワードは8文字以上で、大文字、小文字、数字、特殊文字を含む必要があります"
        )

    # 同じパスワードかチェック
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="新しいパスワードは現在のパスワードと異なる必要があります"
        )

    # パスワード更新
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    return {"message": "パスワードを更新しました"}


@router.get("/usage/stats")
def get_usage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API使用統計を取得"""

    # 今月の使用回数
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)

    monthly_usage = db.query(ApiUsage).filter(
        ApiUsage.user_id == current_user.id,
        ApiUsage.request_date >= start_of_month,
        ApiUsage.endpoint == "/api/convert"
    ).count()

    # 今日の使用回数
    today_start = datetime(now.year, now.month, now.day)
    daily_usage = db.query(ApiUsage).filter(
        ApiUsage.user_id == current_user.id,
        ApiUsage.request_date >= today_start,
        ApiUsage.endpoint == "/api/convert"
    ).count()

    return {
        "daily_usage": daily_usage,
        "monthly_usage": monthly_usage,
        "daily_limit": -1 if current_user.is_premium else 5,
        "is_premium": current_user.is_premium,
        "premium_expires_at": current_user.premium_expires_at.isoformat() if current_user.premium_expires_at else None
    }