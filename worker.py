import os
from redis import Redis
from rq import Worker, Queue
from rq.serializers import JSONSerializer
from logger import log

REDIS_URL = os.getenv("REDIS_URL", "rediss://default:AV93AAIjcDFiMmYxMTY4MjI4NzE0MTVhOWRhZDY1YTk2YTVkMjlmNHAxMA@flexible-eft-24439.upstash.io:6379")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)
queue = Queue(connection=redis_conn, serializer=JSONSerializer)

if __name__ == "__main__":
    log("👷‍♂️ Démarrage du worker RQ")
    worker = Worker([queue], connection=redis_conn, serializer=JSONSerializer)
    worker.work()
