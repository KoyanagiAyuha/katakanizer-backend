from pydantic import BaseModel


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
    word_mappings: list[LineMapping]
