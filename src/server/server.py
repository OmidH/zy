
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.datamodel.manager.sqldb_manager import create_tables
from src.helper.logger import getLogger
from src.agent import AgentSingleton
from src.helper.utils import get_env_prop
from src.server.routers.wikis import wiki_router
from src.server.routers.file import file_router
from src.server.routers.interviews import interview_router
from src.server.routers.user_interviews import user_interview_router
from src.server.routers.rating import rating_router
from src.server.auth.auth import auth_router


# load .env file
load_dotenv()

logging = getLogger()
agent = AgentSingleton()

# Sample
# def get_unfinished_tasks():
#     return [{"id": 1, "text": "Wie heißt du?"},
#             {"id": 2, "text": "Wie alt bist du?"},
#             ]


# tasks = get_unfinished_tasks()
# for task in tasks:
#     q.enqueue(create_question_audio, *(task['id'], 1, task['text']))


api = FastAPI(lifespan=create_tables)
api.add_middleware(SessionMiddleware, secret_key=get_env_prop("SESSION_SECRET_KEY"))
api.include_router(auth_router)
api.include_router(file_router)
api.include_router(interview_router)
api.include_router(user_interview_router)
api.include_router(wiki_router)
api.include_router(rating_router)


if os.getenv("ENVIRONMENT") == "local":
    logging.info('Mounting data/uploads...')
    api.mount("/data", StaticFiles(directory="data/uploads"), name="data")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Add other domains or use "*" for open access (not recommended for production)
]

api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=int(os.getenv('BB_PORT')))
