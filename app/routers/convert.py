"""
変換ルーター

テキスト変換関連のエンドポイントを提供します。
"""

import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import (
    get_conversion_service,
    get_current_user,
    get_current_active_user
)
from ..services import ConversionService
from ..database import User
from ..models.convert import ConvertRequest, ConvertResponse
from ..exceptions import (
    RateLimitError,
    ConversionError,
    to_http_exception,
    rate_limit_exceeded_error
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/api", tags=["convert"])


@router.get("/convert/status")
def get_conversion_status(
    current_user: User = Depends(get_current_user),
    conversion_service: ConversionService = Depends(get_conversion_service)
):
    """変換API利用状況を取得"""
    return conversion_service.get_conversion_status(current_user)


@router.post("/convert/test")
async def convert_text_test(
    request: ConvertRequest,
    conversion_service: ConversionService = Depends(get_conversion_service)
):
    """Test endpoint without authentication"""
    try:
        result = await conversion_service.convert_text_test(
            text=request.text,
            title=request.title,
            language=request.language
        )
        return result
    except Exception as e:
        logger.error(f"Test conversion failed: {str(e)}")
        # テスト用なので、エラーが発生しても基本的な結果を返す
        return {"title": request.title, "word_mappings": []}


@router.post("/convert", response_model=ConvertResponse)
async def convert_text(
    request: ConvertRequest,
    current_user: User = Depends(get_current_active_user),
    conversion_service: ConversionService = Depends(get_conversion_service)
):
    """テキスト変換"""
    start_time = time.time()

    try:
        # 変換処理実行
        result = await conversion_service.convert_text(
            text=request.text,
            title=request.title,
            language=request.language,
            user=current_user
        )

        # レスポンス時間をログに記録
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.debug(f"Conversion completed in {response_time_ms}ms")

        return ConvertResponse(**result)

    except RuntimeError as e:
        # レート制限エラーの特別処理
        error_details = str(e)
        if "制限" in error_details:
            # RuntimeErrorからRateLimitErrorに変換
            try:
                # エラーの詳細情報を解析
                import ast
                error_dict = ast.literal_eval(error_details)
                raise to_http_exception(rate_limit_exceeded_error(
                    remaining=error_dict.get("remaining_conversions", 0),
                    reset_time=error_dict.get("reset_time", ""),
                    is_premium=error_dict.get("is_premium", False)
                ))
            except (ValueError, SyntaxError):
                # 解析に失敗した場合は一般的なレート制限エラー
                status_info = conversion_service.get_conversion_status(current_user)
                raise to_http_exception(rate_limit_exceeded_error(
                    remaining=status_info["remaining_conversions"],
                    reset_time=status_info["reset_time"],
                    is_premium=status_info["is_premium"]
                ))
        else:
            # その他のランタイムエラー
            raise to_http_exception(ConversionError(str(e)))

    except Exception as e:
        logger.error(f"Unexpected error in conversion: {str(e)}")
        raise to_http_exception(ConversionError("予期しないエラーが発生しました"))