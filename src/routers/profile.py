from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..dependencies import get_current_user, get_database_session, get_user_service
from ..models import User
from ..repositories import ApiUsageRepository
from ..schemas import UpdateUsernameRequest, UserProfileResponse
from ..services import UserService

settings = get_settings()
router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session),
):
    """現在のユーザープロフィール情報を取得"""
    api_usage_repo = ApiUsageRepository(db)

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    daily_usage = await api_usage_repo.count_user_requests(
        user_id=current_user.id,
        start_date=today_start,
        endpoint="/api/convert",
    )

    daily_limit = -1 if current_user.is_premium else settings.free_user_daily_limit
    remaining = -1 if current_user.is_premium else max(0, daily_limit - daily_usage)

    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        is_premium=current_user.is_premium,
        premium_expires_at=(
            current_user.premium_expires_at.isoformat() if current_user.premium_expires_at else None
        ),
        daily_usage=daily_usage,
        daily_limit=daily_limit,
        remaining_conversions=remaining,
        created_at=current_user.created_at.isoformat(),
    )


@router.get("/usage/stats")
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session),
):
    """API使用統計を取得"""
    api_usage_repo = ApiUsageRepository(db)

    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    today_start = datetime(now.year, now.month, now.day)

    monthly_usage = await api_usage_repo.count_user_requests(
        user_id=current_user.id,
        start_date=start_of_month,
        endpoint="/api/convert",
    )

    daily_usage = await api_usage_repo.count_user_requests(
        user_id=current_user.id,
        start_date=today_start,
        endpoint="/api/convert",
    )

    return {
        "daily_usage": daily_usage,
        "monthly_usage": monthly_usage,
        "daily_limit": -1 if current_user.is_premium else settings.free_user_daily_limit,
        "is_premium": current_user.is_premium,
        "premium_expires_at": (
            current_user.premium_expires_at.isoformat() if current_user.premium_expires_at else None
        ),
    }


@router.put("/username")
async def update_username(
    request: UpdateUsernameRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """ユーザー名を更新"""
    try:
        updated_user = await user_service.update_username(current_user.id, request.new_username)
        if not updated_user:
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        return {"message": "ユーザー名を更新しました", "username": updated_user.username}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
