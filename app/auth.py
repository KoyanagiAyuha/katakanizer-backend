import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import bcrypt
import jwt
from jwt.exceptions import PyJWTError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db, User, RefreshToken
from .services.email_service import EmailService

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "your-refresh-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワード検証"""
    # bcryptは72バイトまでしかサポートしないため、長いパスワードは切り詰める
    if len(plain_password) > 72:
        plain_password = plain_password[:72]
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """パスワードハッシュ化"""
    # bcryptは72バイトまでしかサポートしないため、長いパスワードは切り詰める
    if len(password) > 72:
        password = password[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def validate_password(password: str) -> bool:
    """
    パスワードポリシー検証
    - 最低8文字
    - 大文字、小文字、数字、特殊文字を各1文字以上含む
    """
    if len(password) < 8:
        return False
    
    # 大文字チェック
    if not re.search(r"[A-Z]", password):
        return False
    
    # 小文字チェック
    if not re.search(r"[a-z]", password):
        return False
    
    # 数字チェック
    if not re.search(r"\d", password):
        return False
    
    # 特殊文字チェック
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    
    return True

def validate_email(email: str) -> bool:
    """メールアドレス形式検証"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def validate_username(username: str) -> bool:
    """
    ユーザー名検証
    - 3-30文字
    - 英数字とアンダースコアのみ
    """
    if len(username) < 3 or len(username) > 30:
        return False
    
    return re.match(r'^[a-zA-Z0-9_]+$', username) is not None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """アクセストークン作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """リフレッシュトークン作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # ユニークなトークンIDを生成
    jti = secrets.token_urlsafe(32)
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def save_refresh_token(db: Session, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
    """リフレッシュトークンをDBに保存"""
    refresh_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(refresh_token)
    db.commit()
    return refresh_token

def revoke_user_refresh_tokens(db: Session, user_id: int):
    """ユーザーの全リフレッシュトークンを無効化"""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    db.commit()

def verify_refresh_token(db: Session, token: str) -> Optional[User]:
    """リフレッシュトークン検証"""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        
        # トークンタイプ確認
        if payload.get("type") != "refresh":
            return None
            
        username: str = payload.get("sub")
        if username is None:
            return None
            
        # DBでトークンを確認
        refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not refresh_token:
            return None
            
        user = get_user_by_username(db, username)
        return user
        
    except PyJWTError:
        return None

def create_tokens(db: Session, user: User) -> Tuple[str, str]:
    """アクセストークンとリフレッシュトークンのペアを作成"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # アクセストークン作成
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # リフレッシュトークン作成
    refresh_token = create_refresh_token(
        data={"sub": user.username},
        expires_delta=refresh_token_expires
    )
    
    # リフレッシュトークンをDBに保存
    expires_at = datetime.utcnow() + refresh_token_expires
    save_refresh_token(db, user.id, refresh_token, expires_at)
    
    return access_token, refresh_token

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """ユーザー名でユーザー取得"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """メールアドレスでユーザー取得"""
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """ユーザー認証"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """現在のユーザー取得（JWT認証）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報を確認できませんでした",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        # アクセストークンであることを確認
        if payload.get("type") != "access":
            raise credentials_exception
            
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """アクティブユーザー取得"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="無効なユーザーです")
    if not current_user.is_email_verified:
        raise HTTPException(status_code=403, detail="メールアドレスが確認されていません")
    return current_user

async def send_verification_email(db: Session, user: User) -> bool:
    """メール確認用のメールを送信（JWT版）"""
    # JWTトークンを生成（DBには保存しない）
    token = EmailService.generate_verification_token(user.email)

    # メール送信
    return await EmailService.send_verification_email(user.email, user.username, token)

async def verify_email_token(db: Session, token: str) -> Optional[User]:
    """メール確認トークンを検証（JWT版）"""
    # JWTトークンからメールアドレスを取得
    email = EmailService.verify_verification_token(token)
    if not email:
        return None

    # メールアドレスでユーザーを検索
    user = get_user_by_email(db, email)
    if not user:
        return None

    # 既に確認済みでもユーザーを返す（重複リクエスト対策）
    if user.is_email_verified:
        return user

    # 未確認の場合は確認済みにする
    user.is_email_verified = True
    db.commit()
    return user

async def send_password_reset_email(db: Session, email: str) -> bool:
    """パスワードリセット用のメールを送信（JWT版）"""
    user = get_user_by_email(db, email)
    if not user:
        return False

    # JWTトークンを生成（DBには保存しない）
    token = EmailService.generate_password_reset_token(email)

    # メール送信
    return await EmailService.send_password_reset_email(user.email, user.username, token)

def verify_password_reset_token(db: Session, token: str) -> Optional[User]:
    """パスワードリセットトークンを検証（JWT版）"""
    # JWTトークンからメールアドレスを取得
    email = EmailService.verify_password_reset_token(token)
    if not email:
        return None

    # メールアドレスでユーザーを検索
    user = get_user_by_email(db, email)
    return user

def reset_password(db: Session, token: str, new_password: str) -> bool:
    """パスワードをリセット"""
    user = verify_password_reset_token(db, token)
    if not user:
        return False

    if not validate_password(new_password):
        return False

    # パスワードを更新
    user.hashed_password = get_password_hash(new_password)
    db.commit()

    # 全リフレッシュトークンを無効化（セキュリティ対策）
    revoke_user_refresh_tokens(db, user.id)

    return True