// errortype.dart

enum ErrorType {
  usernameAlreadyExists(0, "USERNAME_ALREADY_EXISTS", "Username già esistente"),
  usernameNotFound(1, "USERNAME_NOT_FOUND", "Username non trovato"),
  unknownError(2, "UNKNOWN_ERROR", "Errore sconosciuto"),
  sessionNotFound(3, "SESSION_NOT_FOUND", "Sessione non trovata"),
  noMainDevice(4, "NO_MAIN_DEVICE", "L'abbinamento deve essere confermato dal dispositivo principale"),
  malformedMessage(5, "MALFORMED_MESSAGE", "Messaggio malformato o campi mancanti"),
  tokenInvalidOrExpired(6, "TOKEN_INVALID_OR_EXPIRED", "Token non valido o scaduto"),
  unauthorized(7, "UNAUTHORIZED", "Operazione non autorizzata"),
  deviceAlreadyRegistered(8, "DEVICE_ALREADY_REGISTERED", "Il dispositivo risulta già registrato"),
  assocFailure(9, "ASSOC_FAILURE", "Associazione del dispositivo non riuscita");

  final int code;
  final String label;
  final String logMessage;

  const ErrorType(this.code, this.label, this.logMessage);

  static ErrorType? fromCode(int code) {
    for (final e in ErrorType.values) {
      if (e.code == code) return e;
    }
    return null;
  }

  @override
  String toString() => label;

  String message() => logMessage;
}
