import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, ConversionHistory, LineMapping as LineMappingDB, User
from ..models import ConvertRequest, ConvertResponse
from ..openai_service import converter
from ..auth import get_current_user
from ..services.convert_utils import fill_missing_conversions
from ..services.rate_limiter import check_rate_limit, increment_usage, get_remaining_conversions, get_reset_time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/api", tags=["convert"])


@router.get("/convert/status")
def get_conversion_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """変換API利用状況を取得"""
    remaining = get_remaining_conversions(current_user, db)
    reset_time = get_reset_time()

    return {
        "remaining_conversions": remaining,
        "daily_limit": -1 if current_user.is_premium else 5,
        "is_premium": current_user.is_premium,
        "reset_time": reset_time,
        "daily_conversion_count": current_user.daily_conversion_count
    }


@router.post("/convert/test")
async def convert_text_test(request: ConvertRequest):
    """Test endpoint without authentication"""
    text = request.text.strip()
    logger.debug(f"=== TEST CONVERT DEBUG ===")
    logger.debug(f"Input text: {text}")
    
    # 統合されたGPT呼び出し - 1回で全て取得
    conversion_result = converter.convert_text_complete(text, request.language)
    logger.debug(f"GPT result: {conversion_result}")
    
    if not conversion_result:
        logger.warning(f"GPT conversion failed, using empty result for testing: {text[:50]}...")
        conversion_result = {"phrase_mappings": []}
    
    # GPT変換が成功した場合
    initial_mappings = conversion_result["phrase_mappings"]
    logger.debug(f"Initial mappings: {initial_mappings}")
    
    # 抜け漏れをチェックして補完
    word_mappings = fill_missing_conversions(text, initial_mappings)
    logger.debug(f"Final word mappings: {word_mappings}")
    
    return {"title": request.title, "word_mappings": word_mappings}

@router.post("/convert", response_model=ConvertResponse)
async def convert_text(
    request: ConvertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # API利用制限をチェック
    if not check_rate_limit(current_user, db):
        remaining = get_remaining_conversions(current_user, db)
        reset_time = get_reset_time()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "本日の変換回数制限に達しました",
                "remaining_conversions": remaining,
                "reset_time": reset_time,
                "is_premium": False,
                "upgrade_message": "プレミアムプランにアップグレードすると無制限に変換できます"
            }
        )

    start_time = time.time()
    text = request.text.strip()
    title = request.title.strip() or "無題"
    
    # 統合されたGPT呼び出し - 1回で全て取得
    conversion_result = converter.convert_text_complete(text, request.language)
    
    if not conversion_result:
        # GPT変換が失敗した場合は空の結果でテスト
        logger.warning(f"GPT conversion failed, using empty result for testing: {text[:50]}...")
        conversion_result = {"phrase_mappings": []}
    
    # GPT変換が成功した場合
    initial_mappings = conversion_result["phrase_mappings"]
    
    # 抜け漏れをチェックして補完
    word_mappings = fill_missing_conversions(text, initial_mappings)
    logger.debug(f"Conversion successful for text length: {len(text)}, mappings: {len(word_mappings)}")
    
    # Save to history
    history_entry = ConversionHistory(
        title=title,
        original_text=text,
        language=request.language,
        user_id=current_user.id
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)
    
    # Save line mappings
    for i, mapping in enumerate(word_mappings):
        line_mapping = LineMappingDB(
            conversion_id=history_entry.id,
            line_text=mapping["line"],
            casual_katakana=mapping["casual"],
            formal_katakana=mapping["formal"],
            line_order=i
        )
        db.add(line_mapping)
    
    db.commit()

    # API使用履歴を記録
    response_time_ms = int((time.time() - start_time) * 1000)
    increment_usage(current_user, "/api/convert", db, response_time_ms)

    return ConvertResponse(
        title=title,
        word_mappings=word_mappings
    )