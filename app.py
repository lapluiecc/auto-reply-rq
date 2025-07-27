import os
import json
import hmac
import hashlib
import base64
from flask import Flask, request, Response
from datetime import datetime
from redis import Redis
from rq import Queue
from rq.serializers import JSONSerializer
from tasks import process_message
from logger import log  # ✅ Log centralisé

API_KEY = os.getenv("API_KEY", "f376d32d14b058ed2383b97fd568d1b26de1b75c")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
LOG_FILE = "/tmp/log.txt"

app = Flask(__name__)

redis_conn = Redis.from_url(
    os.getenv("REDIS_URL", "rediss://default:..."), decode_responses=True
)

q = Queue(connection=redis_conn, serializer=JSONSerializer)

@app.route('/sms_auto_reply', methods=['POST'])
def sms_auto_reply():
    log("📩 Étape 1 - Requête POST reçue")

    messages_raw = request.form.get("messages")
    if not messages_raw:
        log("❌ Étape 2 - Champ 'messages' manquant")
        return "Requête invalide : messages manquants", 400

    log(f"🔎 Étape 3 - messages brut : {messages_raw}")

    if not DEBUG_MODE:
        signature = request.headers.get("X-SG-SIGNATURE")
        if not signature:
            log("❌ Étape 4.1 - Signature manquante")
            return "Signature requise", 403

        expected_hash = base64.b64encode(hmac.new(API_KEY.encode(), messages_raw.encode(), hashlib.sha256).digest()).decode()
        if signature != expected_hash:
            log(f"❌ Étape 4.2 - Signature invalide (reçue: {signature})")
            return "Signature invalide", 403
        log("✅ Étape 4.3 - Signature valide")

    try:
        messages = json.loads(messages_raw)
        log(f"✔️ Étape 5 - messages parsés avec succès : {messages}")
    except json.JSONDecodeError as e:
        log(f"❌ Étape 5 - JSON invalide : {e}")
        return "Format JSON invalide", 400

    if not isinstance(messages, list):
        log("❌ Étape 6 - Format JSON non liste")
        return "Format JSON invalide : liste attendue", 400

    for i, msg in enumerate(messages):
        try:
            log(f"➡️ Étape 7.{i} - Mise en file du message : {msg}")
            q.enqueue(process_message, json.dumps(msg))
            log(f"✅ Étape 7.{i} - Message ajouté à la queue")
        except Exception as e:
            log(f"❌ Étape 7.{i} - Échec de l'enqueue : {e}")

    log("🏁 Étape 8 - Tous les messages sont en file")
    return "✔️ Messages en cours de traitement", 200

@app.route('/logs', methods=['GET'])
def read_logs():
    if not os.path.exists(LOG_FILE):
        return Response("Aucun log trouvé", mimetype='text/plain')
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        return Response(f.read(), mimetype='text/plain')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
