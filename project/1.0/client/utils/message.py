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
    DEVICES_REQUEST = (15, "DEVICES_REQUEST", "Richiesta elenco dispositivi")
    DEVICES_RESPONSE = (16, "DEVICES_RESPONSE", "Risposta elenco dispositivi")

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
    NO_MAIN_DEVICE = (4, "NO_MAIN_DEVICE", "L'abbinamento deve essere confermato dal dispositivo principale")
    MALFORMED_MESSAGE = (5, "MALFORMED_MESSAGE", "Messaggio malformato o campi mancanti")
    TOKEN_INVALID_OR_EXPIRED = (6, "TOKEN_INVALID_OR_EXPIRED", "Token non valido o scaduto")
    UNAUTHORIZED = (7, "UNAUTHORIZED", "Operazione non autorizzata")
    DEVICE_ALREADY_REGISTERED = (8, "DEVICE_ALREADY_REGISTERED", "Il dispositivo risulta già registrato")
    ASSOC_FAILURE = (9, "ASSOC_FAILURE", "Associazione del dispositivo non riuscita")


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

