import socket
import threading
import random
import hashlib
import os
import json
import sys
from utils.message import MessageType, ErrorType
from utils.groups import GROUPS
from pathlib import Path

from utils.db import db

project_root = Path(__file__).resolve().parent.parent
print(project_root)
sys.path.append(str(project_root))

users = {}  # memorizza username -> public_key
sessions_data = {}  # memorizza connessione -> dati temporanei per autenticazione


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


def handle_registration(conn, msg):
    username = msg.get("username")
    device_name = msg.get("device")
    pk = msg.get("public_key")

    users = db["users"]

    if users.find_one({"_id": username}):
        err_msg = {
            "type": MessageType.ERROR.value,
            "error": ErrorType.USERNAMEALEARYEXISTS.value,
        }
        send_json(conn, err_msg)
        print(f"[SERVER] Registrazione fallita: username '{username}' già esistente")
        return
    else:
        users.insert_one(
            {
                "_id": username,
                "devices": [
                    {"pk": pk, "device_name": device_name, "main_device": True}
                ],
            }
        )

        success_msg = {"type": MessageType.REGISTERED.value}
        send_json(conn, success_msg)
        print(f"[SERVER] Utente registrato: {username}")


def handle_auth_request(conn, msg, q):
    username = msg.get("username")
    users_collection = db["users"]
    user_doc = users_collection.find_one({"_id": username})
    if not user_doc or not user_doc.get("devices"):
        err_msg = {
            "type": MessageType.ERROR.value,
            "error": ErrorType.USERNAMENOTFOUND.value,
        }
        send_json(conn, err_msg)
        print(f"[SERVER] Autenticazione fallita: username '{username}' non trovato")
        return

    challenge = random.randint(0, q - 1)

    sessions_data[conn] = {
        "u_t": int(msg.get("temp"), 16),
        "user": user_doc,
        "challenge": challenge,
    }

    challenge = hex(challenge)

    challenge_msg = {"type": MessageType.CHALLENGE.value, "challenge": challenge}
    send_json(conn, challenge_msg)
    print(f"[SERVER] Sfida inviata a {username}: {challenge[:20]}")


def handle_auth_response(conn, msg, p, g):
    session = sessions_data.get(conn)
    if not session:
        print("[SERVER] Risposta di autenticazione senza sessione attiva")
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
        accepted_msg = {"type": MessageType.ACCEPTED.value}
        send_json(conn, accepted_msg)
        print("[SERVER] Autenticazione accettata")
    else:
        rejected_msg = {"type": MessageType.REJECTED.value}
        send_json(conn, rejected_msg)
        print("[SERVER] Autenticazione rifiutata")


def handle_associate_request(conn, msg, p, g):
    token_length = 32
    
    # print(f"[SERVER] Ricevuta richiesta di connessione da parte di: {conn}")
    pk = msg.get("pk")
    device_name = msg.get("device")
    
    # TODO: SPIEGARE LA SCELTA DEL TOKEN
    
    nonce = os.urandom(16).hex()
    token_raw = f"{pk}{device_name}{nonce}"

    # print(f"[SERVER] Unhashed Token: {token_raw}")
    
    token = hashlib.sha256(token_raw.encode()).hexdigest()[:token_length]

    print(f"[SERVER] Hashed Token: {token}")

    # create_qr_code(token)
    
    msg = {"type": MessageType.TOKEN_ASSOC.value, "token": token}
    send_json(conn, msg)
    print(f"[SERVER] Inviato token al client: {token}")
    


def client_handler(conn, addr, p, g, q, group):
    print(f"[SERVER] Connessione da {addr}")

    # Handshake
    handshake_msg = {
        "type": MessageType.GROUP_SELECTION.value,
        "group_id": group,
    }
    send_json(conn, handshake_msg)
    res = receive_json(conn)
    if res is None:
        print(f"[SERVER] Connessione chiusa dal client {addr} o messaggio non valido")
        conn.close()
        return

    if res.get("status") == "received":
        print(f"[SERVER] Handshake riuscito con {addr}")

    while True:
        msg = receive_json(conn)
        if msg is None:
            print(f"[SERVER] Connessione chiusa dal client {addr}")
            break

        msg_type = msg.get("type")
        if msg_type == MessageType.REGISTER.value:
            handle_registration(conn, msg)
        elif msg_type == MessageType.AUTH_REQUEST.value:
            handle_auth_request(conn, msg, q)
        elif msg_type == MessageType.AUTH_RESPONSE.value:
            handle_auth_response(conn, msg, p, g)
            conn.close()
            sessions_data.pop(conn, None)
            break
        elif msg_type == MessageType.ASSOC_REQUEST.value:
            handle_associate_request(conn, msg, p, g)
        else:
            print(f"[SERVER] Tipo messaggio sconosciuto: {msg_type}")

    conn.close()
    sessions_data.pop(conn, None)
    print(f"[SERVER] Thread terminato per {addr}")


def main():
    HOST = "127.0.0.1"
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
            # Crea un thread per gestire il client
            t = threading.Thread(target=client_handler, args=(conn, addr, p, g, q, group))
            t.start()


if __name__ == "__main__":
    main()
