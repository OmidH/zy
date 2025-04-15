from pydantic import BaseModel
from typing import List


class BulkInterviewItem(BaseModel):
    questions: str
    response: str


class BulkInterviewRequest(BaseModel):
    username: str
    interview: List[BulkInterviewItem]
