from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, User, RefreshToken
from ..auth import (
    get_password_hash, authenticate_user, create_tokens, verify_refresh_token,
    get_current_active_user, validate_password, validate_email, 
    validate_username, get_user_by_username, get_user_by_email,
    revoke_user_refresh_tokens, ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..models import (
    UserRegisterRequest, UserLoginRequest, UserResponse,
    Token, RefreshTokenRequest
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """ユーザー登録"""
    
    # バリデーション
    if not validate_username(request.username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-30 characters and contain only letters, numbers, and underscores"
        )
    
    if not validate_email(request.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    if not validate_password(request.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters and contain uppercase, lowercase, number, and special character"
        )
    
    # 重複チェック
    if get_user_by_username(db, request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # ユーザー作成
    hashed_password = get_password_hash(request.password)
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


@router.post("/login", response_model=Token)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """ユーザーログイン"""
    
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 既存のリフレッシュトークンを無効化
    revoke_user_refresh_tokens(db, user.id)
    
    # 新しいトークンペアを生成
    access_token, refresh_token = create_tokens(db, user)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=Token)
def refresh_access_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """リフレッシュトークンを使用してアクセストークンを再発行"""
    
    user = verify_refresh_token(db, request.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 古いリフレッシュトークンを無効化
    db.query(RefreshToken).filter(
        RefreshToken.token == request.refresh_token
    ).update({"revoked": True})
    db.commit()
    
    # 新しいトークンペアを生成
    access_token, refresh_token = create_tokens(db, user)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
def logout_user(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ログアウト（全リフレッシュトークンを無効化）"""
    
    revoke_user_refresh_tokens(db, current_user.id)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """現在のユーザー情報取得（要認証）"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )