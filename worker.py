from rq import Worker, Queue, Connection
from redis import Redis

redis_conn = Redis.from_url(
    "rediss://default:AV93AAIjcDFiMmYxMTY4MjI4NzE0MTVhOWRhZDY1YTk2YTVkMjlmNHAxMA@flexible-eft-24439.upstash.io:6379",
    decode_responses=True
)

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker(["default"])
        worker.work()
