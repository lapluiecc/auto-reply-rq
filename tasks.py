import os
import time
import json
from datetime import datetime, timezone
from redis import Redis
from rq.serializers import JSONSerializer

# Configuration
SERVER = os.getenv("SERVER", "https://moncolis-attente.com/")
API_KEY = os.getenv("API_KEY", "f3763d214b058ed2383b97fd568d1b26de1b75c")
SECOND_MESSAGE_LINK = os.getenv("SECOND_MESSAGE_LINK", "https://locker-colis-attente.com/183248")
REDIS_URL = os.getenv("REDIS_URL", "rediss://default:AV93AAIjcDFiMmYxMTY4MjI4NzE0MTVhOWRhZDY1YTk2YTVkMjlmNHAxMA@flexible-eft-24439.upstash.io:6379")
LOG_FILE = "/tmp/log.txt"

# Connexion Redis
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)

def log(text):
    print(text)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {text}\n")

def get_conversation_key(number):
    return f"conv:{number}"

def is_archived(number):
    return redis_conn.sismember("archived_numbers", number)

def archive_number(number):
    redis_conn.sadd("archived_numbers", number)

def mark_message_processed(number, msg_id):
    redis_conn.sadd(f"processed:{number}", msg_id)

def is_message_processed(number, msg_id):
    return redis_conn.sismember(f"processed:{number}", msg_id)

def send_request(url, post_data):
    import requests
    log(f"🌐 Envoi POST vers {url} avec data: {post_data}")
    response = requests.post(url, data=post_data)
    try:
        data = response.json()
        log(f"✅ Réponse JSON : {data}")
        return data.get("data")
    except ValueError:
        log(f"❌ Erreur : réponse non JSON : {response.text}")
        raise Exception("Réponse invalide du serveur.")

def send_single_message(number, message, device_slot):
    log(f"📦 Préparation envoi à {number} via SIM {device_slot}")
    post_data = {
        'number': number,
        'message': message,
        'devices': device_slot,
        'type': 'mms',
        'prioritize': 1,
        'key': API_KEY,
    }
    return send_request(f"{SERVER}/services/send.php", post_data)

def process_message(msg_json):
    log(f"🧩 Début traitement RQ - brut : {msg_json}")

    try:
        msg = json.loads(msg_json)
        log(f"🧩 Message décodé : {msg}")
    except Exception as e:
        log(f"❌ JSON invalide dans worker : {e}")
        return

    msg_id = msg.get("ID")
    number = msg.get("number")
    device_id = msg.get("deviceID")

    if not msg_id or not number or not device_id:
        log(f"⛔️ Champs manquants : ID={msg_id}, number={number}, deviceID={device_id}")
        return

    if is_archived(number):
        log(f"🚫 Numéro archivé ignoré : {number}")
        return

    if is_message_processed(number, msg_id):
        log(f"🔁 Message déjà traité : {msg_id}")
        return

    conv_key = get_conversation_key(number)
    try:
        step = int(redis_conn.hget(conv_key, "step") or 0)
    except Exception as e:
        log(f"⚠️ Erreur récupération step : {e}")
        step = 0

    redis_conn.hset(conv_key, "device", device_id)
    log(f"➡️ Étape actuelle pour {number} : {step} (device {device_id})")

    if step == 0:
        reply = "C’est le livreur. Votre colis ne rentrait pas dans la boîte aux lettres ce matin. Je repasse ou je le mets en relais ?"
        redis_conn.hset(conv_key, "step", 1)
        log("💬 Réponse step 0 définie et step = 1")
    elif step == 1:
        reply = f"Ok alors choisissez ici votre nouveau créneau ou point relais : {SECOND_MESSAGE_LINK}\nSans ça je peux rien faire, merci et bonne journée."
        redis_conn.hset(conv_key, "step", 2)
        log("💬 Réponse step 1 définie et step = 2")
    else:
        log(f"✅ Fin de conversation pour {number}")
        archive_number(number)
        redis_conn.delete(conv_key)
        return

    try:
        log("⏳ Attente de 30s avant envoi du message")
        time.sleep(30)
        send_single_message(number, reply, device_id)
        log(f"📤 Message envoyé à {number} : {reply}")
    except Exception as e:
        log(f"❌ Erreur lors de l'envoi à {number} : {str(e)}")

    mark_message_processed(number, msg_id)
    log(f"✅ Message marqué comme traité : {msg_id}")
