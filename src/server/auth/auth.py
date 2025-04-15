from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as DB
from authlib.integrations.starlette_client import OAuth
from urllib import parse

from src.datamodel.interview import User, UserModel
from src.helper.logger import getLogger
from src.helper.utils import get_env_prop
from src.server.auth.user_middleware import OptionalHTTPBearer, get_current_user, get_current_user_by_session
from src.server.utils import get_db


auth_router = APIRouter()

logging = getLogger()

# Auth0 Configuration
AUTH0_DOMAIN = get_env_prop("AUTH0_DOMAIN")
CLIENT_ID = get_env_prop("AUTH0_CLIENT_ID")
CLIENT_SECRET = get_env_prop("AUTH0_CLIENT_SECRET")
BB_URI = get_env_prop("BB_URI")
ALGORITHMS = ["RS256"]

FRONTEND = get_env_prop("FRONTEND_URI")

REDIRECT_URI = parse.urljoin(BB_URI, "/callback")
LOGIN_URL = parse.urljoin(BB_URI, "/login")

oauth = OAuth()
oauth.register(
    name='auth0',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_url=f'https://{AUTH0_DOMAIN}/authorize',
    authorize_params=None,
    access_token_url=f'https://{AUTH0_DOMAIN}/oauth/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri=REDIRECT_URI,
    client_kwargs={'scope': 'openid profile email'},
    server_metadata_url=f'https://{AUTH0_DOMAIN}/.well-known/openid-configuration',
)


@auth_router.get('/login')
async def login(request: Request):
    redirect_uri = REDIRECT_URI

    return await oauth.auth0.authorize_redirect(request, redirect_uri)


@auth_router.get('/whoami',
                 operation_id="whoami",
                 response_model=UserModel,
                 dependencies=[Depends(OptionalHTTPBearer())])
async def whoami(request: Request, user=Depends(get_current_user)):
    return user


@auth_router.get('/callback')
async def callback(request: Request, db: DB = Depends(get_db)):
    try:
        token = await oauth.auth0.authorize_access_token(request)
    except Exception as err:
        logging.error(f"Failed to authorize token! {err}")
        raise HTTPException(status_code=401, detail="Failed to authorize token!")

    user_info = token["userinfo"]

    if user_info is None:
        raise HTTPException(status_code=401, detail="No userinfo provided!")

    username = user_info["name"]

    # connect user to db
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session['user'] = {"username": user.username, "id": user.id}

    # add timestamp to have a ttl
    request.session['last_activity_time'] = datetime.now().isoformat()

    # todo add frontend redirect url here
    return RedirectResponse(url=FRONTEND)


@auth_router.get('/logout', dependencies=[Depends(get_current_user_by_session)])
async def logout(request: Request):
    request.session.clear()
    logout_url = f'https://{AUTH0_DOMAIN}/v2/logout?client_id={CLIENT_ID}&returnTo={parse.quote_plus(LOGIN_URL)}'
    return RedirectResponse(logout_url)
