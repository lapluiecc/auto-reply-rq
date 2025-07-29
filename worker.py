import os
from redis import Redis
from rq import Worker, Queue
from rq.serializers import JSONSerializer
from tasks import process_message
from logger import log

REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)

queue = Queue("default", connection=redis_conn, serializer=JSONSerializer)

if __name__ == "__main__":
    log("👷 Worker lancé")
    # 👇 Assure que RQ garde bien la tâche en mémoire
    assert process_message
    worker = Worker([queue], connection=redis_conn, serializer=JSONSerializer)
    worker.work()
