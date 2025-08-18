# exceptions.py

from utils.message import ErrorType

class ValidationError(Exception):
    """Messaggio ricevuto non valido o con campi mancanti."""
    pass

class UnsupportedMessageTypeError(Exception):
    """Tipo di messaggio non riconosciuto dal server."""
    pass

class AuthenticationError(Exception):
    """Autenticazione fallita (credenziali errate o assenti)."""
    pass

class AuthorizationError(Exception):
    """Accesso negato: permessi insufficienti per l'operazione."""
    pass

class TokenExpiredError(Exception):
    """Il token è scaduto."""
    pass

class TokenNotFoundError(Exception):
    """Token non trovato nel database."""
    pass

class ProtocolError(Exception):
    """Violazione del protocollo o sequenza di messaggi non valida."""
    pass

class ConnectionClosedError(Exception):
    """Connessione chiusa inaspettatamente dal client."""
    pass


def exception_to_error_type(exc: Exception) -> ErrorType:
    """
    Mappa un'eccezione personalizzata a un ErrorType definito nel protocollo.

    Args:
        exc (Exception): L'eccezione sollevata.

    Returns:
        ErrorType: Il corrispondente ErrorType da inviare al client.
    """
    if isinstance(exc, ValidationError):
        return ErrorType.MALFORMED_MESSAGE
    if isinstance(exc, UnsupportedMessageTypeError):
        return ErrorType.UNKNOWN_ERROR
    if isinstance(exc, AuthenticationError):
        return ErrorType.SESSION_NOT_FOUND
    if isinstance(exc, AuthorizationError):
        return ErrorType.NO_MAIN_DEVICE
    if isinstance(exc, TokenExpiredError):
        return ErrorType.TOKEN_INVALID_OR_EXPIRED
    if isinstance(exc, TokenNotFoundError):
        return ErrorType.TOKEN_INVALID_OR_EXPIRED
    if isinstance(exc, ProtocolError):
        return ErrorType.UNKNOWN_ERROR
    if isinstance(exc, ConnectionClosedError):
        return ErrorType.UNKNOWN_ERROR

    # Default
    return ErrorType.UNKNOWN_ERROR
