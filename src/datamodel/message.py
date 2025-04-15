
from pydantic import BaseModel
from enum import Enum


class Role(Enum):
    USER = 'user'
    ASSISTANT = 'assistant'
    TOOL = 'tool'
    FUNCTION = 'function'
    SYSTEM = 'system'


class MessageModel(BaseModel):
    role: Role
    content: str
    model: str = ""
    tokens: int = 0

    class Config:
        from_attributes = True
