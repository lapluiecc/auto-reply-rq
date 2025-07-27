import os
import time
import json
from datetime import datetime
from redis import Redis

SERVER = os.getenv("SERVER", "https://moncolis-attente.com/")
API_KEY = os.getenv("API_KEY", "f376d32d14b058ed2383b97fd568d1b26de1b75c")
STORAGE_FILE = os.path.join(os.path.dirname(__file__), 'conversations.json')
ARCHIVE_FILE = os.path.join(os.path.dirname(__file__), 'archived_numbers.json')
LOG_FILE = "/tmp/log.txt"

def log(text):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.utcnow().isoformat()}] {text}\n")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

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
    device_from_msg = msg.get("deviceID")

    if not msg_id or not number or not device_from_msg:
        log("⛔️ Champs manquants, message ignoré")
        return

    conversations = load_json(STORAGE_FILE)
    archived = load_json(ARCHIVE_FILE)

    log(f"🔁 Traitement : ID={msg_id}, number={number}, device={device_from_msg}")

    if number in archived:
        log(f"🚫 Numéro archivé ignoré : {number}")
        return

    if number not in conversations:
        conversations[number] = {
            "step": 0,
            "device": device_from_msg,
            "processed_ids": []
        }
        log(f"🆕 Conversation créée pour {number}")

    if msg_id in conversations[number]["processed_ids"]:
        log(f"🔁 Déjà traité : {msg_id}")
        return

    step = conversations[number]["step"]
    device_id = conversations[number]["device"]
    log(f"➡️ Étape : {step} | Device : {device_id}")

    if step == 0:
        reply = "C’est le livreur. Votre colis ne rentrait pas dans la boîte aux lettres ce matin. Je repasse ou je le mets en relais ?"
        conversations[number]["step"] = 1
    elif step == 1:
        reply = "Ok alors choisissez ici votre nouveau créneau ou point relais : https://suivi-coursier.com/183248\nSans ça je peux rien faire, merci et bonne journée."
        conversations[number]["step"] = 2
    else:
        log(f"✅ Fin conversation avec {number}")
        archived[number] = True
        conversations.pop(number, None)
        save_json(STORAGE_FILE, conversations)
        save_json(ARCHIVE_FILE, archived)
        return

    try:
        log("⏳ Attente 30s avant envoi...")
        time.sleep(30)
        send_single_message(number, reply, device_id)
        log(f"📤 Message envoyé à {number} : {reply}")
    except Exception as e:
        log(f"❌ Erreur à {number} : {str(e)}")

    conversations[number]["processed_ids"].append(msg_id)
    conversations[number]["processed_ids"] = list(set(conversations[number]["processed_ids"]))[-10:]
    save_json(STORAGE_FILE, conversations)
