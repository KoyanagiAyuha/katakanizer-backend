import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, ConversionHistory, LineMapping as LineMappingDB
from ..models import ConvertRequest, ConvertResponse
from ..openai_service import converter
from ..auth import get_current_user
from ..services.convert_utils import fill_missing_conversions

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/api", tags=["convert"])


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
    current_user = Depends(get_current_user)
):
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
    
    return ConvertResponse(
        title=title,
        word_mappings=word_mappings
    )