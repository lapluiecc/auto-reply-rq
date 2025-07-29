import os
from redis import Redis
from rq import Queue
from rq.serializers import JSONSerializer
from rq.worker import Worker
from tasks import process_message  # ✅ Import direct
from logger import log

REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)
queue = Queue("default", connection=redis_conn, serializer=JSONSerializer)

class LoggingWorker(Worker):
    def execute_job(self, job, queue):
        log(f"⚙️ Traitement du job : {job.description}")
        try:
            return super().execute_job(job, queue)
        except Exception as e:
            log(f"💥 Crash pendant le job : {e}")
            raise

if __name__ == "__main__":
    log("👷 Worker lancé")
    worker = LoggingWorker(
        [queue],
        connection=redis_conn,
        serializer=JSONSerializer,
        log_job_description=True
    )
    worker.work()
