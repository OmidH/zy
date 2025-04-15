import datetime
import decimal
import os
from fastapi import UploadFile
from redis import Redis
from src.datamodel.manager.sqldb_manager import SessionLocal
from src.helper.utils import get_env_prop


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def alchemy_encoder(obj):
    """JSON encoder function for SQLAlchemy special classes."""
    if isinstance(obj, datetime.date):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, decimal.Decimal):
        return float(obj)


def get_redis():
    host = get_env_prop("REDIS_HOST")
    port = get_env_prop("REDIS_PORT")

    return Redis(
        host=host,
        port=port
    )


def get_extension(file: UploadFile):
    _, file_extension = os.path.splitext(file.filename)
    return file_extension
