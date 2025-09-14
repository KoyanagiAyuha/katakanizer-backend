from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db, ConversionHistory, LineMapping as DBLineMapping
from ..models import HistoryResponse, LineMapping
from ..auth import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/my", response_model=List[HistoryResponse])
def get_my_conversion_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """現在のユーザーの変換履歴を取得"""
    
    results = db.query(ConversionHistory).filter(
        ConversionHistory.user_id == current_user.id
    ).order_by(ConversionHistory.created_at.desc()).limit(limit).all()
    
    return [
        HistoryResponse(
            id=entry.id,
            title=entry.title,
            original_text=entry.original_text,
            word_mappings=[
                LineMapping(
                    line=mapping.line_text,
                    casual=mapping.casual_katakana,
                    formal=mapping.formal_katakana
                )
                for mapping in entry.line_mappings
            ],
            language=entry.language,
            created_at=entry.created_at.isoformat()
        )
        for entry in results
    ]


@router.delete("/{history_id}")
def delete_conversion_history(
    history_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """変換履歴を削除（自分の履歴のみ）"""
    
    # 履歴が存在し、現在のユーザーが所有者であることを確認
    history_entry = db.query(ConversionHistory).filter(
        ConversionHistory.id == history_id,
        ConversionHistory.user_id == current_user.id
    ).first()
    
    if not history_entry:
        raise HTTPException(status_code=404, detail="History not found or unauthorized")
    
    # カスケード削除でline_mappingsも一緒に削除される
    db.delete(history_entry)
    db.commit()
    
    return {"message": "History deleted successfully"}


@router.get("/search", response_model=List[HistoryResponse])
def search_conversion_history(
    query: str = "",
    language: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """公開された変換履歴を検索"""
    
    search_query = db.query(ConversionHistory).filter(ConversionHistory.is_public == True)
    
    if query:
        search_pattern = f"%{query}%"
        search_query = search_query.filter(
            (ConversionHistory.title.like(search_pattern)) |
            (ConversionHistory.original_text.like(search_pattern))
        )
    
    if language:
        search_query = search_query.filter(ConversionHistory.language == language)
    
    results = search_query.order_by(ConversionHistory.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        HistoryResponse(
            id=entry.id,
            title=entry.title,
            original_text=entry.original_text,
            word_mappings=[
                LineMapping(
                    line=mapping.line_text,
                    casual=mapping.casual_katakana,
                    formal=mapping.formal_katakana
                )
                for mapping in entry.line_mappings
            ],
            language=entry.language,
            created_at=entry.created_at.isoformat()
        )
        for entry in results
    ]


@router.delete("/{history_id}")
def delete_conversion_history(
    history_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """変換履歴を削除（自分の履歴のみ）"""
    
    # 履歴が存在し、現在のユーザーが所有者であることを確認
    history_entry = db.query(ConversionHistory).filter(
        ConversionHistory.id == history_id,
        ConversionHistory.user_id == current_user.id
    ).first()
    
    if not history_entry:
        raise HTTPException(status_code=404, detail="History not found or unauthorized")
    
    # カスケード削除でline_mappingsも一緒に削除される
    db.delete(history_entry)
    db.commit()
    
    return {"message": "History deleted successfully"}


@router.get("/recent", response_model=List[HistoryResponse])  
def get_recent_conversions(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    """最新の変換履歴を取得"""
    
    from ..database import User
    results = db.query(ConversionHistory).outerjoin(
        User, ConversionHistory.user_id == User.id
    ).filter(
        ConversionHistory.is_public == True
    ).order_by(ConversionHistory.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        HistoryResponse(
            id=entry.id,
            title=entry.title,
            original_text=entry.original_text,
            word_mappings=[
                LineMapping(
                    line=mapping.line_text,
                    casual=mapping.casual_katakana,
                    formal=mapping.formal_katakana
                )
                for mapping in entry.line_mappings
            ],
            language=entry.language,
            created_at=entry.created_at.isoformat()
        )
        for entry in results
    ]


@router.delete("/{history_id}")
def delete_conversion_history(
    history_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """変換履歴を削除（自分の履歴のみ）"""
    
    # 履歴が存在し、現在のユーザーが所有者であることを確認
    history_entry = db.query(ConversionHistory).filter(
        ConversionHistory.id == history_id,
        ConversionHistory.user_id == current_user.id
    ).first()
    
    if not history_entry:
        raise HTTPException(status_code=404, detail="History not found or unauthorized")
    
    # カスケード削除でline_mappingsも一緒に削除される
    db.delete(history_entry)
    db.commit()
    
    return {"message": "History deleted successfully"}