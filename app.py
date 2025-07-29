import os
import json
import hmac
import hashlib
import base64
from flask import Flask, request, Response
from redis import Redis
from rq import Queue
from rq.serializers import JSONSerializer
from tasks import process_message
from logger import log

API_KEY = os.getenv("API_KEY")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
LOG_FILE = "/tmp/log.txt"

app = Flask(__name__)

# ✅ Connexion Redis sécurisée automatique si rediss://
REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    ssl=True if REDIS_URL and REDIS_URL.startswith("rediss://") else False
)

# ✅ File "default" bien déclarée
q = Queue("default", connection=redis_conn, serializer=JSONSerializer)

@app.route('/sms_auto_reply', methods=['POST'])
def sms_auto_reply():
    log("\n📩 Requête POST reçue")
    messages_raw = request.form.get("messages")

    if not messages_raw:
        log("❌ Champ 'messages' manquant")
        return "messages manquants", 400

    log(f"🔎 messages brut : {messages_raw}")

    if not DEBUG_MODE:
        signature = request.headers.get("X-SG-SIGNATURE")
        if not signature:
            log("❌ Signature manquante")
            return "Signature requise", 403

        expected_hash = base64.b64encode(
            hmac.new(API_KEY.encode(), messages_raw.encode(), hashlib.sha256).digest()
        ).decode()

        if signature != expected_hash:
            log(f"❌ Signature invalide (reçue: {signature})")
            return "Signature invalide", 403
        log("✅ Signature valide")

    try:
        messages = json.loads(messages_raw)
        log(f"✔️ messages parsés : {messages}")
    except json.JSONDecodeError as e:
        log(f"❌ JSON invalide : {e}")
        return "Format JSON invalide", 400

    if not isinstance(messages, list):
        log("❌ Format JSON non liste")
        return "Liste attendue", 400

    for i, msg in enumerate(messages):
        try:
            log(f"➡️ Mise en file {i} : {msg}")
            q.enqueue(process_message, json.dumps(msg))
        except Exception as e:
            log(f"❌ Erreur file {i} : {e}")

    log("🏁 Tous les messages sont en file")
    return "OK", 200

@app.route('/logs')
def logs():
    if not os.path.exists(LOG_FILE):
        return Response("Aucun log", mimetype='text/plain')
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        return Response(f.read(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
