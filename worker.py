import os
from redis import Redis
from rq import Worker, Queue
from rq.serializers import JSONSerializer
from logger import log

REDIS_URL = os.getenv("REDIS_URL", "rediss://default:...")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)
queue = Queue(connection=redis_conn, serializer=JSONSerializer)

if __name__ == "__main__":
    log("👷‍♂️ Démarrage du worker RQ")
    worker = Worker([queue], connection=redis_conn, serializer=JSONSerializer)
    worker.work()
