import socket
import json
import random
import sys
import qrcode
import platform
from pathlib import Path
from utils.message import MessageType, ErrorType
from utils.groups import GROUPS
from utils.utils import get_linux_device_model


# --- COSTANTI ---

HOST = "192.168.1.168"
PORT = 65432
CONFIG_PATH = Path.home() / ".config"
SCHNORR_DIR = CONFIG_PATH / "schnorr"


# --- FUNZIONI UTILI ---


def load_private_key(username: str) -> int:
    """Carica la chiave privata dal file, esce se non trovata."""
    privkey_path = SCHNORR_DIR / f"{username}_privkey.txt"
    try:
        with open(privkey_path, "r") as f:
            print(f"[CLIENT] INFO: lettura chiave privata da {privkey_path}.")
            return int(f.read())
    except FileNotFoundError:
        print("[CLIENT] Errore: chiave privata non trovata. Registrati prima di autenticarti.")
        sys.exit(1)


def save_private_key(username: str, alpha: int) -> None:
    """Salva la chiave privata su file."""
    SCHNORR_DIR.mkdir(parents=True, exist_ok=True)
    privkey_path = SCHNORR_DIR / f"{username}_privkey.txt"
    with open(privkey_path, "w") as f:
        f.write(str(alpha))
    print(f"[CLIENT] INFO: chiave privata memorizzata in {privkey_path}.")


def receive_json(sock: socket.socket) -> dict:
    """Riceve dati JSON dal socket e li decodifica."""
    data = sock.recv(4096)
    if not data:
        print("[CLIENT] Connessione chiusa dal server")
        sys.exit(1)
    return json.loads(data.decode())


def send_json(sock: socket.socket, message: dict) -> None:
    """Invia dati JSON serializzati sul socket."""
    sock.sendall(json.dumps(message).encode())


def send_message(sock: socket.socket, msg_type: MessageType, extra_data=None) -> None:
    payload = {
        "type_code": msg_type.code,
        "type": msg_type.label,
    }
    if extra_data:
        payload.update(extra_data)
    send_json(sock, payload)


def send_error(sock: socket.socket, error_type: ErrorType, details=None) -> None:
    payload = {
        "type_code": MessageType.ERROR.code,
        "type": MessageType.ERROR.label,
        "error_code": error_type.code,
        "error": error_type.label,
        "message": error_type.message(),
    }
    if details:
        payload["details"] = details
    send_json(sock, payload)


def create_qr_code(token: str) -> None:
    """Crea e mostra un QR code dal token dato."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.show()


# --- LOGICA CLIENT ---


def get_device_name() -> str:
    manuf, _ = get_linux_device_model()
    return f"{manuf} {platform.system()} {platform.machine()}"


def registration(sock: socket.socket, p: int, g: int, q: int) -> None:
    username = input("Inserisci uno username per la registrazione: ").strip()
    alpha = random.randint(1, q - 1)
    device_name = get_device_name()
    public_key = hex(pow(g, alpha, p))

    send_message(
        sock,
        MessageType.REGISTER,
        {
            "username": username,
            "public_key": public_key,
            "device": device_name,
        },
    )

    response = receive_json(sock)
    if response.get("type_code") == MessageType.ERROR.code:
        err = ErrorType.from_code(response.get("error_code"))
        print(f"[CLIENT] Errore dal server: {err.message()}")
        return False
    elif response.get("type_code") == MessageType.REGISTERED.code:
        print(f"[CLIENT] {MessageType.REGISTERED.message()}")
        save_private_key(username, alpha)
        return True
    else:
        print("[CLIENT] Risposta inattesa dal server:", response)
        return False


def authentication(sock: socket.socket, p: int, g: int, q: int) -> None:
    username = input("Inserisci uno username per l'autenticazione: ").strip()
    alpha = load_private_key(username)

    alpha_t = random.randint(1, q - 1)
    u_t = hex(pow(g, alpha_t, p))
    send_message(sock, MessageType.AUTH_REQUEST, {"temp": u_t, "username": username})

    response = receive_json(sock)
    if response.get("type_code") == MessageType.ERROR.code:
        err = ErrorType.from_code(response.get("error_code"))
        print(f"[CLIENT] Errore dal server: {err.message()}")
        return

    if response.get("type_code") != MessageType.CHALLENGE.code:
        print("[CLIENT] Risposta inattesa dal server durante autenticazione.")
        return

    c = int(response["challenge"], 16)
    print(f"[CLIENT] Ricevuto challenge: {response['challenge'][:20]}...")

    alpha_z = (alpha_t + alpha * c) % q
    send_message(sock, MessageType.AUTH_RESPONSE, {"response": hex(alpha_z)})

    final_response = receive_json(sock)
    if final_response.get("type_code") == MessageType.ACCEPTED.code:
        print("[CLIENT] Autenticazione riuscita!")
        return True
    elif final_response.get("type_code") == MessageType.REJECTED.code:
        print("[CLIENT] Autenticazione fallita.")
        return False
    else:
        print("[CLIENT] Risposta inattesa dal server dopo autenticazione.")
        return


def association(sock: socket.socket, p: int, g: int, q: int) -> None:
    device_name = get_device_name()
    alpha = random.randint(1, q - 1)
    public_key = hex(pow(g, alpha, p))

    send_message(sock, MessageType.ASSOC_REQUEST, {"device": device_name, "pk": public_key})

    print("[CLIENT] Inviata richiesta di associazione del dispositivo")

    while True:
        res = receive_json(sock)
        if not res:
            print("[CLIENT] Connessione chiusa dal server")
            return False

        type_code = res.get("type_code")
        if type_code == MessageType.TOKEN_ASSOC.code:
            token = res.get("token")
            print(f"[CLIENT] Token ricevuto: {token}")
            create_qr_code(token)
        elif type_code == MessageType.ACCEPTED.code:
            print("[CLIENT] Associazione completata, login effettuato!")
            save_private_key(res.get("username"), alpha)
            return True
        elif type_code == MessageType.ERROR.code:
            err = ErrorType.from_code(res.get("error_code"))
            print(f"[CLIENT] Errore: {err.message()}")
            return False
        else:
            print("[CLIENT] Messaggio sconosciuto:", res)


def confirm_association(sock: socket.socket) -> None:
    ans = input("[CLIENT] Inserisci codice di abbinamento: ").strip()
    # Supponiamo il messaggio da inviare sia tipo ASSOC_CONFIRM, definisci se serve e invia
    send_message(sock, MessageType.TOKEN_ASSOC, {"token": ans})

    response = receive_json(sock)
    if response.get("type_code") == MessageType.ACCEPTED.code:
        print("[CLIENT] Abbinamento confermato con successo.")
    elif response.get("type_code") == MessageType.ERROR.code:
        err = ErrorType.from_code(response.get("error_code"))
        print(f"[CLIENT] Errore dal server: {err.message()}")
    else:
        print("[CLIENT] Risposta inattesa dal server:", response)


def log_out(sock: socket.socket) -> None:
    send_message(sock, MessageType.LOGOUT)
    response = receive_json(sock)
    if response.get("type_code") == MessageType.LOGGED_OUT.code:
        print("[CLIENT] Logout effettuato con successo.")
    elif response.get("type_code") == MessageType.ERROR.code:
        err = ErrorType.from_code(response.get("error_code"))
        print(f"[CLIENT] Errore dal server: {err.message()}")
    else:
        print("[CLIENT] Risposta inattesa dal server:", response)


def handshake(sock: socket.socket):
    send_message(sock, MessageType.HANDSHAKE_REQ)
    print("[CLIENT] Richiesta di handshake inviata al server...")

    handshake_msg = receive_json(sock)
    print("[CLIENT] Fase di handshake...")

    send_json(sock, {"status": "received"})

    group = handshake_msg.get("group_id")
    print(f"[CLIENT] {group}")
    if group not in GROUPS:
        print("[CLIENT] Gruppo crittografico non supportato dal client.")
        return False
    return group


# --- MAIN ---


def main():
    logged_in = False
    current_user = False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"[CLIENT] Connesso a {HOST}:{PORT}")

        # Handshake
        group = handshake(sock)
        if not group:
            sys.exit(1)

        print("[CLIENT] Handshake andato a buon fine...")

        p = GROUPS[group]["p"]
        g = GROUPS[group]["g"]
        q = (p - 1) // 2

        while True:
            if not logged_in:
                menu_message = (
                    "\n[CLIENT] Seleziona un'opzione:\n"
                    "  [R] Registrati\n"
                    "  [A] Accedi\n"
                    "  [D] Richiedi abbinamento dispositivo\n"
                    "  [Q] Esci\n"
                )
            else:
                menu_message = (
                    "\n[CLIENT] Seleziona un'opzione:\n"
                    "  [L] Log out\n"
                    "  [C] Conferma abbinamento dispositivo\n"
                    "  [Q] Esci\n"
                )
            print(menu_message)
            ans = input("[CLIENT] Inserisci la tua scelta: ").strip().upper()
            if not logged_in:
                if ans == "R":
                    success = registration(sock, p, g, q)
                    if success:
                        logged_in = True
                elif ans == "A":
                    success = authentication(sock, p, g, q)
                    if success:
                        logged_in = True
                elif ans == "D":
                    success = association(sock, p, g, q)
                    if success:
                        logged_in = True
                elif ans == "Q":
                    print("[CLIENT] Uscita dal client.")
                    break
            else:
                if ans == "L":
                    log_out(sock, p, g, q)
                    logged_in = False
                elif ans == "C":
                    confirm_association(sock)
                elif ans == "Q":
                    print("[CLIENT] Uscita dal client.")
                    break
                else:
                    print("[CLIENT] Input non valido, riprova.")


if __name__ == "__main__":
    main()
