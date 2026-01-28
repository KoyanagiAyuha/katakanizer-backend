from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_current_user, get_favorites_service
from ..models import User
from ..schemas import HistoryResponse, LineMapping
from ..services import FavoritesService

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.post("/{conversion_id}/toggle")
async def toggle_favorite(
    conversion_id: int,
    current_user: User = Depends(get_current_user),
    favorites_service: FavoritesService = Depends(get_favorites_service),
):
    """お気に入りの追加/削除をトグル"""
    try:
        return await favorites_service.toggle_favorite(current_user.id, conversion_id)
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{conversion_id}")
async def add_to_favorites(
    conversion_id: int,
    current_user: User = Depends(get_current_user),
    favorites_service: FavoritesService = Depends(get_favorites_service),
):
    """変換履歴をお気に入りに追加"""
    try:
        return await favorites_service.add_favorite(current_user.id, conversion_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{conversion_id}")
async def remove_from_favorites(
    conversion_id: int,
    current_user: User = Depends(get_current_user),
    favorites_service: FavoritesService = Depends(get_favorites_service),
):
    """変換履歴をお気に入りから削除"""
    result = await favorites_service.remove_favorite(current_user.id, conversion_id)
    if not result["is_favorited"] and result["message"] == "お気に入りに登録されていません":
        raise HTTPException(status_code=404, detail="お気に入りに登録されていません")
    return result


@router.get("/my", response_model=list[HistoryResponse])
async def get_my_favorites(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    favorites_service: FavoritesService = Depends(get_favorites_service),
):
    """現在のユーザーのお気に入りを取得"""
    favorites = await favorites_service.get_user_favorites(
        user_id=current_user.id,
        skip=offset,
        limit=limit,
    )

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
            is_favorite=True,
        )
        for entry in favorites
    ]


@router.get("/check/{conversion_id}")
async def check_favorite_status(
    conversion_id: int,
    current_user: User = Depends(get_current_user),
    favorites_service: FavoritesService = Depends(get_favorites_service),
):
    """特定の変換履歴がお気に入りに追加されているか確認"""
    return await favorites_service.get_favorite_status(current_user.id, conversion_id)
