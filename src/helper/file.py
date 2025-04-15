from enum import Enum
from logging import getLogger
import os

from src.datamodel.interview import UserModel
from src.helper.utils import get_env_prop

logging = getLogger()


class PathType(Enum):
    GLOBAL = "global"
    USER = "user"


def get_audio_path(type: PathType, filename: str, user: UserModel = None):
    root = get_env_prop("BB_AUDIO_PATH")

    if type == PathType.USER.value and user is None:
        raise Exception("User is not defined")

    path = os.path.join(root, PathType.GLOBAL.value) if type == PathType.GLOBAL.value else os.path.join(root, str(user.id))

    create_dir(path)

    return os.path.join(path, filename)


def get_wiki_path(filename: str, user: UserModel = None):
    root = get_env_prop("BB_MD_PATH")

    path = os.path.join(root, str(user.id))

    create_dir(path)

    return os.path.join(path, filename)


def create_dir(path: str):
    if not os.path.exists(path):
        os.mkdir(path)
