from pydantic import BaseModel


class ErrorModel(BaseModel):
    message: str
    current_status: str
