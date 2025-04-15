
from pydantic import BaseModel


class PromptModel(BaseModel):
    id: str
    prompt_text: str
