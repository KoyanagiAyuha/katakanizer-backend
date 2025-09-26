from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_email_verified: bool
    created_at: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class ResendVerificationRequest(BaseModel):
    email: str


class UpdateProfileRequest(BaseModel):
    username: str = None
    email: str = None
    current_password: str = None
    new_password: str = None


class UpdateUsernameRequest(BaseModel):
    new_username: str


class UpdateEmailRequest(BaseModel):
    new_email: str
    password: str


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_email_verified: bool
    is_premium: bool
    premium_expires_at: str = None
    daily_conversion_count: int
    remaining_conversions: int
    created_at: str


class RegistrationResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_email_verified: bool
    created_at: str
    message: str