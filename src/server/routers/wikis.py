

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.helper.logger import getLogger
from src.datamodel.interview import UserInterview, UserModel, Wiki, WikiModel
from src.datamodel.wiki_update import WikiUpdateModel
from src.helper.wiki import save_wiki, terminate_title
from src.server.auth.user_middleware import OptionalHTTPBearer, get_current_user
from src.server.utils import get_db


wiki_router = APIRouter()

logging = getLogger()


@wiki_router.put("/wikis/{wiki_id}",
                 operation_id="wikis_update",
                 response_model=WikiModel,
                 dependencies=[Depends(OptionalHTTPBearer())],)
def update(wiki_id: int, update_data: WikiUpdateModel, db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):

    try:
        wiki = db.query(Wiki).filter(Wiki.id == wiki_id).first()

        if not wiki:
            raise HTTPException(status_code=404, detail="Wiki not found")

        logging.info(f"update_wiki - {wiki.id}")

        # Version 1 is AI generated Version 2 is edited by the customer
        version = wiki.version + 1 if wiki.version == 1 else wiki.version
        user_interview_id = wiki.user_interview_id

        filepath = save_wiki(
            wiki=update_data.updated_content,
            user=user,
            user_interview_id=wiki.user_interview_id,
            prompt_id=wiki.prompt_id,
            version=version
        )

        if wiki.version == 1:
            new_wiki = Wiki(
                version=version,
                content=update_data.updated_content,
                filepath=filepath,
                selected=wiki.selected,
                prompt_id=wiki.prompt_id,
                user_interview_id=user_interview_id)

            db.add(new_wiki)

            # Flush the session to get the primary key of entity_a
            db.flush()

            wiki = new_wiki
        else:
            wiki.content = update_data.updated_content

        user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).first()
        user_interview.title = terminate_title(update_data.updated_content)
        user_interview.selected_wiki = wiki.id

        db.commit()

        return wiki

    except Exception as err:
        logging.error(f"Failed to update wiki: {err}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(err))


@wiki_router.get("/user_interviews/{user_interview_id}/wikis",
                 operation_id="wikis_list",
                 response_model=List[WikiModel],
                 dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],)
def list(user_interview_id: int, db: Session = Depends(get_db)):
    # get latest version
    wikis = db.query(Wiki).filter(Wiki.user_interview_id == user_interview_id).order_by(desc(Wiki.createdAt)).order_by(desc(Wiki.version)).all()

    return wikis


@wiki_router.get("/user_interviews/{user_interview_id}/wikis/latest",
                 operation_id="latest",
                 response_model=WikiModel,
                 dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],)
def latest(user_interview_id: int, db: Session = Depends(get_db)):
    user_interview = db.query(UserInterview).filter(UserInterview.id == user_interview_id).one_or_none()

    if user_interview.selected_wiki is None:
        raise HTTPException(status_code=404, detail="No latest wiki selected.")

    wiki = db.query(Wiki).filter(Wiki.user_interview_id == user_interview_id, Wiki.id == user_interview.selected_wiki).one_or_none()

    logging.debug(f"hello: {wiki.id}")

    if wiki is None:
        raise HTTPException(status_code=404, detail="No latest wiki found.")

    return wiki


@wiki_router.post("/user_interviews/{user_interview_id}/wikis/{wiki_id}/select",
                  operation_id="select_wiki",
                  dependencies=[Depends(get_current_user), Depends(OptionalHTTPBearer())],)
def select(user_interview_id: int, wiki_id, db: Session = Depends(get_db)):
    wiki = db.query(Wiki).filter(Wiki.user_interview_id == user_interview_id, Wiki.id == wiki_id).first()

    if wiki is None:
        raise HTTPException(status_code=404, detail="Wiki not found.")

    wiki.selected = True

    # Update UserInterview title depending on the wiki title
    user_interview = db.query(UserInterview).filter_by(id=user_interview_id).one_or_none()
    user_interview.title = terminate_title(wiki.content)
    user_interview.selected_wiki = wiki.id
    # Update

    db.commit()
