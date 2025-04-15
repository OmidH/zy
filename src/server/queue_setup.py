from rq import Queue

from src.server.utils import get_redis

q = Queue(connection=get_redis())
