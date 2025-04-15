

from logging import getLogger
import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from markdown import markdown
import weasyprint

from src.datamodel.interview import UserModel
from src.helper.file import PathType, get_audio_path, get_wiki_path
from src.server.auth.user_middleware import OptionalHTTPBearer, get_current_user


file_router = APIRouter(prefix="/data/uploads")

logging = getLogger()


@file_router.get("/audio/{path}/{filename}", dependencies=[Depends(OptionalHTTPBearer())])
async def audio(path: str, filename: str, user: UserModel = Depends(get_current_user)):
    path_type = PathType.GLOBAL.value if path == PathType.GLOBAL.value else PathType.USER.value

    if path_type == PathType.USER.value and (not path.isdigit() or int(path) != user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    file_path = get_audio_path(path_type, filename, user)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File was not found!")

    return FileResponse(file_path, filename=filename)


@file_router.get("/wiki/{user_id}/{filename}", dependencies=[Depends(OptionalHTTPBearer())])
async def wiki(request: Request, user_id: str, filename: str, user: UserModel = Depends(get_current_user)):
    if not user_id.isdigit() or int(user_id) != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    file_path = get_wiki_path(filename, user)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File was not found!")

    with open(file_path, "r") as file:
        md_content = file.read()

    html_content = markdown(md_content)

    if request.headers.get("accept") == "application/pdf":

        css = weasyprint.CSS(filename="./pdf.css")
        pdf = weasyprint.HTML(string=html_content).write_pdf(stylesheets=[css])
        return Response(pdf, media_type="application/pdf")

    return Response(html_content, media_type="text/html")
