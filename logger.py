from datetime import datetime, timezone

LOG_FILE = "/tmp/log.txt"

def log(text):
    print(text)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {text}\n")
