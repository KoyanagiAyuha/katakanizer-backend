import logging
import time

from fastapi import APIRouter, Depends

from ..dependencies import get_conversion_service, get_current_user
from ..exceptions import ConversionError, rate_limit_exceeded_error, to_http_exception
from ..models import User
from ..schemas import ConvertRequest, ConvertResponse
from ..services import ConversionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["convert"])


@router.get("/convert/status")
async def get_conversion_status(
    current_user: User = Depends(get_current_user),
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """変換API利用状況を取得"""
    return await conversion_service.get_conversion_status(current_user)


@router.post("/convert/test")
async def convert_text_test(
    request: ConvertRequest,
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """テスト用エンドポイント（認証不要）"""
    try:
        return await conversion_service.convert_text_test(
            text=request.text,
            title=request.title,
            language=request.language,
        )
    except Exception as e:
        logger.error(f"Test conversion failed: {e}")
        return {"title": request.title, "word_mappings": []}


@router.post("/convert", response_model=ConvertResponse)
async def convert_text(
    request: ConvertRequest,
    current_user: User = Depends(get_current_user),
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """テキスト変換"""
    start_time = time.time()

    try:
        result = await conversion_service.convert_text(
            text=request.text,
            title=request.title,
            language=request.language,
            user=current_user,
        )

        response_time_ms = int((time.time() - start_time) * 1000)
        logger.debug(f"Conversion completed in {response_time_ms}ms")

        return ConvertResponse(**result)

    except RuntimeError as e:
        error_details = str(e)
        if "制限" in error_details:
            try:
                import ast

                error_dict = ast.literal_eval(error_details)
                raise to_http_exception(
                    rate_limit_exceeded_error(
                        remaining=error_dict.get("remaining_conversions", 0),
                        reset_time=error_dict.get("reset_time", ""),
                        is_premium=error_dict.get("is_premium", False),
                    )
                )
            except (ValueError, SyntaxError):
                status_info = await conversion_service.get_conversion_status(current_user)
                raise to_http_exception(
                    rate_limit_exceeded_error(
                        remaining=status_info["remaining_conversions"],
                        reset_time=status_info["reset_time"],
                        is_premium=status_info["is_premium"],
                    )
                )
        else:
            raise to_http_exception(ConversionError(str(e)))

    except Exception as e:
        logger.error(f"Unexpected error in conversion: {e}")
        raise to_http_exception(ConversionError("予期しないエラーが発生しました"))
