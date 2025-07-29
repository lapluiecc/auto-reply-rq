import os
from redis import Redis
from rq import Worker, Queue
from rq.serializers import JSONSerializer
import tasks  # 🔥 OBLIGATOIRE : importe le fichier qui contient process_message
from logger import log

REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    ssl=True if REDIS_URL.startswith("rediss://") else False
)

queue = Queue("default", connection=redis_conn, serializer=JSONSerializer)

if __name__ == "__main__":
    log("👷 Worker lancé")
    worker = Worker(
        [queue],
        connection=redis_conn,
        serializer=JSONSerializer,
        log_job_description=True
    )
    worker.work()
