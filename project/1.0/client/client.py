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

class ClientConnection:
    MESSAGE_LENGTH = 4096

    def __init__(self, sock: socket.socket):
        self.sock = sock

    def _send_json(self, message: dict):
        try:
            self.sock.sendall(json.dumps(message).encode())
        except BrokenPipeError:
            print("[CLIENT] Errore: connessione chiusa durante l'invio")
        except OSError as e:
            print(f"[CLIENT] Errore di invio: {e}")

    def receive(self):
        try:
            data = self.sock.recv(self.MESSAGE_LENGTH)
            if not data:
                print("[CLIENT] Connessione chiusa dal server")
                return None
            return json.loads(data.decode())
        except json.JSONDecodeError:
            print("[CLIENT] Errore nel parsing del messaggio JSON")
            return None
        except ConnectionResetError:
            print("[CLIENT] Connessione resettata dal server")
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
                print(f"[CLIENT] INFO: lettura chiave privata da {privkey_path}.")
                return int(f.read())
        except FileNotFoundError:
            print("[CLIENT] Errore: chiave privata non trovata. Registrati prima di autenticarti.")
            sys.exit(1)

    @classmethod
    def save_private_key(cls, username: str, key: int) -> None:
        """Salva la chiave privata su file."""
        cls.SCHNORR_DIR.mkdir(parents=True, exist_ok=True)
        privkey_path = cls.SCHNORR_DIR / f"{username}_privkey.txt"
        with open(privkey_path, "w") as f:
            f.write(str(key))
        print(f"[CLIENT] INFO: chiave privata memorizzata in {privkey_path}.")


class ClientApp:
    def __init__(self, client_conn: ClientConnection):
        self.client_conn = client_conn

    def handshake(self, client: ClientConnection) -> bool:
        self.client_conn.send(MessageType.HANDSHAKE_REQ)
        print("[CLIENT] Richiesta di handshake inviata al server...")

        response = wait_for_response(client, {MessageType.GROUP_SELECTION.code})

        if response is None:
            return False

        print("[CLIENT] Fase di handshake...")

        self.client_conn.send(MessageType.HANDSHAKE_RES)

        if response.get("type_code") == MessageType.GROUP_SELECTION.code:
            group = response.get("group_id")
            print(f"[CLIENT] Gruppo selezionato dal server: {group}")

            if group not in GROUPS:
                print("[CLIENT] Gruppo crittografico non supportato dal client.")
                return False

            self.p = GROUPS[group]["p"]
            self.g = GROUPS[group]["g"]
            self.q = (self.p - 1) // 2

            return True

    def register(self) -> bool:
        username = input("Inserisci uno username per la registrazione: ").strip()
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
            print(f"[CLIENT] {MessageType.REGISTERED.message()}")
            KeyManager.save_private_key(username, alpha)
            return True
        else:
            print("[CLIENT] Risposta inattesa dal server:", response)
            return False

    def auth(self) -> bool:
        username = input("Inserisci uno username per l'autenticazione: ").strip()
        alpha = KeyManager.load_private_key(username)

        alpha_t = random.randint(1, self.q - 1)
        u_t = hex(pow(self.g, alpha_t, self.p))
        self.client_conn.send(MessageType.AUTH_REQUEST, {"temp": u_t, "username": username})

        response = wait_for_response(self.client_conn, {MessageType.CHALLENGE.code})
        if response is None:
            return False

        c = int(response["challenge"], 16)
        print(f"[CLIENT] Ricevuto challenge: {response['challenge'][:20]}...")

        alpha_z = (alpha_t + alpha * c) % self.q
        self.client_conn.send(MessageType.AUTH_RESPONSE, {"response": hex(alpha_z)})

        response = wait_for_response(
            self.client_conn, {MessageType.ACCEPTED.code, MessageType.REJECTED.code}
        )

        if response is None:
            return False

        if response.get("type_code") == MessageType.ACCEPTED.code:
            print("[CLIENT] Autenticazione riuscita!")
            return True
        elif response.get("type_code") == MessageType.REJECTED.code:
            print("[CLIENT] Autenticazione fallita.")
            return False

    def assoc(self) -> bool:
        device_name = get_device_name()

        alpha = random.randint(1, self.q - 1)
        public_key = hex(pow(self.g, alpha, self.p))

        # Invio della richiesta di associazione
        self.client_conn.send(MessageType.ASSOC_REQUEST, {"device": device_name, "pk": public_key})
        print("[CLIENT] Inviata richiesta di associazione del dispositivo")

        # Primo step: attendere il token da mostrare come QR
        response = wait_for_response(
            self.client_conn, {MessageType.TOKEN_ASSOC.code, MessageType.ERROR.code}
        )
        if response is None:
            return False

        if response.get("type_code") == MessageType.TOKEN_ASSOC.code:
            token = response.get("token")
            print(f"[CLIENT] Token ricevuto: {token}")
            create_qr_code(token)

        # Secondo step: attendere conferma di associazione
        response = wait_for_response(
            self.client_conn, {MessageType.ACCEPTED.code, MessageType.ERROR.code}
        )
        if response is None:
            return False

        if response.get("type_code") == MessageType.ACCEPTED.code:
            print("[CLIENT] Associazione completata, login effettuato!")
            KeyManager.save_private_key(response.get("username"), alpha)
            return True

    def confirm_assoc(self) -> bool:
        ans = input("[CLIENT] Inserisci codice di abbinamento: ").strip()

        self.client_conn.send(MessageType.TOKEN_ASSOC, {"token": ans})

        response = wait_for_response(self.client_conn, {MessageType.ACCEPTED.code})

        if response is None:
            return False

        if response.get("type_code") == MessageType.ACCEPTED.code:
            print("[CLIENT] Abbinamento confermato con successo.")
            return True

    def log_out(self) -> bool:
        self.client_conn.send(MessageType.LOGOUT)

        response = wait_for_response(self.client_conn, {MessageType.LOGGED_OUT.code})

        if response is None:
            return False

        if response.get("type_code") == MessageType.LOGGED_OUT.code:
            print("[CLIENT] Logout effettuato con successo.")
            return True


def wait_for_response(client: ClientConnection, expected_types: set[MessageType]):
    while True:
        msg = client.receive()

        if msg is None:
            print("[CLIENT] Connessione chiusa o messaggio vuoto.")
            return None

        if msg.get("type_code") in expected_types:
            return msg
        elif msg.get("type_code") == MessageType.ERROR.code:
            err = ErrorType.from_code(msg["error_code"])
            print(f"[CLIENT] Errore: {err.message()}")
            return None
        else:
            print("[CLIENT] Messaggio inatteso:", msg)


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


# --- MAIN ---
def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"[CLIENT] Connesso a {HOST}:{PORT}")

        client_conn = ClientConnection(sock)
        app = ClientApp(client_conn)

        if not app.handshake(client_conn):
            sys.exit(1)

        print("[CLIENT] Handshake andato a buon fine...")

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
                print(
                    "\n[CLIENT] Seleziona un'opzione:\n"
                    "  [R] Registrati\n"
                    "  [A] Accedi\n"
                    "  [D] Richiedi abbinamento dispositivo\n"
                    "  [Q] Esci\n"
                )
                ans = input("[CLIENT] Inserisci la tua scelta: ").strip().upper()
                action = actions_not_logged.get(ans)
                if action:
                    success = action()
                    if success:
                        logged_in = True
                else:
                    print("[CLIENT] Input non valido.")
            else:
                print(
                    "\n[CLIENT] Seleziona un'opzione:\n"
                    "  [L] Log out\n"
                    "  [C] Conferma abbinamento dispositivo\n"
                    "  [Q] Esci\n"
                )
                ans = input("[CLIENT] Inserisci la tua scelta: ").strip().upper()
                action = actions_logged.get(ans)
                if action:
                    success = action()
                    if ans == "L" and success:
                        logged_in = False
                else:
                    print("[CLIENT] Input non valido.")


if __name__ == "__main__":
    main()
