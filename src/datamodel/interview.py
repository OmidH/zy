from datetime import datetime
import enum
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Sequence, String, func, Enum
from sqlalchemy.orm import relationship

from .manager.sqldb_manager import Base, engine

# Definition Sequenz
increment_sequence = Sequence('increment_sequence', start=1000, increment=1)
increment_sequence.create(bind=engine)


class InterviewStateType(enum.Enum):
    active = "active"
    paused = "paused"
    stopped = "stopped"
    completed = "completed"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    user_interviews = relationship("UserInterview", back_populates="user")


class Interview(Base):
    __tablename__ = 'interviews'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=True)
    business_segment = Column(String, nullable=True)
    createdAt = Column(DateTime(), default=func.now())
    updatedAt = Column(DateTime(), default=func.now(), onupdate=func.now())
    questions = relationship("Question", back_populates="interview")


class AdditionalQuestion(Base):
    __tablename__ = 'additional_questions'
    id = Column(Integer, primary_key=True)
    text = Column(String, index=True)
    order = Column(Integer, Sequence('increment_sequence', start=1000, increment=1), default=Sequence('increment_sequence').next_value())
    category = Column(String, default="additional")
    audio = Column(String)
    createdAt = Column(DateTime(), default=func.now())
    user_interview_id = Column(Integer, ForeignKey('user_interviews.id'), index=True)
    response_id = Column(Integer, ForeignKey('responses.id'), nullable=True)


class Wiki(Base):
    __tablename__ = "wikis"
    id = Column(Integer, primary_key=True)
    prompt_id = Column(String)
    selected = Column(Boolean, default=False)
    version = Column(Integer)
    content = Column(String)
    filepath = Column(String)
    user_interview_id = Column(Integer, ForeignKey('user_interviews.id'), index=True)
    user_interview = relationship("UserInterview", back_populates="wikis")
    createdAt = Column(DateTime(), default=func.now())


class Cost(Base):
    __tablename__ = "costs"
    id = Column(Integer, primary_key=True)
    tokens = Column(Integer)
    model = Column(String)
    user_interview_id = Column(Integer, ForeignKey('user_interviews.id'), index=True)
    user_interview = relationship("UserInterview", back_populates="costs")


class UserInterview(Base):
    __tablename__ = 'user_interviews'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), index=True)
    user = relationship("User", back_populates="user_interviews")
    interview = relationship("Interview")
    interview_state = relationship("InterviewState", back_populates="user_interview", uselist=False)
    wikis = relationship("Wiki", back_populates="user_interview", uselist=False)
    responses = relationship("Response", back_populates="user_interview")
    costs = relationship("Cost", back_populates="user_interview", uselist=False)
    title = Column(String, nullable=True)

    selected_wiki = Column(Integer, nullable=True)
    createdAt = Column(DateTime(), default=func.now())


class InterviewState(Base):
    __tablename__ = 'interview_state'
    id = Column(Integer, primary_key=True)
    category = Column(String, index=False)
    step = Column(Integer, index=False)
    state = Column(Enum(InterviewStateType), default=InterviewStateType.active)
    user_interview_id = Column(Integer, ForeignKey('user_interviews.id'), index=True)
    user_interview = relationship("UserInterview", back_populates="interview_state")


class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    audio = Column(String)
    category = Column(String, index=True)
    order = Column(Integer, index=False)
    interview_id = Column(Integer, ForeignKey('interviews.id'))
    interview = relationship("Interview", back_populates="questions")
    responses = relationship("Response", back_populates="question")


class Response(Base):
    __tablename__ = 'responses'
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=True)
    audio = Column(String, nullable=True)
    audio_text = Column(String, nullable=True)
    skipped = Column(Boolean, default=False)
    is_additional = Column(Boolean, default=False)
    by_user = Column(Boolean, default=True)
    question_id = Column(Integer, ForeignKey('questions.id'), index=True)
    additional_question_id = Column(Integer, ForeignKey('additional_questions.id'), index=True)
    user_interview_id = Column(Integer, ForeignKey('user_interviews.id'), index=True)
    question = relationship("Question", back_populates="responses")
    user_interview = relationship("UserInterview", back_populates="responses", foreign_keys=[user_interview_id])


class RawResponse(Base):
    __tablename__ = 'raw_responses'
    id = Column(Integer, primary_key=True)
    json_obj = Column(String)
    model = Column(String)
    tokens = Column(Integer)
    response_id = Column(Integer, ForeignKey('responses.id'), index=True, nullable=True)
    user_interview_id = Column(Integer, ForeignKey('user_interviews.id'), index=True, nullable=True)


class UserModel(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class ResponseModel(BaseModel):
    id: int
    text: Optional[str]
    audio: Optional[str]
    audio_text: Optional[str]
    question_id: Optional[int]
    additional_question_id: Optional[int]
    is_additional: bool = False
    by_user: bool = True
    skipped: bool = False

    class Config:
        from_attributes = True


class RawResponseModel(BaseModel):
    id: int
    json_obj: str
    model: str
    tokens: int
    response_id: Optional[int]
    user_interview_id: Optional[int]


class QuestionModel(BaseModel):
    id: int
    text: str
    audio: Optional[str]
    category: Optional[str]
    order: int
    interview_id: int

    class Config:
        from_attributes = True


class WikiModel(BaseModel):
    id: int

    prompt_id: str
    selected: bool

    version: int
    content: str
    filepath: str
    user_interview_id: int

    createdAt: datetime

    class Config:
        from_attributes = True


class CostModel(BaseModel):
    id: int
    tokens: int
    model: str
    user_interview_id: int

    class Config:
        from_attributes = True


class InterviewStateModel(BaseModel):
    id: int
    category: Optional[str]
    step: Optional[int]
    state: Optional[InterviewStateType]
    user_interview_id: int

    class Config:
        from_attributes = True


class InterviewModel(BaseModel):
    id: int
    title: Optional[str]
    business_segment: Optional[str]
    questions: List[QuestionModel] = []

    class Config:
        from_attributes = True


class InterviewCreate(BaseModel):
    title: Optional[str]
    business_segment: Optional[str]
    questions: Dict[str, List[str]]


class UserInterviewCreate(BaseModel):
    interview_id: int


class UserInterviewModel(BaseModel):
    id: int
    user_id: int
    interview_id: int
    interview_state: Optional[InterviewStateModel]
    responses: List[ResponseModel] = []

    title: Optional[str]
    selected_wiki: Optional[int]
    createdAt: datetime

    class Config:
        from_attributes = True


class AdditionalQuestionModel(BaseModel):
    id: int
    text: str
    order: int
    audio: str
    category: str
    user_interview_id: int
    response_id: int

    class Config:
        from_attributes = True


class UserInterviewPosition(BaseModel):
    step: int
    num_questions: int
    state: Optional[InterviewStateType]
