# Dependency to get the current user based on the session
from datetime import datetime, timedelta
import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from literalai import Optional
from sqlalchemy.orm import Session as DB

from src.datamodel.interview import User
from src.helper.logger import getLogger
from src.server.utils import get_db


SECRET_KEY = os.getenv('SECRET_KEY', "easysecret")

logging = getLogger()


async def get_current_user(request: Request, db: DB = Depends(get_db)) -> User:
    # first check if request has an jwt
    user = await get_current_user_by_jwt(request, db=db)

    # if no jwt is found no user was returned => check in session
    if user is None:
        user = get_current_user_by_session(request)

    return user


def get_current_user_by_session(request: Request) -> User:
    logging.debug("Try to find user in session")
    user = request.session.get("user")
    if not user:
        logging.info("Session is not valid! No user found in session.")
        request.session.clear()
        raise HTTPException(status_code=401, detail="Session is not valid!")
    # Check if session has not expired

    last_activity_time = datetime.fromisoformat(request.session.get('last_activity_time'))
    if last_activity_time and datetime.now() - last_activity_time > timedelta(days=1):
        logging.info("Session is not expired!")
        request.session.clear()  # Clear the session if it has expired
        raise HTTPException(status_code=401, detail="Session is not expired!")

    return User(id=int(user["id"]), username=user["username"])


class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        from fastapi import status
        try:
            r = await super().__call__(request)
            token = r
        except HTTPException as ex:
            assert ex.status_code == status.HTTP_403_FORBIDDEN, ex
            token = None
        return token


get_credentials = OptionalHTTPBearer()


async def get_current_user_by_jwt(request: Request, db: DB = Depends(get_db)) -> Optional[User]:
    try:
        credentials: HTTPAuthorizationCredentials = await get_credentials(request=request)
    except Exception as err:
        logging.debug(f"Could not find any credentials: {err}")
        return None

    if credentials:
        if not credentials.scheme == "Bearer":
            logging.debug("Invalid or missing authentication scheme.")
            raise HTTPException(status_code=403, detail="Invalid or missing authentication scheme.")

        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"], options={"require": ["sub"]})
        except jwt.ExpiredSignatureError:
            logging.error("Token has expired.")
            raise HTTPException(status_code=401, detail="Token has expired.")
        except jwt.InvalidTokenError as err:
            logging.error(f"Invalid token: {err}")
            raise HTTPException(status_code=401, detail="Invalid token.")

        subscriber = payload.get("sub")
        if not subscriber:
            logging.error("Token does not contain a subscriber.")
            raise HTTPException(status_code=401, detail="Token does not contain a subscriber.")

        user = db.query(User).get(subscriber)
        if user is None:
            logging.error("User from token not found.")
            raise HTTPException(status_code=403, detail="User from token not found.")

        return user
    else:
        logging.debug("No credentials provided!")
        return None
