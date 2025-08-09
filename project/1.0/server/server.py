import socket
import threading
import random
import hashlib
import os
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Assicurati che il project_root sia nel path prima di importare i moduli interni
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from utils.message import MessageType, ErrorType
from utils.groups import GROUPS
from utils.db import db


class ConnContext:
    MESSAGE_LENGTH = 4096

    def __init__(self, conn: socket.socket, addr: str):
        self.conn = conn
        self.addr = addr
        self.session = {}  # dati temporanei (user, challenge, u_t, ...)
        self._closed = False

    def close(self):
        try:
            if not self._closed:
                self.conn.close()
                self._closed = True
        except Exception as e:
            print(f"[SERVER] Errore durante la chiusura della connessione {self.addr}: {e}")
        finally:
            self.session.clear()
            print(f"[SERVER] Connessione con {self.addr} chiusa.")

    def update_session(self, data: dict):
        self.session.update(data)

    @property
    def is_session_empty(self):
        return not self.session

    def _send_json(self, message: dict):
        try:
            self.conn.sendall(json.dumps(message).encode())
        except BrokenPipeError:
            print(f"[SERVER] Errore: connessione chiusa dal client {self.addr} durante l'invio")

    def receive_json(self):
        try:
            data = self.conn.recv(self.MESSAGE_LENGTH)
            if not data:
                return None
            return json.loads(data.decode())
        except (ConnectionResetError, json.JSONDecodeError):
            return None

    def send_message(self, msg_type: MessageType, extra_data=None):
        payload = {
            "type_code": msg_type.code,
            "type": msg_type.label,
        }
        if extra_data:
            payload.update(extra_data)
        self._send_json(payload)

    def send_error(self, error_type: ErrorType, details=None):
        payload = {
            "type_code": MessageType.ERROR.code,
            "type": MessageType.ERROR.label,
            "error_code": error_type.code,
            "error": error_type.label,
            "message": error_type.message(),
        }
        if details:
            payload["details"] = details
        self._send_json(payload)


# ---------- handlers ----------

def handle_registration(ctx: ConnContext, msg: dict):
    username = msg.get("username")
    device_name = msg.get("device")
    pk = msg.get("public_key")

    if not username or not pk:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    users_collection = db["users"]

    if users_collection.find_one({"_id": username}):
        ctx.send_error(ErrorType.USERNAME_ALREADY_EXISTS)
        print(f"[SERVER] Registrazione fallita: username '{username}' già esistente")
        return

    user = {
        "_id": username,
        "devices": [{"pk": pk, "device_name": device_name, "main_device": True, "logged": True}],
        "created_at": datetime.now().isoformat(),
    }

    users_collection.insert_one(user)
    ctx.update_session({"user": user})
    ctx.send_message(MessageType.REGISTERED)
    print(f"[SERVER] Utente registrato: {username}")


def handle_auth_request(ctx: ConnContext, msg: dict, q: int):
    username = msg.get("username")
    temp_hex = msg.get("temp")
    if not username or not temp_hex:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    users_collection = db["users"]
    user_doc = users_collection.find_one({"_id": username})

    if not user_doc or not user_doc.get("devices"):
        ctx.send_error(ErrorType.USERNAME_NOT_FOUND)
        print(f"[SERVER] Autenticazione fallita: username '{username}' non trovato")
        return

    # validate and parse temp (hex)
    try:
        u_t = int(temp_hex, 16)
    except (ValueError, TypeError):
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    challenge = random.randint(0, q - 1)

    ctx.update_session({"u_t": u_t, "user": user_doc, "challenge": challenge})
    ctx.send_message(MessageType.CHALLENGE, {"challenge": hex(challenge)})
    print(f"[SERVER] Sfida inviata a {username}: {hex(challenge)[:20]}...")


def handle_auth_response(ctx: ConnContext, msg: dict, p: int, g: int):
    if ctx.is_session_empty or "user" not in ctx.session:
        print("[SERVER] Risposta di autenticazione senza sessione attiva")
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        return

    resp_hex = msg.get("response")
    if not resp_hex:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    try:
        alpha_z = int(resp_hex, 16)
    except (ValueError, TypeError):
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    u_t = ctx.session["u_t"]
    devices = ctx.session["user"]["devices"]
    challenge = ctx.session["challenge"]

    authenticated = False
    matched_device = None
    for device in devices:
        try:
            pk = int(device["pk"], 16)
        except (ValueError, TypeError):
            continue
        left = pow(g, alpha_z, p)
        right = (u_t * pow(pk, challenge, p)) % p
        if left == right:
            authenticated = True
            matched_device = device
            break

    if authenticated:
        ctx.send_message(MessageType.ACCEPTED)
        print(f"[SERVER] User {ctx.session["user"]["_id"]} autenticato dal dispositivo {matched_device.get('device_name') if matched_device else 'unknown'}")
    else:
        ctx.send_message(MessageType.REJECTED)
        print("[SERVER] Autenticazione rifiutata")


# Token pairing: semplice implementazione (aggiungi expiry se vuoi)
def save_token_pk(token: str, pk: str, device_name: str):
    temp_token_collection = db["temp_tokens"]
    token_doc = {
        "_id": token,
        "pk": pk,
        "device_name": device_name,
        "created_at": datetime.now()
        # aggiungi "expiry": datetime.utcnow() + timedelta(minutes=15) se vuoi TTL
    }
    temp_token_collection.insert_one(token_doc)


def get_info_from_token(token: str):
    temp_token_collection = db["temp_tokens"]
    token_doc = temp_token_collection.find_one({"_id": token})
    if token_doc:
        return token_doc["pk"], token_doc.get("device_name")
    else:
        return None, None


def handle_assoc_request(ctx: ConnContext, msg: dict):
    token_length = 32
    pk = msg.get("pk")
    device_name = msg.get("device")

    if not pk:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    nonce = os.urandom(16).hex()
    token_raw = f"{pk}{device_name or ''}{nonce}"
    token = hashlib.sha256(token_raw.encode()).hexdigest()[:token_length]

    print(f"[SERVER] Hashed Token: {token}")

    ctx.send_message(MessageType.TOKEN_ASSOC, {"token": token})
    save_token_pk(token, pk, device_name or "")
    print(f"[SERVER] Salvata tupla: {token} - {pk[:20]}...")


def handle_assoc_confirm(ctx: ConnContext, msg: dict):
    token = msg.get("token")
    if not token:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    pk, device_name = get_info_from_token(token)
    if not pk:
        ctx.send_error(ErrorType.TOKEN_INVALID_OR_EXPIRED)
        return

    if "user" not in ctx.session:
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        return

    username = ctx.session["user"]["_id"]
    users_collection = db["users"]
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

    # opzionale: rimuovere token dopo uso
    db["temp_tokens"].delete_one({"_id": token})

    ctx.send_message(MessageType.ACCEPTED)
    print(f"[SERVER] Dispositivo associato a {username}: {device_name} ({pk[:20]}...)")


def handle_logout(ctx: ConnContext):
    # se session presente, invalida e chiudi
    if not ctx.is_session_empty:
        ctx.send_message(MessageType.LOGGED_OUT)
        print("[SERVER] Logout effettuato con successo")
    else:
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        print(f"[SERVER] Errore: {ErrorType.SESSION_NOT_FOUND.message()}")
    ctx.close()
    return True


def handle_handshake(ctx: ConnContext, group_id: str):
    ctx.send_message(MessageType.GROUP_SELECTION, {"group_id": group_id})
    res = ctx.receive_json()
    if res is None:
        print(f"[SERVER] Connessione chiusa dal client {ctx.addr} o messaggio non valido")
        ctx.close()
        return
    if res.get("status") == "received":
        print(f"[SERVER] Handshake riuscito con {ctx.addr}")


# ---------------- client handler ----------------

def client_handler(ctx: ConnContext, p: int, g: int, q: int, group_id: str):
    print(f"[SERVER] Thread avviato per {ctx.addr}")
    try:
        while True:
            msg = ctx.receive_json()
            if msg is None:
                print(f"[SERVER] Connessione chiusa dal client {ctx.addr}")
                break

            msg_type = msg.get("type")
            if msg_type == MessageType.HANDSHAKE_REQ.label:
                handle_handshake(ctx, group_id)
            elif msg_type == MessageType.REGISTER.label:
                handle_registration(ctx, msg)
            elif msg_type == MessageType.AUTH_REQUEST.label:
                handle_auth_request(ctx, msg, q)
            elif msg_type == MessageType.AUTH_RESPONSE.label:
                handle_auth_response(ctx, msg, p, g)
            elif msg_type == MessageType.ASSOC_REQUEST.label:
                handle_assoc_request(ctx, msg)
            elif msg_type == MessageType.TOKEN_ASSOC.label:
                handle_assoc_confirm(ctx, msg)
            elif msg_type == MessageType.LOGOUT.label:
                should_close = handle_logout(ctx)
                if should_close:
                    break
            else:
                print(f"[SERVER] Tipo messaggio sconosciuto: {msg_type}")
    except Exception as e:
        print(f"[SERVER] Errore nel thread per {ctx.addr}: {e}")
    finally:
        if not ctx._closed:
            ctx.close()
        print(f"[SERVER] Thread terminato per {ctx.addr}")


# ---------------- main ----------------

def main():
    HOST = "192.168.1.168"
    PORT = 65432

    group_id = "modp-1536"
    p = GROUPS[group_id]["p"]
    g = GROUPS[group_id]["g"]
    q = (p - 1) // 2

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[SERVER] In ascolto su {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            ctx = ConnContext(conn, addr)
            t = threading.Thread(target=client_handler, args=(ctx, p, g, q, group_id))
            t.daemon = True
            t.start()


if __name__ == "__main__":
    main()
