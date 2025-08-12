import argparse
import json
import platform
import qrcode
import random
import socket
import sys
from pathlib import Path

from utils.groups import GROUPS
from utils.logger import Logger
from utils.message import MessageType, ErrorType
from utils.utils import get_linux_device_model

# --- COSTANTI ---

DEBUG = False

logger = Logger()


class ClientConnection:
    MESSAGE_LENGTH = 4096

    def __init__(self, sock: socket.socket):
        self.sock = sock

    def _send_json(self, message: dict):
        try:
            self.sock.sendall(json.dumps(message).encode())
        except BrokenPipeError:
            logger.error("[CLIENT] Errore: connessione chiusa durante l'invio")
        except OSError as e:
            logger.error(f"[CLIENT] Errore di invio: {e}")

    def receive(self):
        try:
            data = self.sock.recv(self.MESSAGE_LENGTH)
            if not data:
                logger.warning("[CLIENT] Connessione chiusa dal server")
                return None
            return json.loads(data.decode())
        except json.JSONDecodeError:
            logger.error("[CLIENT] Errore nel parsing del messaggio JSON")
            return None
        except ConnectionResetError:
            logger.warning("[CLIENT] Connessione resettata dal server")
            return None

    def send(self, msg_type: MessageType, extra_data=None):
        payload = {
            "type_code": msg_type.code,
            "type": msg_type.label,
        }
        if extra_data:
            payload.update(extra_data)
        self._send_json(payload)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class KeyManager:
    CONFIG_PATH = Path.home() / ".config"
    SCHNORR_DIR = CONFIG_PATH / "schnorr"

    @classmethod
    def load_private_key(cls, username: str) -> int:
        """Carica la chiave privata dal file, esce se non trovata."""
        privkey_path = cls.SCHNORR_DIR / f"{username}_privkey.txt"
        try:
            with open(privkey_path, "r") as f:
                if DEBUG:
                    logger.debug(
                        f"[CLIENT] INFO: lettura chiave privata da {privkey_path}."
                    )
                return int(f.read())
        except FileNotFoundError:
            logger.error(
                "[CLIENT] Errore: chiave privata non trovata. Registrati prima di autenticarti."
            )
            sys.exit(1)

    @classmethod
    def save_private_key(cls, username: str, key: int) -> None:
        """Salva la chiave privata su file."""
        cls.SCHNORR_DIR.mkdir(parents=True, exist_ok=True)
        privkey_path = cls.SCHNORR_DIR / f"{username}_privkey.txt"
        with open(privkey_path, "w") as f:
            f.write(str(key))
        if DEBUG:
            logger.debug(
                f"[CLIENT] INFO: chiave privata memorizzata in {privkey_path}."
            )


class ClientApp:
    def __init__(self, client_conn: ClientConnection):
        self.client_conn = client_conn

    def handshake(self, client: ClientConnection) -> bool:
        self.client_conn.send(MessageType.HANDSHAKE_REQ)
        if DEBUG:
            logger.debug("[CLIENT] Richiesta di handshake inviata al server...")

        response = wait_for_response(client, {MessageType.GROUP_SELECTION.code})

        if response is None:
            return False

        if DEBUG:
            logger.debug("[CLIENT] Fase di handshake...")

        self.client_conn.send(MessageType.HANDSHAKE_RES)

        if response.get("type_code") == MessageType.GROUP_SELECTION.code:
            group = response.get("group_id")
            logger.info(f"[CLIENT] Gruppo selezionato dal server: {group}")

            if group not in GROUPS:
                logger.error("[CLIENT] Gruppo crittografico non supportato dal client.")
                return False

            self.p = GROUPS[group]["p"]
            self.g = GROUPS[group]["g"]
            self.q = (self.p - 1) // 2

            return True

    def register(self) -> bool:
        username = input(
            "[INPUT] Inserisci uno username per la registrazione: "
        ).strip()
        alpha = random.randint(1, self.q - 1)
        device_name = get_device_name()
        public_key = hex(pow(self.g, alpha, self.p))

        self.client_conn.send(
            MessageType.REGISTER,
            {
                "username": username,
                "public_key": public_key,
                "device": device_name,
            },
        )

        response = wait_for_response(self.client_conn, {MessageType.REGISTERED.code})

        if response is None:
            return False

        if response.get("type_code") == MessageType.REGISTERED.code:
            logger.info(f"[CLIENT] {MessageType.REGISTERED.message()}")
            KeyManager.save_private_key(username, alpha)
            return True
        else:
            logger.warning("[CLIENT] Risposta inattesa dal server:", response)
            return False

    def auth(self) -> bool:
        username = input(
            "[INPUT] Inserisci uno username per l'autenticazione: "
        ).strip()
        alpha = KeyManager.load_private_key(username)

        alpha_t = random.randint(1, self.q - 1)
        u_t = hex(pow(self.g, alpha_t, self.p))
        self.client_conn.send(
            MessageType.AUTH_REQUEST, {"temp": u_t, "username": username}
        )

        response = wait_for_response(self.client_conn, {MessageType.CHALLENGE.code})
        if response is None:
            return False

        c = int(response["challenge"], 16)
        if DEBUG:
            logger.debug(
                f"[CLIENT] Ricevuto challenge: {response['challenge'][:20]}..."
            )

        alpha_z = (alpha_t + alpha * c) % self.q
        self.client_conn.send(MessageType.AUTH_RESPONSE, {"response": hex(alpha_z)})

        response = wait_for_response(
            self.client_conn, {MessageType.ACCEPTED.code, MessageType.REJECTED.code}
        )

        if response is None:
            return False

        if response.get("type_code") == MessageType.ACCEPTED.code:
            logger.info("[CLIENT] Autenticazione riuscita!")
            return True
        elif response.get("type_code") == MessageType.REJECTED.code:
            logger.info("[CLIENT] Autenticazione fallita.")
            return False

    def assoc(self) -> bool:
        device_name = get_device_name()

        alpha = random.randint(1, self.q - 1)
        public_key = hex(pow(self.g, alpha, self.p))

        # Invio della richiesta di associazione
        self.client_conn.send(
            MessageType.ASSOC_REQUEST, {"device": device_name, "pk": public_key}
        )
        if DEBUG:
            logger.debug("[CLIENT] Inviata richiesta di associazione del dispositivo")

        # Primo step: attendere il token da mostrare come QR
        response = wait_for_response(
            self.client_conn, {MessageType.TOKEN_ASSOC.code, MessageType.ERROR.code}
        )
        if response is None:
            return False

        if response.get("type_code") == MessageType.TOKEN_ASSOC.code:
            token = response.get("token")
            logger.info(f"[CLIENT] Token ricevuto: {token}")
            create_qr_code(token)

        # Secondo step: attendere conferma di associazione
        response = wait_for_response(
            self.client_conn, {MessageType.ACCEPTED.code, MessageType.ERROR.code}
        )
        if response is None:
            return False

        if response.get("type_code") == MessageType.ACCEPTED.code:
            logger.info("[CLIENT] Associazione completata, login effettuato!")
            KeyManager.save_private_key(response.get("username"), alpha)
            return True

    def confirm_assoc(self) -> bool:
        ans = input("[INPUT] Inserisci codice di abbinamento: ").strip()

        self.client_conn.send(MessageType.TOKEN_ASSOC, {"token": ans})

        response = wait_for_response(self.client_conn, {MessageType.ACCEPTED.code})

        if response is None:
            return False

        if response.get("type_code") == MessageType.ACCEPTED.code:
            logger.info("[CLIENT] Abbinamento confermato con successo.")
            return True

    def log_out(self) -> bool:
        self.client_conn.send(MessageType.LOGOUT)

        response = wait_for_response(self.client_conn, {MessageType.LOGGED_OUT.code})

        if response is None:
            return False

        if response.get("type_code") == MessageType.LOGGED_OUT.code:
            logger.info("[CLIENT] Logout effettuato con successo.")
            return True


def wait_for_response(client: ClientConnection, expected_types: set[MessageType]):
    while True:
        msg = client.receive()

        if msg is None:
            logger.warning("[CLIENT] Connessione chiusa o messaggio vuoto.")
            return None

        if msg.get("type_code") in expected_types:
            return msg
        elif msg.get("type_code") == MessageType.ERROR.code:
            err = ErrorType.from_code(msg["error_code"])
            logger.warning(f"[CLIENT] Errore: {err.message()}")
            return None
        else:
            logger.warning("[CLIENT] Messaggio inatteso:", msg)


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


def get_device_name() -> str:
    manuf, _ = get_linux_device_model()
    return f"{manuf} {platform.system()} {platform.machine()}"


def not_logged_menu() -> str:
    menu = (
        "\n[CLIENT] Seleziona un'opzione:\n"
        "  [R] Registrati\n"
        "  [A] Accedi\n"
        "  [D] Richiedi abbinamento dispositivo\n"
        "  [Q] Esci\n"
    )
    return menu


def logged_menu() -> str:
    menu = (
        "\n[CLIENT] Seleziona un'opzione:\n"
        "  [L] Log out\n"
        "  [C] Conferma abbinamento dispositivo\n"
        "  [Q] Esci\n"
    )
    return menu

def parse_args():
    parser = argparse.ArgumentParser(
        description="Client di autenticazione con protocollo di Schnorr"
    )
    
    parser.add_argument(
        "-i",
        "--ip",
        type=str,
        required=False,
        help="Indirizzo IP del server"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        required=False,
        help="Porta del server"
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Abilita il logging in modalità debug"
    )
    
    parser.add_argument(
        "-g",
        "--gui",
        action="store_true",
        help="Avvia il client in modalità GUI"
    )

    return parser.parse_args()

# --- MAIN ---
def main():
    
    args = parse_args()
    
    ip = args.ip
    port = args.port
    gui = args.gui
    
    global DEBUG
    DEBUG = args.debug

    if not ip:
        ip = "127.0.0.1"
    
    if not port:    
        port = 65432
        
    if gui:
        # gui()
        pass
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        logger.info(f"[CLIENT] Connesso a {ip}:{port}")

        client_conn = ClientConnection(sock)
        app = ClientApp(client_conn)

        if not app.handshake(client_conn):
            sys.exit(1)

        if DEBUG:
            logger.debug("[CLIENT] Handshake andato a buon fine...")

        logged_in = False

        # Azioni per il menu NON loggato
        actions_not_logged = {
            "R": app.register,
            "A": app.auth,
            "D": app.assoc,
            "Q": lambda: sys.exit("[CLIENT] Uscita dal client."),
        }

        # Azioni per il menu loggato
        actions_logged = {
            "L": app.log_out,
            "C": app.confirm_assoc,
            "Q": lambda: sys.exit("[CLIENT] Uscita dal client."),
        }

        while True:
            if not logged_in:
                print(not_logged_menu())
                ans = input("[INPUT] Inserisci la tua scelta: ").strip().upper()
                action = actions_not_logged.get(ans)
                if action:
                    success = action()
                    if success:
                        logged_in = True
                else:
                    logger.warning("[CLIENT] Input non valido.")
            else:
                print(logged_menu())
                ans = input("[INPUT] Inserisci la tua scelta: ").strip().upper()
                action = actions_logged.get(ans)
                if action:
                    success = action()
                    if ans == "L" and success:
                        logged_in = False
                else:
                    logger.warning("[CLIENT] Input non valido.")


if __name__ == "__main__":
    main()
