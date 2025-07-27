import os
import json
import hmac
import hashlib
import base64
from flask import Flask, request, Response
from datetime import datetime
from redis import Redis
from rq import Queue
from worker import process_message

API_KEY = os.getenv("API_KEY", "f376d32d14b058ed2383b97fd568d1b26de1b75c")
DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"
LOG_FILE = "/tmp/log.txt"

app = Flask(__name__)
redis_conn = Redis()
q = Queue(connection=redis_conn)

def log(text):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.utcnow().isoformat()}] {text}\n")

@app.route('/sms_auto_reply', methods=['POST'])
def sms_auto_reply():
    log("📩 Requête POST reçue")

    messages_raw = request.form.get("messages")
    if not messages_raw:
        log("❌ messages_raw manquant")
        return "Requête invalide : messages manquants", 400

    log(f"🔎 messages brut : {messages_raw}")

    if not DEBUG_MODE and "X-SG-SIGNATURE" in request.headers:
        signature = request.headers.get("X-SG-SIGNATURE")
        expected_hash = base64.b64encode(hmac.new(API_KEY.encode(), messages_raw.encode(), hashlib.sha256).digest()).decode()
        if signature != expected_hash:
            log("❌ Signature invalide")
            return "Signature invalide", 403

    try:
        messages = json.loads(messages_raw)
        log(f"✔️ messages parsés : {messages}")
    except json.JSONDecodeError:
        log("❌ JSON invalide")
        return "Format JSON invalide", 400

    for msg in messages:
        q.enqueue(process_message, msg)

    return "✔️ Messages en cours de traitement", 200

@app.route('/logs', methods=['GET'])
def read_logs():
    if not os.path.exists(LOG_FILE):
        return Response("Aucun log trouvé", mimetype='text/plain')
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    return Response(content, mimetype='text/plain')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
