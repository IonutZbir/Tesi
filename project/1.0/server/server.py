import hashlib
import json
import os
import random
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path for internal imports
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from utils.context import ConnContext
from utils.exceptions import *
from utils.groups import GROUPS
from utils.logger import Logger
from utils.message import ErrorType, MessageType

from models.temp_token import *
from models.user import *

DEBUG = True

logger = Logger()

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


def validate_message(msg: dict, required_fields: dict):
    """required_fields: dict con chiave=nome campo, valore=tipo atteso."""
    if not isinstance(msg, dict):
        raise ValidationError("Messaggio non valido: non è un dizionario")

    parsed = {}
    for field, expected_type in required_fields.items():
        value = msg.get(field)
        if value is None:
            raise ValidationError(f"Campo mancante: {field}")
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"Il campo {field} deve essere {expected_type.__name__}"
            )
        parsed[field] = value
    return parsed


def generate_token(token_length: int, pk: str, device_name: str) -> str:
    nonce = os.urandom(16).hex()
    token_raw = f"{pk}{device_name or ''}{nonce}"
    token = hashlib.sha256(token_raw.encode()).hexdigest()[:token_length]
    return token


# ---------- handlers ----------


def handle_registration(ctx: ConnContext, msg: dict):
    try:
        data = validate_message(
            msg, {"username": str, "device": str, "public_key": str}
        )
    except ValidationError as e:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        if DEBUG:
            logger.error(f"[SERVER] Errore di validazione {e}")
            return

    username = data["username"]
    device_name = data["device"]
    pk = data["public_key"]

    if User.find_user_by_id(username):
        ctx.send_error(ErrorType.USERNAME_ALREADY_EXISTS)
        if DEBUG:
            logger.debug(
                f"[SERVER] Registrazione fallita: username '{username}' già esistente"
            )
        return

    user = User(username)
    user.add_device(Device(pk, device_name))

    user.insert_user()

    ctx.update_session(user=user, logged_device=device_name, login_time=datetime.now())

    ctx.send_message(MessageType.REGISTERED)
    if DEBUG:
        logger.debug(f"[SERVER] Utente registrato: {username}")


def handle_auth_request(ctx: ConnContext, msg: dict, q: int):
    try:
        data = validate_message(msg, {"username": str, "temp": str})
    except ValidationError as e:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        if DEBUG:
            logger.error(f"[SERVER] Errore di validazione {e}")
        return

    username = data["username"]
    temp_pk_hex = data["temp"]

    user = User.find_user_by_id(username)

    if not user:
        ctx.send_error(ErrorType.USERNAME_NOT_FOUND)
        if DEBUG:
            logger.debug(
                f"[SERVER] Autenticazione fallita: username '{username}' non trovato"
            )
        return

    try:
        temp_pk = int(temp_pk_hex, 16)
    except (ValueError, TypeError):
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        return

    challenge = random.randint(0, q - 1)

    ctx.update_session(temp_pk=temp_pk, user=user, challenge=challenge)

    ctx.send_message(MessageType.CHALLENGE, {"challenge": hex(challenge)})
    if DEBUG:
        logger.debug(f"[SERVER] Sfida inviata a {username}: {hex(challenge)[:20]}...")


def handle_auth_response(ctx: ConnContext, msg: dict, p: int, g: int):
    if ctx.is_session_empty:
        if DEBUG:
            logger.error("[SERVER] Risposta di autenticazione senza sessione attiva")
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        return

    try:
        data = validate_message(msg, {"response": str})
    except ValidationError as e:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        if DEBUG:
            logger.error(f"[SERVER] Errore di validazione {e}")
        return

    resp_hex = data["response"]

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
        ctx.update_session(
            logged_device=matched_device["device_name"], login_time=datetime.now()
        )
        ctx.session.user.update_user_login(ctx.session.logged_device)

        if DEBUG:
            logger.debug(
                f"[SERVER] User {ctx.session.user._id} autenticato dal dispositivo {ctx.session.logged_device}"
                if matched_device
                else "'unknown'"
            )
    else:
        ctx.send_message(MessageType.REJECTED)
        if DEBUG:
            logger.debug("[SERVER] Autenticazione rifiutata")


def handle_assoc_request(ctx: ConnContext, msg: dict):
    token_length = 32

    try:
        data = validate_message(msg, {"pk": str, "device": str})
    except ValidationError as e:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        if DEBUG:
            logger.error(f"[SERVER] Errore di validazione {e}")
        return

    pk = data["pk"]
    device_name = data["device"]

    token = generate_token(token_length, pk, device_name)
    if DEBUG:
        logger.debug(f"[SERVER] Hashed Token: {token}")

    ctx.send_message(MessageType.TOKEN_ASSOC, {"token": token})

    temp_token = TempToken(token, pk, device_name)
    temp_token.insert_temp_token()

    register_connection(token, ctx)
    if DEBUG:
        logger.debug(f"[SERVER] Salvata tupla: {token} - {pk[:20]}...")


def handle_assoc_confirm(ctx: ConnContext, msg: dict):
    try:
        data = validate_message(msg, {"token": str})
    except ValidationError as e:
        ctx.send_error(ErrorType.MALFORMED_MESSAGE)
        if DEBUG:
            logger.error(f"[SERVER] Errore di validazione {e}")
        return

    token = data["token"]
    temp_token = TempToken.find_pk_by_id(token)

    if not temp_token:
        ctx.send_error(ErrorType.UNAUTHORIZED)
        if DEBUG:
            logger.error(
                f"[SERVER] Errore: {ErrorType.UNAUTHORIZED.message()}"
            )
        return

    pk, device_name = temp_token.pk, temp_token.device_name

    if not ctx.session.is_authenticated():
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        if DEBUG:
            logger.error(
                f"[SERVER] Errore: {ErrorType.SESSION_NOT_FOUND.message()}"
            )
        return

    devices = ctx.session.user.devices

    for device in devices:
        if device["device_name"] == device_name and not device["main_device"]:
            ctx.send_error(ErrorType.NO_MAIN_DEVICE)
            if DEBUG:
                logger.error(
                    f"[SERVER] Errore: {ErrorType.NO_MAIN_DEVICE.message()}"
                )
            return

    if temp_token.is_expired:
        ctx.send_error(ErrorType.TOKEN_INVALID_OR_EXPIRED)
        TempToken.delete_one(token)
        if DEBUG:
            logger.error(
                f"[SERVER] Errore: {ErrorType.TOKEN_INVALID_OR_EXPIRED.message()}"
            )
        return

    user = ctx.session.user

    user.update_user_with_device(pk, device_name)

    ctx.update_session(user=user)

    TempToken.delete_one(token)

    # Verifica che il secondo dispositivo non si sia scollegato nel mentre, altrimenti annulla accoppiamento
    # e dal database viene cancellata la coppia tempo_token

    s_ctx = get_connection(token)

    if not s_ctx:
        ctx.send_error(ErrorType.ASSOC_FAILURE)
        if DEBUG:
            logger.debug(f"[SERVER] {ErrorType.message(ErrorType.ASSOC_FAILURE)}")

    # Send ACCEPT message to main device
    ctx.send_message(MessageType.ACCEPTED)
    if DEBUG:
        logger.debug(
            f"[SERVER] Dispositivo associato a {user._id}: {device_name} ({pk[:20]}...)"
        )

    # Send ACCEPT message to second device
    # TODO: thread lock?
    s_ctx.update_session(
        user=user, logged_device=device_name, login_time=datetime.now()
    )
    s_ctx.send_message(MessageType.ACCEPTED, {"username": user._id})


def handle_logout(ctx: ConnContext):
    # se session presente, invalida e chiudi
    if not ctx.is_session_empty:
        ctx.send_message(MessageType.LOGGED_OUT)
        user = ctx.session.user
        user.update_user_loggedout(ctx.session.logged_device)
        ctx.clear_session()
        if DEBUG:
            logger.debug("[SERVER] Logout effettuato con successo")
    else:
        ctx.send_error(ErrorType.SESSION_NOT_FOUND)
        if DEBUG:
            logger.debug(f"[SERVER] Errore: {ErrorType.SESSION_NOT_FOUND.message()}")
    return True


def handle_handshake(ctx: ConnContext, group_id: str):
    ctx.send_message(MessageType.GROUP_SELECTION, {"group_id": group_id})
    res = ctx.receive_json()
    if res is None:
        logger.info(
            f"[SERVER] Connessione chiusa dal client {ctx.addr} o messaggio non valido"
        )
        ctx.close()
        return
    if res.get("type") == MessageType.HANDSHAKE_REQ.label:
        logger.info(f"[SERVER] Handshake riuscito con {ctx.addr}")


# ---------------- client handler ----------------


def client_handler(ctx: ConnContext, p: int, g: int, q: int, group_id: str):
    logger.info(f"[SERVER] Thread avviato per {ctx.addr}")
    try:
        while True:
            msg = ctx.receive_json()
            if msg is None:
                logger.info(f"[SERVER] Connessione chiusa dal client {ctx.addr}")
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
                logger.info(f"[SERVER] Tipo messaggio sconosciuto: {msg_type}")
    except Exception as e:
        logger.error(f"[SERVER] Errore nel thread per {ctx.addr}: {e}")
    finally:
        if not ctx._closed:
            ctx.close()
        logger.info(f"[SERVER] Thread terminato per {ctx.addr}")


# ---------------- main ----------------


def main():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    HOST = config["host"]
    PORT = config["port"]
    GROUP_ID = config["group_id"]

    GROUP_ID = "modp-1536"
    p = GROUPS[GROUP_ID]["p"]
    g = GROUPS[GROUP_ID]["g"]
    q = (p - 1) // 2

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        logger.info(f"[SERVER] In ascolto su {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            ctx = ConnContext(conn, addr)
            t = threading.Thread(target=client_handler, args=(ctx, p, g, q, GROUP_ID))
            t.daemon = True
            t.start()


if __name__ == "__main__":
    main()
