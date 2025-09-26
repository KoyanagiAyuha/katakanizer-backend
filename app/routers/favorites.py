from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, Favorite, ConversionHistory, User
from ..models import HistoryResponse, LineMapping
from ..auth import get_current_user

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.post("/{conversion_id}/toggle")
def toggle_favorite(
    conversion_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """お気に入りの追加/削除をトグル"""

    # 変換履歴が存在するか確認
    conversion = db.query(ConversionHistory).filter(
        ConversionHistory.id == conversion_id
    ).first()

    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # すでにお気に入りに追加されているか確認
    existing_favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.conversion_id == conversion_id
    ).first()

    if existing_favorite:
        # お気に入りから削除
        db.delete(existing_favorite)
        db.commit()
        return {"message": "Removed from favorites", "is_favorite": False}
    else:
        # お気に入りに追加
        favorite = Favorite(
            user_id=current_user.id,
            conversion_id=conversion_id
        )
        db.add(favorite)
        db.commit()
        return {"message": "Added to favorites", "is_favorite": True}


@router.post("/{conversion_id}")
def add_to_favorites(
    conversion_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """変換履歴をお気に入りに追加"""

    # 変換履歴が存在するか確認
    conversion = db.query(ConversionHistory).filter(
        ConversionHistory.id == conversion_id
    ).first()

    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # すでにお気に入りに追加されているか確認
    existing_favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.conversion_id == conversion_id
    ).first()

    if existing_favorite:
        # すでに登録されている場合は削除（トグル動作）
        db.delete(existing_favorite)
        db.commit()
        return {"message": "Removed from favorites", "is_favorite": False}

    # お気に入りに追加
    favorite = Favorite(
        user_id=current_user.id,
        conversion_id=conversion_id
    )
    db.add(favorite)
    db.commit()

    return {"message": "Added to favorites", "is_favorite": True}


@router.delete("/{conversion_id}")
def remove_from_favorites(
    conversion_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """変換履歴をお気に入りから削除"""

    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.conversion_id == conversion_id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Not in favorites")

    db.delete(favorite)
    db.commit()

    return {"message": "Removed from favorites"}


@router.get("/my", response_model=List[HistoryResponse])
def get_my_favorites(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """現在のユーザーのお気に入りを取得"""

    favorites = db.query(ConversionHistory).join(
        Favorite, Favorite.conversion_id == ConversionHistory.id
    ).filter(
        Favorite.user_id == current_user.id
    ).order_by(Favorite.created_at.desc()).offset(offset).limit(limit).all()

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
            created_at=entry.created_at.isoformat(),
            username=entry.user.username if entry.user else "Anonymous",
            is_favorite=True
        )
        for entry in favorites
    ]


@router.get("/check/{conversion_id}")
def check_favorite_status(
    conversion_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """特定の変換履歴がお気に入りに追加されているか確認"""

    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.conversion_id == conversion_id
    ).first()

    return {"is_favorite": favorite is not None}