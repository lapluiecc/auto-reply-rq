import os
import time
import json
from datetime import datetime, timezone
from redis import Redis
from logger import log

SERVER = os.getenv("SERVER")
API_KEY = os.getenv("API_KEY")
SECOND_MESSAGE_LINK = os.getenv("SECOND_MESSAGE_LINK")

# ✅ Connexion Redis dynamique (Upstash compatible)
REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)

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
    log(f"🌐 POST vers {url} avec {post_data}")
    try:
        response = requests.post(url, data=post_data)
        return response.json().get("data")
    except Exception as e:
        log(f"❌ Erreur POST : {e}")
        return None

def send_single_message(number, message, device_slot):
    log(f"📦 Envoi à {number} via SIM {device_slot}")
    return send_request(f"{SERVER}/services/send.php", {
        'number': number,
        'message': message,
        'devices': device_slot,
        'type': 'mms',
        'prioritize': 1,
        'key': API_KEY,
    })

def process_message(msg_json):
    log("🛠️ Début EXÉCUTION process_message")  # ✅ Log immédiat
    log(f"\n📥 Nouveau job reçu : {msg_json}")
    try:
        msg = json.loads(msg_json)
        log(f"🧩 Traitement du message : {msg}")
    except Exception as e:
        log(f"❌ JSON invalide : {e}")
        return

    number = msg.get("number")
    msg_id = msg.get("ID")
    device_id = msg.get("deviceID")

    if not number or not msg_id or not device_id:
        log(f"⛔️ Champs manquants : ID={msg_id}, number={number}, device={device_id}")
        return

    try:
        if is_archived(number) or is_message_processed(number, msg_id):
            log(f"🔁 Ignoré {msg_id} - {number}")
            return

        conv_key = get_conversation_key(number)
        step = int(redis_conn.hget(conv_key, "step") or 0)
        redis_conn.hset(conv_key, "device", device_id)

        if step == 0:
            reply = "C’est le livreur. Votre colis ne rentrait pas dans la boîte. Je repasse ou je le mets en relais ?"
            redis_conn.hset(conv_key, "step", 1)
        elif step == 1:
            reply = f"Ok choisissez votre point relais ici : {SECOND_MESSAGE_LINK}"
            redis_conn.hset(conv_key, "step", 2)
        else:
            archive_number(number)
            redis_conn.delete(conv_key)
            log(f"📦 Conversation terminée avec {number}")
            return

        send_single_message(number, reply, device_id)
        mark_message_processed(number, msg_id)
        log(f"✅ Réponse envoyée à {number} : {reply}")
        log("🎯 FIN process_message atteinte")  # ✅ Fin visible dans logs

    except Exception as e:
        log(f"❌ Erreur traitement Redis ou envoi : {e}")
