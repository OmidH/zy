
from logging import getLogger
from sqlalchemy.orm import Session
from .sqldb_manager import engine
from src.datamodel.interview import AdditionalQuestion, Interview, Question, QuestionModel, Response, ResponseModel, UserInterview, AdditionalQuestionModel


logging = getLogger()


def get_user_interview_state(user_interview_id: int, user_question: str):
    logging.debug("get_user_interview_state - Fetching user interview state for user_interview_id: %s", user_interview_id)
    with Session(bind=engine) as session:
        user_interview = session.query(UserInterview).filter_by(id=user_interview_id).one_or_none()
        if not user_interview:
            return {"error": "User interview not found"}

        interview_id = user_interview.interview_id
        interview = session.query(Interview).filter_by(id=interview_id).one_or_none()
        if not interview:
            logging.error("Interview not found, setting default")
            business_segment = "Allgemein"
        else:
            business_segment = interview.business_segment

        # Fetch all questions for the interview
        mandatory_questions = session.query(Question).filter_by(interview_id=interview_id).all()
        optional_questions = session.query(AdditionalQuestion).filter_by(user_interview_id=user_interview_id).all()

        # Mapping of question IDs to question objects
        all_questions = {q.id: q for q in mandatory_questions + optional_questions}

        # Fetch all responses given by the user in this interview
        responses = session.query(Response).filter_by(user_interview_id=user_interview_id).all()
        answered_questions_with_responses = []
        skipped_questions = []

        # Classify each response
        for response in responses:
            if response.skipped:
                if response.question_id in all_questions:
                    skipped_questions.append(all_questions[response.question_id])
            else:
                if response.question_id in all_questions:
                    answered_questions_with_responses.append((all_questions[response.question_id], response))

        # Determine unanswered questions
        all_responded_ids = {q.id for q, _ in answered_questions_with_responses}.union({q.id for q in skipped_questions})

        # Remove the question with the same text as 'user_question'
        user_question_text = user_question.strip().lower()  # Normalize the user question text
        questions_to_remove = set()
        for q in mandatory_questions + optional_questions:
            if q.text.strip().lower() == user_question_text:
                questions_to_remove.add(q.id)

        unanswered_mandatory = [q for q in mandatory_questions if q.id not in all_responded_ids and q.id not in questions_to_remove]
        unanswered_optional = [q for q in optional_questions if q.id not in all_responded_ids and q.id not in questions_to_remove]

        # Prepare the data to return
        result = {
            "business_segment": business_segment,
            # Prepare a list of answered questions with their corresponding responses, excluding the question that matches the user's provided question text
            "answered_questions": [{"question": QuestionModel.model_validate(q).model_dump(),
                                    "response": ResponseModel.model_validate(r).model_dump()}
                                   for q, r in answered_questions_with_responses
                                   if q.text.strip().lower() != user_question.strip().lower()],
            "unanswered_mandatory_questions": [QuestionModel.model_validate(q).model_dump() for q in unanswered_mandatory],
            "unanswered_optional_questions": [AdditionalQuestionModel.model_validate(q).model_dump() for q in unanswered_optional],
            "skipped_questions": [QuestionModel.model_validate(q).model_dump() for q in skipped_questions]
        }
        logging.debug("get_user_interview_state - ", result)
        print("get_user_interview_state - ", result)
        return result


def generate_history(answered_questions):
    history = []

    for qa in answered_questions:
        response_dump = ResponseModel.model_validate(qa["response"]).model_dump()
        # for question, response in answered_questions:
        formatted_question = QuestionModel.model_validate(qa["question"]).model_dump()["text"]
        formatted_response = response_dump["text"] + ("\n" if response_dump["text"] else "") + response_dump["audio_text"]
        history.append(f"System: {formatted_question}\nUser: {formatted_response}")

    return history
