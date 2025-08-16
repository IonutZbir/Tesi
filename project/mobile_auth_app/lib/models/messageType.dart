// messagetype.dart

enum MessageType {
  register(0, "REGISTER", "Ricevuta richiesta di registrazione"),
  groupSelection(1, "GROUP_SELECTION", "Invio selezione gruppo"),
  error(2, "ERROR", "Errore generico ricevuto"),
  challenge(3, "CHALLENGE", "Invio sfida per autenticazione"),
  authRequest(4, "AUTH_REQUEST", "Ricevuta richiesta autenticazione"),
  authResponse(5, "AUTH_RESPONSE", "Ricevuta risposta autenticazione"),
  accepted(6, "ACCEPTED", "Autenticazione accettata"),
  rejected(7, "REJECTED", "Autenticazione rifiutata"),
  registered(8, "REGISTERED", "Utente registrato con successo"),
  assocRequest(9, "ASSOC_REQUEST", "Richiesta abbinamento dispositivo"),
  tokenAssoc(10, "TOKEN_ASSOC", "Token di abbinamento ricevuto"),
  logout(11, "LOGOUT", "Richiesta di logout"),
  handshakeReq(12, "HANDSHAKE_REQ", "Richiesta handshake"),
  handshakeRes(13, "HANDSHAKE_RES", "Risposta handshake"),
  loggedOut(14, "LOGGED_OUT", "Logout effettuato"),
  devicesRequest(15, "DEVICES_REQUEST", "Richiesta elenco dispositivi"),
  devicesResponse(16, "DEVICES_RESPONSE", "Risposta elenco dispositivi");

  final int code;
  final String label;
  final String logMessage;

  const MessageType(this.code, this.label, this.logMessage);

  static MessageType? fromCode(int code) {
    for (final e in MessageType.values) {
      if (e.code == code) return e;
    }
    return null;
  }

  @override
  String toString() => label;

  String message() => logMessage;
}
