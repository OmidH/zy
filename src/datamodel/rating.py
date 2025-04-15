from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, func
from .manager.sqldb_manager import Base


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Integer)
    feedback = Column(String, nullable=True)
    createdAt = Column(DateTime(), default=func.now())
    user_interview_id = Column(Integer, index=True)


class RatingModel(BaseModel):
    id: int
    score: int
    feedback: Optional[str]
    createdAt: datetime
    user_interview_id: int

    class Config:
        from_attributes = True


class RatingCreate(BaseModel):
    score: int
    feedback: Optional[str]
