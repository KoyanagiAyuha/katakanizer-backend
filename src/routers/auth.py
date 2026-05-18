from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_current_user, get_user_service
from ..middlewares import get_firebase_user
from ..models import User
from ..schemas import SignupRequest, UserResponse
from ..services import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    firebase_user: dict = Depends(get_firebase_user),
    user_service: UserService = Depends(get_user_service),
):
    """新規ユーザー登録（ユーザー名をフロントから受け取る）"""
    try:
        user, created = await user_service.get_or_create_user(
            firebase_uid=firebase_user["uid"],
            email=firebase_user["email"],
            username=request.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    if not created:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このアカウントは既に登録されています",
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        is_premium=user.is_premium,
        created_at=user.created_at.isoformat(),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """現在のユーザー情報取得（Firebase 認証）"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        is_premium=current_user.is_premium,
        created_at=current_user.created_at.isoformat(),
    )
