from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    passkey: str = Field(min_length=3, max_length=16)


class ActUpdateRequest(BaseModel):
    current_act: int = Field(ge=1, le=9)


class WebSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)


class ChatRequest(BaseModel):
    phone: str = Field(min_length=3, max_length=40)
    message: str = Field(min_length=1, max_length=200)
