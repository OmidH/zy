from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from ...helper.logger import getLogger
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
logging = getLogger()
db_type = os.getenv("BB_DB_TYPE", 'sqlite')


def get_database_url():
    database_url = os.getenv("BB_DATABASE_URL")
    # logging.info(f"get_database_url - {database_url}")
    if not database_url or "None" in database_url:
        raise SystemExit("Invalid database URL")
    return database_url


try:
    if db_type == 'postgresql':
        engine = create_engine(get_database_url())
    else:
        engine = create_engine(get_database_url(), connect_args={"check_same_thread": False})
except SQLAlchemyError as e:
    logging.error(f"Failed to create engine: {e}")
    raise SystemExit("Failed to create database engine")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@asynccontextmanager
async def create_tables(app: FastAPI):
    # This will create the tables on application startup
    Base.metadata.create_all(bind=engine)
    yield
