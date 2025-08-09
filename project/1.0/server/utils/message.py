from enum import Enum

class MessageType(Enum):
    REGISTER = (0, "REGISTER", "Ricevuta richiesta di registrazione")
    GROUP_SELECTION = (1, "GROUP_SELECTION", "Invio selezione gruppo")
    ERROR = (2, "ERROR", "Errore generico ricevuto")
    CHALLENGE = (3, "CHALLENGE", "Invio sfida per autenticazione")
    AUTH_REQUEST = (4, "AUTH_REQUEST", "Ricevuta richiesta autenticazione")
    AUTH_RESPONSE = (5, "AUTH_RESPONSE", "Ricevuta risposta autenticazione")
    ACCEPTED = (6, "ACCEPTED", "Autenticazione accettata")
    REJECTED = (7, "REJECTED", "Autenticazione rifiutata")
    REGISTERED = (8, "REGISTERED", "Utente registrato con successo")
    ASSOC_REQUEST = (9, "ASSOC_REQUEST", "Richiesta abbinamento dispositivo")
    TOKEN_ASSOC = (10, "TOKEN_ASSOC", "Token di abbinamento ricevuto")
    LOGOUT = (11, "LOGOUT", "Richiesta di logout")
    HANDSHAKE_REQ = (12, "HANDSHAKE_REQ", "Richiesta handshake")
    HANDSHAKE_RES = (13, "HANDSHAKE_RES", "Risposta handshake")
    LOGGED_OUT = (14, "LOGGED_OUT", "Logout effettuato")

    def __init__(self, code, label, log_message):
        self.code = code
        self.label = label
        self.log_message = log_message

    @classmethod
    def from_code(cls, code):
        for item in cls:
            if item.code == code:
                return item
        return None

    def __str__(self):
        return self.label

    def message(self):
        return self.log_message


class ErrorType(Enum):
    USERNAME_ALREADY_EXISTS = (0, "USERNAME_ALREADY_EXISTS", "Username già esistente")
    USERNAME_NOT_FOUND = (1, "USERNAME_NOT_FOUND", "Username non trovato")
    UNKNOWN_ERROR = (2, "UNKNOWN_ERROR", "Errore sconosciuto")
    SESSION_NOT_FOUND = (3, "SESSION_NOT_FOUND", "Sessione non trovata")

    def __init__(self, code, label, log_message):
        self.code = code
        self.label = label
        self.log_message = log_message

    @classmethod
    def from_code(cls, code):
        for item in cls:
            if item.code == code:
                return item
        return None

    def __str__(self):
        return self.label

    def message(self):
        return self.log_message

# Ottieni enum da codice
# msg_type = MessageType.from_code(4)
# print(msg_type)             # AUTH_REQUEST
# print(msg_type.log())       # Ricevuta richiesta autenticazione

# err = ErrorType.USERNAME_ALREADY_EXISTS
# print(err)                  # USERNAME_ALREADY_EXISTS
# print(err.message())        # Username già esistente
