import os
import time
import json
from datetime import datetime
from redis import Redis

# Configuration
SERVER = os.getenv("SERVER", "https://moncolis-attente.com/")
API_KEY = os.getenv("API_KEY", "f3763d214b058ed2383b97fd568d1b26de1b75c")
SECOND_MESSAGE_LINK = os.getenv("SECOND_MESSAGE_LINK", "https://locker-colis-attente.com/183248")
LOG_FILE = "/tmp/log.txt"

redis_client = Redis(host='localhost', port=6379, decode_responses=True)

def log(text):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.utcnow().isoformat()}] {text}\n")

def get_conversation_key(number):
    return f"conv:{number}"

def is_archived(number):
    return redis_client.sismember("archived_numbers", number)

def archive_number(number):
    redis_client.sadd("archived_numbers", number)

def mark_message_processed(number, msg_id):
    redis_client.sadd(f"processed:{number}", msg_id)

def is_message_processed(number, msg_id):
    return redis_client.sismember(f"processed:{number}", msg_id)

def send_request(url, post_data):
    import requests
    response = requests.post(url, data=post_data)
    try:
        json_data = response.json()
    except ValueError:
        raise Exception("Réponse invalide du serveur.")
    if not json_data.get("success"):
        error = json_data.get("error", {}).get("message", "Erreur inconnue")
        raise Exception(f"Erreur d'envoi : {error}")
    return json_data.get("data")

def send_single_message(number, message, device_slot):
    post_data = {
        'number': number,
        'message': message,
        'devices': device_slot,
        'type': 'mms',
        'prioritize': 1,
        'key': API_KEY,
    }
    return send_request(f"{SERVER}/services/send.php", post_data)

def process_message(msg):
    msg_id = msg.get("ID")
    number = msg.get("number")
    device_id = msg.get("deviceID")

    if not msg_id or not number or not device_id:
        log("⛔️ Champs manquants, message ignoré")
        return

    if is_archived(number):
        log(f"🚫 Numéro archivé ignoré : {number}")
        return

    if is_message_processed(number, msg_id):
        log(f"🔁 Message déjà traité : {msg_id}")
        return

    conv_key = get_conversation_key(number)
    step = int(redis_client.hget(conv_key, "step") or 0)
    redis_client.hset(conv_key, "device", device_id)

    log(f"➡️ Étape {step} pour {number} via {device_id}")

    if step == 0:
        reply = "C’est le livreur. Votre colis ne rentrait pas dans la boîte aux lettres ce matin. Je repasse ou je le mets en relais ?"
        redis_client.hset(conv_key, "step", 1)
    elif step == 1:
        reply = f"Ok alors choisissez ici votre nouveau créneau ou point relais : {SECOND_MESSAGE_LINK}\nSans ça je peux rien faire, merci et bonne journée."
        redis_client.hset(conv_key, "step", 2)
    else:
        log(f"✅ Conversation terminée avec {number}")
        archive_number(number)
        redis_client.delete(conv_key)
        return

    try:
        log("⏳ Attente 30s avant envoi...")
        time.sleep(30)
        send_single_message(number, reply, device_id)
        log(f"📤 Message envoyé à {number} : {reply}")
    except Exception as e:
        log(f"❌ Erreur à {number} : {str(e)}")

    mark_message_processed(number, msg_id)
