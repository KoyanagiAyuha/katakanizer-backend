from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..models import User
from ..schemas import UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """現在のユーザー情報取得（Firebase 認証）"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        is_premium=current_user.is_premium,
        created_at=current_user.created_at.isoformat(),
    )
