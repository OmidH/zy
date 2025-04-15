from pydantic import BaseModel


class WikiUpdateModel(BaseModel):
    updated_content: str
