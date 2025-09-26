import secrets
from typing import Optional
import resend
from datetime import datetime, timedelta
import jwt

from ..config import get_settings

settings = get_settings()

# Resend APIの設定
if settings.resend_api_key:
    resend.api_key = settings.resend_api_key

class EmailService:
    @staticmethod
    def generate_verification_token(email: str) -> str:
        """メール確認用JWTトークンを生成"""
        payload = {
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "type": "email_verification"
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def verify_verification_token(token: str) -> Optional[str]:
        """メール確認トークンを検証し、メールアドレスを返す"""
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "email_verification":
                return None
            return payload.get("email")
        except jwt.PyJWTError:
            return None

    @staticmethod
    def generate_password_reset_token(email: str) -> str:
        """パスワードリセット用JWTトークンを生成"""
        payload = {
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "type": "password_reset"
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def verify_password_reset_token(token: str) -> Optional[str]:
        """パスワードリセットトークンを検証し、メールアドレスを返す"""
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "password_reset":
                return None
            return payload.get("email")
        except jwt.PyJWTError:
            return None

    @staticmethod
    async def send_verification_email(email: str, username: str, token: str) -> bool:
        """メール確認用メールを送信"""
        verification_url = f"{settings.frontend_url}/verify-email?token={token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>メールアドレスの確認</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h2 style="color: #333; text-align: center;">メールアドレスの確認</h2>
                <p>こんにちは、{username}さん</p>
                <p>Katakanizerへのご登録ありがとうございます。</p>
                <p>以下のボタンをクリックして、メールアドレスを確認してください：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background-color: #007bff; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        メールアドレスを確認
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">
                    このリンクは24時間で期限切れになります。
                </p>
                <p style="color: #666; font-size: 14px;">
                    もしボタンが機能しない場合は、以下のURLをブラウザにコピーしてください：<br>
                    <a href="{verification_url}">{verification_url}</a>
                </p>
            </div>
        </body>
        </html>
        """

        try:
            params = {
                "from": f"Katakanizer <{settings.from_email}>",
                "to": [email],
                "subject": "Katakanizer - メールアドレスの確認",
                "html": html_content,
            }

            response = resend.Emails.send(params)
            return True
        except Exception as e:
            print(f"メール送信エラー: {e}")
            return False

    @staticmethod
    async def send_password_reset_email(email: str, username: str, token: str) -> bool:
        """パスワードリセット用メールを送信"""
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>パスワードリセット</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h2 style="color: #333; text-align: center;">パスワードリセット</h2>
                <p>こんにちは、{username}さん</p>
                <p>パスワードのリセットリクエストを受け付けました。</p>
                <p>以下のボタンをクリックして、新しいパスワードを設定してください：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #dc3545; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        パスワードをリセット
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">
                    このリンクは1時間で期限切れになります。
                </p>
                <p style="color: #666; font-size: 14px;">
                    もしボタンが機能しない場合は、以下のURLをブラウザにコピーしてください：<br>
                    <a href="{reset_url}">{reset_url}</a>
                </p>
                <p style="color: #666; font-size: 14px;">
                    このリクエストに覚えがない場合は、このメールを無視してください。
                </p>
            </div>
        </body>
        </html>
        """

        try:
            params = {
                "from": f"Katakanizer <{settings.from_email}>",
                "to": [email],
                "subject": "Katakanizer - パスワードリセット",
                "html": html_content,
            }

            response = resend.Emails.send(params)
            return True
        except Exception as e:
            print(f"メール送信エラー: {e}")
            return False