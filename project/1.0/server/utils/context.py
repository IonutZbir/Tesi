import json
import socket
import datetime

from typing import Optional, Any, Dict

from utils.message import ErrorType, MessageType
from dataclasses import dataclass

from models.user import User


@dataclass
class SessionData:
    user: User = None
    logged_device: Optional[str] = None
    login_time: datetime.datetime = None
    temp_pk: Optional[int] = None
    challenge: Optional[int] = None

    def is_authenticated(self) -> bool:
        return self.user is not None


class ConnContext:
    MESSAGE_LENGTH = 4096

    def __init__(self, conn: socket.socket, addr: str):
        self.conn = conn
        self.addr = addr
        self.session = SessionData()
        self._closed = False

    def close(self) -> None:
        """Chiude la connessione e pulisce i dati di sessione."""
        if self._closed:
            return
        try:
            self.conn.close()
        except Exception as e:
            print(f"[SERVER] Errore durante la chiusura di {self.addr}: {e}")
        finally:
            self.clear_session()
            self._closed = True
            print(f"[SERVER] Connessione con {self.addr} chiusa.")

    def update_session(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.session, key):
                setattr(self.session, key, value)

    def get_session_data(self) -> Dict[str, Any]:
        """Restituisce una copia dei dati di sessione."""
        return self.session.copy()

    def clear_session(self):
        self.session = SessionData()  # reset

    @property
    def is_session_empty(self) -> bool:
        return not self.session.is_authenticated()

    def _send_json(self, message: Dict[str, Any]) -> bool:
        """Invia un messaggio JSON al client."""
        if self._closed:
            print(f"[SERVER] Tentativo di invio a {self.addr}, ma connessione già chiusa.")
            return False
        try:
            self.conn.sendall(json.dumps(message).encode())
            return True
        except (BrokenPipeError, ConnectionResetError):
            print(f"[SERVER] Errore: connessione chiusa dal client {self.addr} durante l'invio")
            self.close()
            return False

    def receive_json(self) -> Optional[Dict[str, Any]]:
        """Riceve un messaggio JSON dal client."""
        if self._closed:
            return None
        try:
            data = self.conn.recv(self.MESSAGE_LENGTH)
            if not data:
                self.close()
                return None
            return json.loads(data.decode())
        except json.JSONDecodeError:
            print(f"[SERVER] Errore: messaggio JSON non valido da {self.addr}")
            return None
        except ConnectionResetError:
            self.close()
            return None

    def send_message(
        self, msg_type: MessageType, extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Invia un messaggio standard al client."""
        payload = {
            "type_code": msg_type.code,
            "type": msg_type.label,
        }
        if extra_data:
            payload.update(extra_data)
        return self._send_json(payload)

    def send_error(self, error_type: ErrorType, details: Optional[str] = None) -> bool:
        """Invia un messaggio di errore al client."""
        payload = {
            "type_code": MessageType.ERROR.code,
            "type": MessageType.ERROR.label,
            "error_code": error_type.code,
            "error": error_type.label,
            "message": error_type.message(),
        }
        if details:
            payload["details"] = details
        return self._send_json(payload)
