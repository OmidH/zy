import json
from dotenv import load_dotenv

from src.datamodel.interview import AdditionalQuestion, Cost, Question, RawResponse, Response
from src.datamodel.manager.db_helper import generate_history, get_user_interview_state
from src.helper.file import get_audio_path

from ...agent import AgentSingleton
from ...helper.logger import getLogger
from ...datamodel.manager.sqldb_manager import SessionLocal

load_dotenv()

logging = getLogger()
agent = AgentSingleton()


async def create_question_audio(question_id, interview_id, text, is_additional=False):
    # Set the appropriate file prefix and database model based on `is_additional`
    file_prefix = 'aq' if is_additional else 'q'
    db_model = AdditionalQuestion if is_additional else Question

    # Construct file name and path
    filename = f'{file_prefix}_i{interview_id}_q{question_id}.mp3'
    path = get_audio_path("global", filename)

    # Generate text-to-speech and log the output path
    new_path = await agent.tts(text, path)
    logging.info(f"{file_prefix.upper()} i{interview_id}/q{question_id}/{text} saved to {new_path}")

    # Update the database with the new audio path
    db = SessionLocal()
    try:
        question = db.query(db_model).filter(db_model.id == question_id).first()
        if question:
            question.audio = path
            db.commit()
            logging.info(f"Updated {file_prefix} question {question_id} with new audio path: {question.audio}.")
        else:
            logging.error(f"No question found with ID {question_id}.")
    except Exception as e:
        logging.error(f"Error updating {file_prefix} question: {e}")
        db.rollback()
    finally:
        db.close()


async def background_analyse(user_question: str, user_answer: str, user_interview_id: int, response_id: int):

    logging.info(f"background_analyse - q: {user_question}\na: {user_answer}\n")

    db = SessionLocal()

    try:
        user_interview_state = get_user_interview_state(user_interview_id, user_question)

        unanswered_mandatory_questions_list = []
        for question in user_interview_state['unanswered_mandatory_questions']:
            unanswered_mandatory_questions_list.append(question['text'])

        unanswered_optional_questions_list = []
        for question in user_interview_state['unanswered_optional_questions']:
            unanswered_optional_questions_list.append(question['text'])

        skipped_questions_list = []
        for question in user_interview_state['skipped_questions']:
            skipped_questions_list.append(question['text'])

        analysed = await agent.dify_analyse(
            business_segment=user_interview_state['business_segment'],
            question=user_question,
            message=user_answer,
            history=generate_history(user_interview_state["answered_questions"]),
            mandatory_upcoming_questions=unanswered_mandatory_questions_list,
            optional_upcoming_questions=unanswered_optional_questions_list,
            skipped_questions=skipped_questions_list
        )
        logging.info(f"submit_answer - {analysed}")

        raw_response = RawResponse(
            json_obj=analysed["data"]["outputs"]["text"],
            model="zy_followup_questions",
            tokens=analysed["data"]["total_tokens"],
            response_id=response_id,
            user_interview_id=user_interview_id
        )
        db.add(raw_response)

        cost = Cost(
            tokens=analysed["data"]["total_tokens"],
            model="zy_followup_questions",
            user_interview_id=user_interview_id
        )
        db.add(cost)

        db.commit()

        json_rr = json.loads(analysed["data"]["outputs"]["text"])
        for add_q in json_rr['additional_questions']:
            additional_question = AdditionalQuestion(
                text=add_q,
                user_interview_id=user_interview_id,
                response_id=response_id
            )
            db.add(additional_question)
            db.commit()
            db.refresh(additional_question)
            await create_question_audio(
                additional_question.id,
                user_interview_id,
                add_q,
                True)

        for skip_q in json_rr['removed_optional_questions']:
            a_q = db.query(AdditionalQuestion).filter(AdditionalQuestion.text == skip_q, AdditionalQuestion.user_interview_id == user_interview_id).one_or_none()
            skipped_r = Response(user_interview_id=user_interview_id, additional_question_id=a_q.id, skipped=True, is_additional=True, by_user=False)
            logging.debug(f"Skipped additional question: {a_q.id}")
            db.add(skipped_r)
        db.commit()

    except Exception as e:
        logging.error(f"Error in background_analyse: {e}")
        db.rollback()
    finally:
        db.close()
