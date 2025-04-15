

import asyncio
import os
from typing import List
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound


from src.helper.logger import getLogger
from src.datamodel.audio import AudioModel
from src.datamodel.error import ErrorModel
from src.datamodel.interview import AdditionalQuestion, AdditionalQuestionModel, Interview, InterviewState, InterviewStateType, Question, QuestionModel, Response, ResponseModel, User, UserInterview, UserInterviewCreate, UserInterviewModel, UserInterviewPosition, UserModel
from src.datamodel.interview_status import InterviewStatusModel
from src.helper.file import get_audio_path
from src.helper.wiki import generate_dify_wiki, generate_wiki
from src.prompts.assign_prompt import assign_prompts
from src.server.auth.user_middleware import OptionalHTTPBearer, get_current_user
from src.server.tasks.task_worker import background_analyse
from src.server.utils import get_db

from src.server.queue_setup import q


from src.agent import AgentSingleton

agent = AgentSingleton()


user_interview_router = APIRouter(prefix="/user_interviews")

logging = getLogger()

DIFY_ENABLED = bool(os.getenv("DIFY_ENABLED", False))
logging.info(f"DIFY_ENABLED: {DIFY_ENABLED}")


@user_interview_router.get("/",
                           operation_id="user_interviews_list",
                           name="list",
                           response_model=List[UserInterviewModel],
                           dependencies=[Depends(OptionalHTTPBearer())])
def get_user_interviews(user=Depends(get_current_user), states: List[InterviewStateType] = Query(default=[InterviewStateType.completed, InterviewStateType.stopped]), db: Session = Depends(get_db)):
    """
    Fetches all interviews that have been started by a given user, regardless of the interview status.
    """
    user_interviews = db.query(UserInterview).join(InterviewState).filter(UserInterview.user_id == user.id, InterviewState.state.in_(states)).order_by(desc(UserInterview.createdAt)).all()
    if not user_interviews:
        raise HTTPException(status_code=404, detail="No interviews found for this user.")

    interviews = []
    for user_interview in user_interviews:
        interviews.append(UserInterviewModel.model_validate(user_interview))

    return interviews


@user_interview_router.get("/{user_interview_id}",
                           operation_id="user_interviews_id",
                           name="getById",
                           response_model=UserInterviewModel,
                           dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())])
def get_user_interview_by_id(user_interview_id: int, db: Session = Depends(get_db)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()
    if not user_interview:
        raise HTTPException(status_code=404, detail=f"Interviews not found with id={user_interview_id}.")
    return UserInterviewModel.model_validate(user_interview)


@user_interview_router.post("/",
                            operation_id="user_interviews_create",
                            name="create",
                            response_model=UserInterviewModel,
                            dependencies=[Depends(OptionalHTTPBearer())])
def create_user_interview(user_interview: UserInterviewCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    interview = db.query(Interview).filter(Interview.id == user_interview.interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    new_user_interview = UserInterview(
        user_id=user.id,
        interview_id=user_interview.interview_id
    )
    db.add(new_user_interview)
    db.commit()
    db.refresh(new_user_interview)

    print(f"{new_user_interview.createdAt}")

    new_interview_state = InterviewState(
        user_interview_id=new_user_interview.id,
        category='general',  # or another default category
        step=0,
        state=InterviewStateType.active
    )
    db.add(new_interview_state)
    db.commit()
    db.refresh(new_interview_state)

    return new_user_interview


@user_interview_router.get("/{user_interview_id}/state",
                           operation_id="user_interviews_state",
                           name="state",
                           response_model=UserInterviewPosition,
                           dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())])
def get_state_by_user_interview_id(user_interview_id: int, db: Session = Depends(get_db)):
    try:
        state = db.query(InterviewState).filter(InterviewState.user_interview_id == user_interview_id).one()
        interview_id = db.query(UserInterview).filter(UserInterview.id == user_interview_id).one().interview_id
        num_questions = db.query(Question).filter(Question.interview_id == interview_id).count()
        num_add_questions = db.query(AdditionalQuestion).filter(AdditionalQuestion.user_interview_id == user_interview_id).count()
        logging.debug(f"get_state_by_user_interview_id - {state}")
        if state:
            new_user_state = UserInterviewPosition(step=state.step,
                                                   state=state.state,
                                                   num_questions=num_add_questions + num_questions)
            return new_user_state
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "No state object found for user interview."}
            )
    except NoResultFound:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "No row was found when one was required"}
        )


@user_interview_router.get("/{user_interview_id}/history",
                           operation_id="user_interviews_history",
                           name="history",
                           dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())])  # , response_model=[{"question": QuestionModel, "response": ResponseModel}] | any)
def get_history_by_user_interview_id(user_interview_id: int, db: Session = Depends(get_db)):
    responses = db.query(Response).filter(Response.user_interview_id == user_interview_id).all()
    rets = []
    for resp in responses:
        if resp.is_additional:
            question = db.query(AdditionalQuestion).filter(AdditionalQuestion.id == resp.additional_question_id).first()
        else:
            question = db.query(Question).filter(Question.id == resp.question_id).first()
        rets.append({"question": question, "response": resp})
    return rets


@user_interview_router.post("/upload_audio",
                            operation_id="user_interviews_upload_audio",
                            name="upload_audio",
                            response_model=AudioModel,
                            dependencies=[Depends(OptionalHTTPBearer())])
def upload_audio(request: Request, file: UploadFile = File(...),
                 interview_id: int = Form(...), question_id: int = Form(...), user=Depends(get_current_user)):
    try:
        # filename = f"a_ui{interview_id}_q{question_id}_u{user.id}{get_extension(file)}"
        filename = f"a_ui{interview_id}_q{question_id}_u{user.id}.webm"
        file_location = get_audio_path("user", filename, user)
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())

        # filename = filename.replace('.webm', '.mp3')
        # output_path = get_audio_path("user", filename, user)
        # command = ['ffmpeg', '-y', '-i', file_location, '-codec:a', 'libmp3lame', '-q:a', '2', output_path]
        # try:
        #     subprocess.run(command, check=True)
        # except subprocess.CalledProcessError as e:
        #     raise HTTPException(status_code=500, detail=str(e))

        return AudioModel(url=filename, user_id=user.id, interview_id=interview_id, question_id=question_id)
    except Exception as e:
        logging.error(f"failed to upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_interview_router.post("/{user_interview_id}/submit_answer",
                            operation_id="user_interviews_submit_answer",
                            name="submit_answer",
                            response_model=ResponseModel,
                            dependencies=[Depends(OptionalHTTPBearer())])
async def submit_answer(user_interview_id: int, response: ResponseModel, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()
    if not user_interview or user_interview.interview_state.state != InterviewStateType.active:
        raise HTTPException(status_code=400, detail="User interview is not active")

    if response.skipped:
        new_response = Response(
            user_interview_id=user_interview_id,
            text="",
            audio="",
            audio_text="",
            skipped=response.skipped,
            is_additional=response.is_additional)

        if not response.is_additional:
            new_response.question_id = response.question_id
        else:
            new_response.additional_question_id = response.additional_question_id

        db.add(new_response)
        db.commit()
    else:
        transcript = ''
        if len(response.audio.strip()) > 0:
            file_path = get_audio_path("user", os.path.basename(response.audio), user)
            transcript = await agent.stt(file_path)
        else:
            transcript = ''

        new_response = Response(
            user_interview_id=user_interview_id,
            text=response.text,
            audio=response.audio,
            audio_text=transcript,
            skipped=response.skipped,
            is_additional=response.is_additional)

        if not response.is_additional:
            current_question = db.query(Question).filter_by(id=response.question_id).first()
            new_response.question_id = response.question_id
        else:
            current_question = db.query(AdditionalQuestion).filter_by(id=response.additional_question_id).first()
            new_response.additional_question_id = response.additional_question_id

        if not current_question:
            raise HTTPException(status_code=404, detail="Question not found")

        db.add(new_response)
        db.commit()
        db.refresh(new_response)

        final_answer = f"{response.text.strip()}\n{transcript.strip()}"
        final_question = f"{current_question.text}".strip()

        q.enqueue(background_analyse, *(final_question, final_answer, user_interview_id, new_response.id))

    return new_response


@user_interview_router.get("/{user_interview_id}/current_question",
                           operation_id="user_interviews_current",
                           name="current",
                           response_model=QuestionModel | AdditionalQuestionModel,
                           dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],
                           responses={
                               400: {"model": ErrorModel, "description": "Bad Request"},
                               404: {"model": ErrorModel, "description": "Not Found"}
                           })
def get_current_question(user_interview_id: int, db: Session = Depends(get_db)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()

    if not user_interview or user_interview.interview_state.state not in [InterviewStateType.active, InterviewStateType.paused]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User interview is not active or paused",
                     "current_status": user_interview.interview_state.state}
        )

    if not user_interview or user_interview.interview_state.state == InterviewStateType.completed:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User interview is already completed",
                     "current_status": user_interview.interview_state.state}
        )

    state = user_interview.interview_state

    questions = db.query(Question).filter_by(interview_id=user_interview.interview_id).order_by(Question.order).all()
    if not questions:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "No questions found",
                     "current_status": user_interview.interview_state.state}
        )

    additional_questions = db.query(AdditionalQuestion).filter_by(user_interview_id=user_interview.id).order_by(AdditionalQuestion.order).all()
    all_questions = questions + additional_questions

    logging.info(f"get_current_question - {all_questions}")

    question = all_questions[state.step]
    return question


@user_interview_router.post("/{user_interview_id}/next_question",
                            operation_id="user_interviews_next",
                            name="next",
                            response_model=QuestionModel | AdditionalQuestionModel,
                            dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],
                            responses={
                                400: {"model": ErrorModel, "description": "Bad Request"},
                                404: {"model": ErrorModel, "description": "Not Found"}
                            })
def get_next_question(user_interview_id: int, db: Session = Depends(get_db)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()

    if not user_interview:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "User interview not found"}
        )

    logging.debug(f"get_next_question - state: {user_interview.interview_state.state}")

    if user_interview.interview_state.state != InterviewStateType.active:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User interview is not active"}
        )

    questions = db.query(Question).filter(Question.interview_id == user_interview.interview_id).order_by(Question.order).all()
    additional_questions = db.query(AdditionalQuestion).filter_by(user_interview_id=user_interview.id).order_by(AdditionalQuestion.order).all()
    all_questions = questions + additional_questions

    state = user_interview.interview_state

    logging.debug(f'get_next_question - step: {state.step}, length: {len(all_questions)}')

    while state.step < len(all_questions) - 1:
        state.step += 1
        next_question = all_questions[state.step]
        response_exists = db.query(Response).filter(
            ((Response.question_id == next_question.id) | (Response.additional_question_id == next_question.id)) & (Response.user_interview_id == user_interview_id)
        ).one_or_none()

        # Check if a response exists. If not, return the next question.
        # This happens when a question has been skipped by the AI.
        if response_exists is None:
            state.category = next_question.category
            db.commit()
            return next_question

    # When all questions are checked and no further unanswered questions are found
    if state.step >= len(all_questions) - 1:
        logging.debug('get_next_question - interview completed 🎉')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "No more questions"}
        )


@user_interview_router.post("/{user_interview_id}/pause",
                            operation_id="user_interviews_pause",
                            name="pause",
                            response_model=InterviewStatusModel,
                            dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],
                            responses={
                                400: {"model": ErrorModel, "description": "Bad Request"}
                            })
def pause_user_interview(user_interview_id: int, db: Session = Depends(get_db)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()
    if not user_interview or user_interview.interview_state.state != InterviewStateType.active:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User interview is not active",
                     "current_status": user_interview.interview_state.state}
        )

    user_interview.interview_state.state = InterviewStateType.paused
    db.commit()

    return InterviewStatusModel(status="paused")


@user_interview_router.post("/{user_interview_id}/stop",
                            operation_id="user_interviews_stop",
                            name="stop",
                            response_model=InterviewStatusModel,
                            dependencies=[Depends(OptionalHTTPBearer())],
                            responses={
                                400: {"model": ErrorModel, "description": "Bad Request"}
                            })
async def stop_user_interview(user_interview_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()
    if not user_interview or user_interview.interview_state.state == InterviewStateType.stopped:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User interview is already stopped",
                     "current_status": user_interview.interview_state.state}
        )

    user_interview.interview_state.state = InterviewStateType.stopped
    db.commit()

    prompts = assign_prompts(DIFY_ENABLED)

    tasks = [
        (generate_dify_wiki(user=user,
                            interview_id=user_interview.interview_id,
                            user_interview_id=user_interview.id,
                            interview_date=user_interview.createdAt.strftime("%Y-%m-%dT%H:%M"),
                            dify_id=int(value.id),
                            db=db)
         if DIFY_ENABLED else
         generate_wiki(user=user,
                       interview_id=user_interview.interview_id,
                       user_interview_id=user_interview.id,
                       prompt=value,
                       db=db)) for value in prompts]

    wiki_models = await asyncio.gather(*tasks)

    return InterviewStatusModel(status="stopped", wikis=wiki_models)


@user_interview_router.post("/{user_interview_id}/continue",
                            operation_id="user_interviews_continue",
                            name="continue",
                            response_model=InterviewStatusModel,
                            dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],
                            responses={
                                400: {"model": ErrorModel, "description": "Bad Request"},
                                404: {"model": ErrorModel, "description": "Not Found"}
                            })
def continue_user_interview(user_interview_id: int, db: Session = Depends(get_db)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()
    if not user_interview:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "User interview not found",
                     "current_status": user_interview.interview_state.state.value}
        )
    if user_interview.interview_state and user_interview.interview_state.state == InterviewStateType.active:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User interview is already active",
                     "current_status": user_interview.interview_state.state.value}
        )

    user_interview.interview_state.state = InterviewStateType.active
    db.commit()

    return InterviewStatusModel(status="active", wikis=[])
