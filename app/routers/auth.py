from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, User, RefreshToken
from ..auth import (
    get_password_hash, verify_password, authenticate_user, create_tokens, verify_refresh_token,
    get_current_active_user, validate_password, validate_email,
    validate_username, get_user_by_username, get_user_by_email,
    revoke_user_refresh_tokens, ACCESS_TOKEN_EXPIRE_MINUTES,
    send_verification_email, verify_email_token, send_password_reset_email,
    reset_password
)
from ..models import (
    UserRegisterRequest, UserLoginRequest, UserResponse,
    Token, RefreshTokenRequest, EmailVerificationRequest,
    PasswordResetRequest, PasswordResetConfirmRequest,
    ResendVerificationRequest, RegistrationResponse
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegistrationResponse)
async def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """ユーザー登録"""
    
    # バリデーション
    if not validate_username(request.username):
        raise HTTPException(
            status_code=400,
            detail="ユーザー名は3〜30文字で、英数字とアンダースコアのみ使用可能です"
        )
    
    if not validate_email(request.email):
        raise HTTPException(status_code=400, detail="無効なメールアドレス形式です")
    
    if not validate_password(request.password):
        raise HTTPException(
            status_code=400,
            detail="パスワードは8文字以上で、大文字、小文字、数字、特殊文字を含む必要があります"
        )
    
    # 重複チェック
    if get_user_by_username(db, request.username):
        raise HTTPException(status_code=400, detail="このユーザー名は既に使用されています")
    
    if get_user_by_email(db, request.email):
        raise HTTPException(status_code=400, detail="このメールアドレスは既に登録されています")
    
    # ユーザー作成
    hashed_password = get_password_hash(request.password)
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password
    )

    db.add(user)
    db.commit()
    db.refresh(user)  # userオブジェクトを最新の状態に

    # メール確認用メールを送信（トークンを生成してDBに保存）
    try:
        await send_verification_email(db, user)
        db.refresh(user)  # トークン保存後に再度refresh
    except Exception as e:
        print(f"メール送信エラー: {e}")

    return RegistrationResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        created_at=user.created_at.isoformat(),
        message="登録が完了しました！ログインする前に、メールを確認してアカウントを認証してください。"
    )


@router.post("/login", response_model=Token)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """ユーザーログイン"""

    # まずユーザーの存在を確認
    user = get_user_by_username(db, request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが間違っています",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # パスワードを検証
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが間違っています",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # メール確認チェック
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="メールアドレスが確認されていません。メールを確認して、アカウントを認証してからログインしてください。",
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
            detail="無効なリフレッシュトークンです",
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
    
    return {"message": "ログアウトしました"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """現在のユーザー情報取得（要認証）"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/verify-email")
async def verify_email(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """メールアドレス確認"""
    user = await verify_email_token(db, request.token)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="無効または期限切れの確認トークンです"
        )

    return {"message": "メールアドレスの確認が完了しました"}


@router.post("/resend-verification")
async def resend_verification_email(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """メール確認メール再送信"""
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="ユーザーが見つかりません"
        )

    if user.is_email_verified:
        raise HTTPException(
            status_code=400,
            detail="メールアドレスは既に確認済みです"
        )

    try:
        success = await send_verification_email(db, user)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="確認メールの送信に失敗しました"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="確認メールの送信に失敗しました"
        )

    return {"message": "確認メールを送信しました"}


@router.post("/request-password-reset")
async def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """パスワードリセットリクエスト"""
    if not validate_email(request.email):
        raise HTTPException(
            status_code=400,
            detail="無効なメールアドレス形式です"
        )

    try:
        success = await send_password_reset_email(db, request.email)
        # セキュリティ上、メールアドレスが存在しなくても成功レスポンスを返す
        return {"message": "該当するメールアドレスのアカウントが存在する場合、パスワードリセットリンクを送信しました"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="パスワードリセットリクエストの処理に失敗しました"
        )


@router.post("/reset-password")
def reset_user_password(request: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    """パスワードリセット実行"""
    success = reset_password(db, request.token, request.new_password)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="無効または期限切れのリセットトークン、または無効なパスワードです"
        )

    return {"message": "パスワードのリセットが完了しました"}