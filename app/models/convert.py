from pydantic import BaseModel
from typing import List


class ConvertRequest(BaseModel):
    title: str = ""
    text: str
    language: str = "en"


class LineMapping(BaseModel):
    line: str
    casual: str
    formal: str


class ConvertResponse(BaseModel):
    id: int
    title: str
    word_mappings: List[LineMapping]


class HistoryResponse(BaseModel):
    id: int
    title: str
    original_text: str
    word_mappings: List[LineMapping]
    language: str
    created_at: str
    username: str
    is_favorite: bool = False