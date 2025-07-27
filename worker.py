from redis import Redis
from rq import Worker, Queue

redis_conn = Redis.from_url(
    "rediss://default:AV93AAIjcDFiMmYxMTY4MjI4NzE0MTVhOWRhZDY1YTk2YTVkMjlmNHAxMA@flexible-eft-24439.upstash.io:6379",
    decode_responses=True
)

if __name__ == "__main__":
    queue = Queue(connection=redis_conn)
    worker = Worker(queues=[queue], connection=redis_conn)
    worker.work()
