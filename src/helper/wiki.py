import json
from logging import getLogger
import re
from typing import List
from sqlalchemy.orm import Session


from src.agent import AgentSingleton
from src.datamodel.interview import AdditionalQuestion, Cost, Interview, Question, RawResponse, Response, UserModel, Wiki
from src.datamodel.prompt import PromptModel
from src.helper.file import get_wiki_path
from src.helper.utils import build_wiki_from_data


logging = getLogger()
agent = AgentSingleton()


def save_wiki(wiki: str, user: UserModel, user_interview_id: str, prompt_id: str, version: int = 1):
    logging.info(f"save_wiki: {wiki[:20]}...")

    filename = f"{user_interview_id}_{prompt_id}_{version}"

    path = get_wiki_path(filename, user)

    with open(path, "w", encoding='utf-8') as file:
        file.write(cleanup_md(wiki))
    return path


def cleanup_md(wiki: str):
    cleaned_wiki = wiki.strip().strip('`')

    if cleaned_wiki.lower().startswith('markdown'):
        cleaned_wiki = cleaned_wiki[8:]
    cleaned_wiki = cleaned_wiki.strip()

    return cleaned_wiki


def generate_summary(user_interview_id: int, db: Session):
    responses = db.query(Response).filter_by(user_interview_id=user_interview_id).all()

    if not responses:
        return "No responses found for this user interview."

    conversation: List[str] = []
    for answer in responses:
        if not answer.is_additional:
            question = db.query(Question).get(answer.question_id)
        else:
            question = db.query(AdditionalQuestion).get(answer.additional_question_id)

        conversation.append(f"system: {question.text}")
        conversation.append(f"user: {answer.text}\n{answer.audio_text}")

    return conversation

    # summary_lines = []
    # for response in responses:
    #     question = db.query(Question).get(response.question_id)
    #     if question:
    #         summary_lines.append(f"Q: {question.text} A: {response.text}")

    # summary = "\n".join(summary_lines)
    # return summary


async def generate_wiki(user: UserModel, interview_id: int, user_interview_id: int, prompt: PromptModel, db: Session):
    summary = generate_summary(user_interview_id, db)

    interview = db.query(Interview).filter_by(id=interview_id).one_or_none()
    if not interview:
        logging.error("Interview not found, setting default")
        business_segment = "Allgemein"
    business_segment = interview.business_segment

    version = 1

    wiki = await agent.generate_wiki(business_segment=business_segment,
                                     history=summary,
                                     prompt=prompt,
                                     generate_conversation=False)

    wiki_filepath = save_wiki(
        wiki=wiki.content,
        user=user,
        user_interview_id=user_interview_id,
        prompt_id=prompt.id,
        version=version
    )

    wm = Wiki(
        content=wiki.content,
        filepath=wiki_filepath,
        prompt_id=prompt.id,
        user_interview_id=user_interview_id,
        version=version
    )
    db.add(wm)

    rr = RawResponse(
        json_obj=wiki.content,
        model=wiki.model,
        tokens=wiki.tokens,
        user_interview_id=user_interview_id
    )
    db.add(rr)

    cost = Cost(
        tokens=wiki.tokens,
        model=wiki.model,
        user_interview_id=user_interview_id
    )
    db.add(cost)

    db.commit()
    return wm


async def generate_dify_wiki(user: UserModel, interview_id: int, user_interview_id: int, interview_date: str, dify_id: int, db: Session):
    summary = generate_summary(user_interview_id, db)

    logging.debug(f"generate_wiki - {summary}")

    interview = db.query(Interview).filter_by(id=interview_id).one_or_none()
    if not interview:
        logging.error("Interview not found, setting default")
        business_segment = "Allgemein"
    business_segment = interview.business_segment

    version = 1
    prompt_id = f'dify_{dify_id}'

    wiki_data = await agent.generate_dify_wiki(business_segment=business_segment,
                                               history=summary,
                                               prompt_id=dify_id,
                                               interview_date=interview_date,
                                               generate_conversation_string=True)

    logging.info(f"generate_wiki - {wiki_data}")

    wiki = build_wiki_from_data(wiki_data["data"]["outputs"])

    wiki_filepath = save_wiki(
        wiki=wiki,
        user=user,
        user_interview_id=user_interview_id,
        prompt_id=prompt_id,
        version=version
    )

    wm = Wiki(
        content=wiki,
        filepath=wiki_filepath,
        prompt_id=prompt_id,
        user_interview_id=user_interview_id,
        version=version
    )
    db.add(wm)

    rr = RawResponse(
        json_obj=json.dumps(wiki_data),
        model='dify',
        tokens=wiki_data['data']['total_tokens'],
        user_interview_id=user_interview_id
    )
    db.add(rr)

    cost = Cost(
        tokens=wiki_data['data']['total_tokens'],
        model='dify',
        user_interview_id=user_interview_id
    )
    db.add(cost)

    db.commit()
    return wm


def terminate_title(markdown: str) -> str:
    # Regular expression to match Markdown headlines
    headline_pattern = re.compile(r'^(#+)\s+(.*)', re.MULTILINE)

    # Search for the first headline
    match = headline_pattern.search(markdown)

    if match:
        # Return the headline without the Markdown syntax
        return match.group(2).strip()
    else:
        # Fall back to the first line if no headlines are found
        return markdown.split('\n', 1)[0].strip()
