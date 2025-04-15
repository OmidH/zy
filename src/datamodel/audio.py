from pydantic import BaseModel


class AudioModel(BaseModel):
    url: str
    user_id: int
    interview_id: int
    question_id: int
