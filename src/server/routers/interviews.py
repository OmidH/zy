

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.helper.logger import getLogger
from src.datamodel.interview import Interview, InterviewCreate, InterviewModel, Question
from src.server.auth.user_middleware import OptionalHTTPBearer, get_current_user
from src.server.tasks.task_worker import create_question_audio
from src.server.utils import get_db

from src.server.queue_setup import q


interview_router = APIRouter()

logging = getLogger()


@interview_router.post("/interviews/",
                       operation_id="interviews_create",
                       response_model=InterviewModel,
                       dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())])
def create_interview(interview: InterviewCreate, db: Session = Depends(get_db)):
    new_interview = Interview()
    new_interview.business_segment = interview.business_segment
    new_interview.title = interview.title
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)

    counter = 0
    # Create questions and associate them with the interview
    for category, questions in interview.questions.items():
        for question_text in questions:
            new_question = Question(
                text=question_text,
                category=category,
                order=counter,
                interview_id=new_interview.id
            )
            db.add(new_question)
            db.commit()
            db.refresh(new_question)
            counter += 1
            q.enqueue(create_question_audio, *(new_question.id, new_interview.id, question_text))

    return new_interview


@interview_router.get("/interviews/",
                      operation_id="interviews_list",
                      response_model=List[InterviewModel],
                      dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())])
def get_interviews(db: Session = Depends(get_db)):
    interviews = db.query(Interview).all()
    return interviews


@interview_router.get("/interviews/{interview_id}",
                      operation_id="interview_by_id",
                      name="getById",
                      response_model=InterviewModel,
                      dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())])
def get_interview_by_id(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview
