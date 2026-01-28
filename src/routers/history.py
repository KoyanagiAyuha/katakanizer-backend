from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_conversion_service, get_current_user, get_database_session
from ..models import User
from ..repositories import FavoriteRepository
from ..schemas import HistoryResponse, LineMapping
from ..services import ConversionService

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/my", response_model=list[HistoryResponse])
async def get_my_conversion_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    conversion_service: ConversionService = Depends(get_conversion_service),
    db: AsyncSession = Depends(get_database_session),
):
    """現在のユーザーの変換履歴を取得"""
    results = await conversion_service.get_conversion_history(
        user_id=current_user.id,
        limit=limit,
    )

    favorite_repo = FavoriteRepository(db)
    favorites = await favorite_repo.get_user_favorites(current_user.id, include_conversions=False)
    favorite_ids = {fav.conversion_id for fav in favorites}

    return [
        HistoryResponse(
            id=entry.id,
            title=entry.title,
            original_text=entry.original_text,
            word_mappings=[
                LineMapping(
                    line=mapping.line_text,
                    casual=mapping.casual_katakana,
                    formal=mapping.formal_katakana,
                )
                for mapping in entry.line_mappings
            ],
            language=entry.language,
            created_at=entry.created_at.isoformat(),
            username=current_user.username,
            is_favorite=entry.id in favorite_ids,
        )
        for entry in results
    ]


@router.get("/recent", response_model=list[HistoryResponse])
async def get_recent_conversions(
    limit: int = 10,
    offset: int = 0,
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """最新の公開変換履歴を取得"""
    results = await conversion_service.get_public_conversions(skip=offset, limit=limit)

    return [
        HistoryResponse(
            id=entry.id,
            title=entry.title,
            original_text=entry.original_text,
            word_mappings=[
                LineMapping(
                    line=mapping.line_text,
                    casual=mapping.casual_katakana,
                    formal=mapping.formal_katakana,
                )
                for mapping in entry.line_mappings
            ],
            language=entry.language,
            created_at=entry.created_at.isoformat(),
            username=entry.user.username if entry.user else "Anonymous",
        )
        for entry in results
    ]


@router.delete("/{history_id}")
async def delete_conversion_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    conversion_service: ConversionService = Depends(get_conversion_service),
):
    """変換履歴を削除（自分の履歴のみ）"""
    try:
        success = await conversion_service.delete_conversion(history_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="履歴が見つかりません")
        return {"message": "履歴を削除しました"}
    except RuntimeError as e:
        raise HTTPException(status_code=403, detail=str(e))
