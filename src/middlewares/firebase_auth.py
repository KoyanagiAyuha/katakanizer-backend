import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from ..config import get_settings

settings = get_settings()
security = HTTPBearer()


async def verify_firebase_token(token: str) -> dict:
    """Firebase ID トークンを検証して uid と email を取得"""
    try:
        jwks_url = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.firebase_project_id,
            issuer=f"https://securetoken.google.com/{settings.firebase_project_id}",
        )

        return {
            "uid": payload["user_id"],
            "email": payload.get("email"),
            "email_verified": payload.get("email_verified", False),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの有効期限が切れています",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"無効なトークンです: {e}",
        )


async def get_firebase_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Firebase 認証済みユーザー情報を取得"""
    return await verify_firebase_token(credentials.credentials)


async def get_optional_firebase_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
) -> dict | None:
    """Firebase 認証ユーザー（オプショナル）"""
    if not credentials:
        return None
    try:
        return await verify_firebase_token(credentials.credentials)
    except HTTPException:
        return None
