from typing import Optional
from pydantic import BaseModel

from src.datamodel.interview import WikiModel


class InterviewStatusModel(BaseModel):
    status: str
    wikis: Optional[list[WikiModel]]
