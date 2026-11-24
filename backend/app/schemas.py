from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    language: str | None = None


class LanguageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class LanguageResponse(BaseModel):
    language: str | None = None
