from pydantic import BaseModel

from .convert import LineMapping


class HistoryResponse(BaseModel):
    id: int
    title: str
    original_text: str
    word_mappings: list[LineMapping]
    language: str
    created_at: str
    username: str
    is_favorite: bool = False
