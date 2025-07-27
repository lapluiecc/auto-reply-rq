from redis import Redis
from rq import Worker, Queue
from rq.serializers import JSONSerializer
from tasks import process_message  # ✅ Import de la fonction depuis tasks.py
import os
from datetime import datetime, timezone

REDIS_URL = os.getenv("REDIS_URL", "rediss://default:AV93AAIjcDFiMmYxMTY4MjI4NzE0MTVhOWRhZDY1YTk2YTVkMjlmNHAxMA@flexible-eft-24439.upstash.io:6379")
LOG_FILE = "/tmp/log.txt"

# Connexion Redis
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)

# Queue avec serializer JSON
queue = Queue(connection=redis_conn, serializer=JSONSerializer)

def log(text):
    print(text)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {text}\n")

if __name__ == "__main__":
    log("👷‍♂️ Démarrage du worker RQ")
    worker = Worker([queue], connection=redis_conn, serializer=JSONSerializer)
    worker.work()
