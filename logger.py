import os
from datetime import datetime, timezone

LOG_FILE = "/tmp/log.txt"

def log(text):
    print(text)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {text}\n")
    except Exception as e:
        print(f"[LOGGER ERROR] {e}")
