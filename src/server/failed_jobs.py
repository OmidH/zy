from logging import getLogger
from rq.registry import FailedJobRegistry
from rq.job import Job

from src.server.utils import get_redis
from .queue_setup import q

logging = getLogger()


def log_failed_jobs():
    failed_job_registry = FailedJobRegistry(queue=q)
    failed_job_ids = failed_job_registry.get_job_ids()

    for job_id in failed_job_ids:
        job = Job.fetch(job_id, connection=get_redis())
        logging.error(f"Job {job_id} failed: {job.exc_info}")


# Log failed jobs
log_failed_jobs()
