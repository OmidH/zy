

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.datamodel.rating import Rating, RatingModel, RatingCreate
from src.helper.logger import getLogger
from src.server.auth.user_middleware import OptionalHTTPBearer, get_current_user
from src.server.utils import get_db


rating_router = APIRouter()

logging = getLogger()


@rating_router.post("/user_interviews/{user_interview_id}/rate",
                    operation_id="rate",
                    response_model=RatingModel,
                    dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],)
def rate_interview(user_interview_id: int, data: RatingCreate, db: Session = Depends(get_db)):

    rating = Rating(user_interview_id=user_interview_id,
                    score=data.score,
                    feedback=data.feedback)

    db.add(rating)
    db.commit()

    return rating
