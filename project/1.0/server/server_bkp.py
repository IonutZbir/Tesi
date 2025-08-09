import socket
import threading
import random
import hashlib
import os
import json
import sys
from pathlib import Path

from utils.message import MessageType, ErrorType
from utils.groups import GROUPS
from utils.db import db
from datetime import datetime

# Percorso progetto e import (già fatto nel tuo esempio)
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Dati temporanei in memoria: connessione -> dati sessione autenticazione
sessions_data = {}


def send_json(conn, message):
    try:
        conn.sendall(json.dumps(message).encode())
    except BrokenPipeError:
        print("[SERVER] Errore: connessione chiusa dal client durante l'invio")


def receive_json(conn):
    try:
        data = conn.recv(4096)
        if not data:
            return None
        return json.loads(data.decode())
    except (ConnectionResetError, json.JSONDecodeError):
        return None


def send_message(conn: socket.socket, msg_type: MessageType, extra_data=None) -> None:
    payload = {
        "type_code": msg_type.code,
        "type": msg_type.label,
    }
    if extra_data:
        payload.update(extra_data)
    send_json(conn, payload)


def send_error(conn: socket.socket, error_type: ErrorType, details=None) -> None:
    payload = {
        "type_code": MessageType.ERROR.code,
        "type": MessageType.ERROR.label,
        "error_code": error_type.code,
        "error": error_type.label,
        "message": error_type.message(),
    }
    if details:
        payload["details"] = details
    send_json(conn, payload)


def handle_registration(conn, msg):
    username = msg.get("username")
    device_name = msg.get("device")
    pk = msg.get("public_key")

    users_collection = db["users"]

    if users_collection.find_one({"_id": username}):
        send_error(conn, ErrorType.USERNAME_ALREADY_EXISTS)

        print(f"[SERVER] Registrazione fallita: username '{username}' già esistente")
        return

    user = {
        "_id": username,
        "devices": [{"pk": pk, "device_name": device_name, "main_device": True, "logged": True}],
        "created_at": datetime.now().isoformat(),
    }

    users_collection.insert_one(user)

    sessions_data[conn] = {"user": user}

    send_message(conn, MessageType.REGISTERED)
    print(f"[SERVER] Utente registrato: {username}")


def handle_auth_request(conn, msg, q):
    username = msg.get("username")
    users_collection = db["users"]
    user_doc = users_collection.find_one({"_id": username})

    if not user_doc or not user_doc.get("devices"):
        send_error(conn, ErrorType.USERNAME_NOT_FOUND)
        print(f"[SERVER] Autenticazione fallita: username '{username}' non trovato")
        return

    challenge = random.randint(0, q - 1)
    sessions_data[conn] = {
        "u_t": int(msg.get("temp"), 16),
        "user": user_doc,
        "challenge": challenge,
    }

    send_message(conn, MessageType.CHALLENGE, {"challenge": hex(challenge)})

    print(f"[SERVER] Sfida inviata a {username}: {hex(challenge)[:20]}...")


def handle_auth_response(conn, msg, p, g):
    session = sessions_data.get(conn)
    if not session:
        print("[SERVER] Risposta di autenticazione senza sessione attiva")
        send_error(conn, ErrorType.SESSION_NOT_FOUND)
        return

    alpha_z = int(msg.get("response"), 16)
    u_t = session["u_t"]
    devices = session["user"]["devices"]
    challenge = session["challenge"]

    authenticated = False
    for device in devices:
        pk = int(device["pk"], 16)
        left = pow(g, alpha_z, p)
        right = (u_t * pow(pk, challenge, p)) % p
        if left == right:
            authenticated = True
            break

    if authenticated:
        send_message(conn, MessageType.ACCEPTED)
        print("[SERVER] Autenticazione accettata")
    else:
        send_message(conn, MessageType.REJECTED)
        print("[SERVER] Autenticazione rifiutata")


def save_token_pk(token: str, pk: str, device_name):
    temp_token_collection = db["temp_tokens"]

    token_pk = {"_id": token, "pk": pk, "device_name": device_name}

    temp_token_collection.insert_one(token_pk)


def get_info_from_token(token: str):
    temp_token_collection = db["temp_tokens"]
    token_doc = temp_token_collection.find_one({"_id": token})
    if token_doc:
        return token_doc["pk"], token_doc["device_name"]
    else:
        return None, None


def handle_assoc_request(conn, msg):
    token_length = 32
    pk = msg.get("pk")
    device_name = msg.get("device")

    nonce = os.urandom(16).hex()
    token_raw = f"{pk}{device_name}{nonce}"
    token = hashlib.sha256(token_raw.encode()).hexdigest()[:token_length]

    print(f"[SERVER] Hashed Token: {token}")

    send_message(conn, MessageType.TOKEN_ASSOC, {"token": token})
    print(f"[SERVER] Inviato token al client: {token}")

    save_token_pk(token, pk, device_name)
    print(f"[SERVER] Salvata tupla: {token} - {pk[:20]}...")


def handle_assoc_confirm(conn, msg, p, g):
    token = msg["token"]
    print(f"[SERVER] ricevuto token: {token}")

    pk, device_name = get_info_from_token(token)

    user = sessions_data[conn]
    users_collection = db["users"]
    username = user["user"]["_id"]

    users_collection.update_one(
        {"_id": username},
        {
            "$push": {
                "devices": {
                    "pk": pk,
                    "device_name": device_name,
                    "main_device": False,
                    "logged": True,
                }
            }
        },
    )

    send_message(conn, MessageType.ACCEPTED)
    print(f"[SERVER] Dispositivo associato a {username}: {device_name} ({pk[:20]}...)")


def handle_logout(conn):
    if conn in sessions_data:
        send_message(conn, MessageType.LOGGED_OUT)
        print("[SERVER] Logout effettuato con successo")
    else:
        send_error(conn, ErrorType.SESSION_NOT_FOUND)
        print(f"[SERVER] Errore: {ErrorType.SESSION_NOT_FOUND.message()}")
    conn.close()
    sessions_data.pop(conn, None)
    return True


def handle_handshake(conn, addr, group):
    send_message(conn, MessageType.GROUP_SELECTION, {"group_id": group})
    res = receive_json(conn)
    if res is None:
        print(f"[SERVER] Connessione chiusa dal client {addr} o messaggio non valido")
        conn.close()
        return
    if res.get("status") == "received":
        print(f"[SERVER] Handshake riuscito con {addr}")


def client_handler(conn, addr, p, g, q, group):
    print(f"[SERVER] Connessione da {addr}")

    while True:
        msg = receive_json(conn)
        if msg is None:
            print(f"[SERVER] Connessione chiusa dal client {addr}")
            break

        msg_type = msg.get("type")
        if msg_type == MessageType.HANDSHAKE_REQ.label:
            handle_handshake(conn, addr, group)
        elif msg_type == MessageType.REGISTER.label:
            handle_registration(conn, msg)
        elif msg_type == MessageType.AUTH_REQUEST.label:
            handle_auth_request(conn, msg, q)
        elif msg_type == MessageType.AUTH_RESPONSE.label:
            handle_auth_response(conn, msg, p, g)
        elif msg_type == MessageType.ASSOC_REQUEST.label:
            handle_assoc_request(conn, msg)
        elif msg_type == MessageType.LOGOUT.label:
            should_close = handle_logout(conn)
            if should_close:
                break
        elif msg_type == MessageType.TOKEN_ASSOC.label:
            handle_assoc_confirm(conn, msg, p, g)
        else:
            print(f"[SERVER] Tipo messaggio sconosciuto: {msg_type}")

    print(f"[SERVER] Thread terminato per {addr}")


def main():
    HOST = "192.168.1.168"
    PORT = 65432

    group = "modp-1536"
    p = GROUPS[group]["p"]
    g = GROUPS[group]["g"]
    q = (p - 1) // 2

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[SERVER] In ascolto su {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=client_handler, args=(conn, addr, p, g, q, group))
            t.start()


if __name__ == "__main__":
    main()
