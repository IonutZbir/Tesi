import socket
import threading
import random
import hashlib
import os
import sys
from pathlib import Path

# Assicurati che il project_root sia nel path prima di importare i moduli interni
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from utils.message import MessageType, ErrorType
from utils.groups import GROUPS
from utils.context import ConnContext

from models.user import *
from models.temp_token import *


# --- Struttura globale per le connessioni attive ---
active_connections = {}
connections_lock = threading.Lock()

def register_connection(identifier: str, ctx: ConnContext):
    with connections_lock:
        active_connections[identifier] = ctx

def get_connection(identifier) -> ConnContext:
    with connections_lock:
        return active_connections.get(identifier)

def remove_connection(identifier):
    with connections_lock:
        active_connections.pop(identifier, None)

# ---------- handlers ----------

def handle_registration(ctx: ConnContext, msg: dict):
    # TODO: input validation
    username = msg.get("username")
    device_name = msg.get("device")
    pk = msg.get("public_key")

    if not username or not pk:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    if User.find_user_by_id(username):
        ctx.send_error(ErrorType.USERNAME_ALREADY_EXISTS)
        print(f"[SERVER] Registrazione fallita: username '{username}' già esistente")
        return

    user = User(username)
    user.add_device(Device(pk, device_name))

    user.insert_user()
    
    ctx.update_session(user=user, logged_device=device_name, login_time=datetime.now())
    
    ctx.send_message(MessageType.REGISTERED)
    print(f"[SERVER] Utente registrato: {username}")


def handle_auth_request(ctx: ConnContext, msg: dict, q: int):
    # TODO: input validation
    username = msg.get("username")
    temp_pk_hex = msg.get("temp")
    if not username or not temp_pk_hex:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    user = User.find_user_by_id(username)

    if not user:
        ctx.send_error(ErrorType.USERNAME_NOT_FOUND)
        print(f"[SERVER] Autenticazione fallita: username '{username}' non trovato")
        return

    # validate and parse temp (hex)
    try:
        temp_pk = int(temp_pk_hex, 16)
    except (ValueError, TypeError):
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    challenge = random.randint(0, q - 1)
    
    ctx.update_session(temp_pk=temp_pk, user=user, challenge=challenge)
    
    ctx.send_message(MessageType.CHALLENGE, {"challenge": hex(challenge)})
    print(f"[SERVER] Sfida inviata a {username}: {hex(challenge)[:20]}...")


def handle_auth_response(ctx: ConnContext, msg: dict, p: int, g: int):
    if ctx.is_session_empty:
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

    temp_pk = ctx.session.temp_pk
    devices = ctx.session.user.devices
    challenge = ctx.session.challenge

    authenticated = False
    matched_device = None
    for device in devices:
        try:
            pk = int(device["pk"], 16)
        except (ValueError, TypeError):
            continue
        left = pow(g, alpha_z, p)
        right = (temp_pk * pow(pk, challenge, p)) % p
        if left == right:
            authenticated = True
            matched_device = device
            break

    if authenticated:
        ctx.send_message(MessageType.ACCEPTED)
        ctx.update_session(logged_device=matched_device["device_name"], login_time=datetime.now())        
        ctx.session.user.update_user_login(ctx.session.logged_device)

        print(f"[SERVER] User {ctx.session.user._id} autenticato dal dispositivo {ctx.session.logged_device}" if matched_device else "'unknown'")
    else:
        ctx.send_message(MessageType.REJECTED)
        print("[SERVER] Autenticazione rifiutata")


def handle_assoc_request(ctx: ConnContext, msg: dict):
    # TODO: input validation and token_length??
    token_length = 32
    pk = msg.get("pk")
    device_name = msg.get("device")

    if not pk:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    # token = generate_token()
    nonce = os.urandom(16).hex()
    token_raw = f"{pk}{device_name or ''}{nonce}"
    token = hashlib.sha256(token_raw.encode()).hexdigest()[:token_length]

    print(f"[SERVER] Hashed Token: {token}")

    ctx.send_message(MessageType.TOKEN_ASSOC, {"token": token})
    
    temp_token = TempToken(token, pk, device_name)
    temp_token.insert_temp_token()
    
    register_connection(token, ctx)
    
    print(f"[SERVER] Salvata tupla: {token} - {pk[:20]}...")


def handle_assoc_confirm(ctx: ConnContext, msg: dict):
    token = msg.get("token")
    
    # TODO: TempToken.find_pk_by_id(token) ritorna un'istanza di TempToken e non un dict
    temp_token = TempToken.find_pk_by_id(token)

    pk, device_name = temp_token["pk"], temp_token["device_name"]
    
    devices = ctx.session.user.devices
    
    for device in devices: 
        if device["device_name"] == device_name and not device_name["main_device"]: 
            ctx.send_error(ErrorType.NO_MAIN_DEVICE)
            return
    
    if not token:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    # TODO: controllare se il token è scaduto
    if not pk:
        ctx.send_error(ErrorType.TOKEN_INVALID_OR_EXPIRED)
        return

    if not ctx.session.is_authenticated():
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        return

    user = ctx.session.user
    
    user.update_user_with_device(pk, device_name)
    
    ctx.update_session(user=user)

    # opzionale: rimuovere token dopo uso
    # db["temp_tokens"].delete_one({"_id": token})

    # Send ACCEPT message to main device
    ctx.send_message(MessageType.ACCEPTED)
    print(f"[SERVER] Dispositivo associato a {user._id}: {device_name} ({pk[:20]}...)")

    # Send ACCEPT message to second device
    s_ctx = get_connection(token)
    
    # TODO: thread lock?
    s_ctx.update_session(user=user, logged_device=device_name, login_time=datetime.now())
    s_ctx.send_message(MessageType.ACCEPTED, {
        "username": user._id
    })


def handle_logout(ctx: ConnContext):
    # se session presente, invalida e chiudi
    if not ctx.is_session_empty:
        ctx.send_message(MessageType.LOGGED_OUT)
        user = ctx.session.user
        user.update_user_loggedout(ctx.session.logged_device)
        ctx.clear_session()
        print("[SERVER] Logout effettuato con successo")
    else:
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        print(f"[SERVER] Errore: {ErrorType.SESSION_NOT_FOUND.message()}")
    return True


def handle_handshake(ctx: ConnContext, group_id: str):
    ctx.send_message(MessageType.GROUP_SELECTION, {"group_id": group_id})
    res = ctx.receive_json()
    if res is None:
        print(f"[SERVER] Connessione chiusa dal client {ctx.addr} o messaggio non valido")
        ctx.close()
        return
    if res.get("type") == MessageType.HANDSHAKE_REQ.label:
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
                handle_logout(ctx)
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
