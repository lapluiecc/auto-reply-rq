import os
from redis import Redis
from rq import Worker, Queue
from rq.serializers import JSONSerializer
import tasks  # 👈 Obligatoire pour que process_message soit connu
from logger import log

# ✅ Connexion Redis sans paramètre ssl (géré automatiquement)
REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)

# ✅ Queue "default"
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
