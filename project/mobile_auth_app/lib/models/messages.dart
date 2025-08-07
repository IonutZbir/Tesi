// Enum per i tipi di messaggi
enum MessageType {
  register,
  groupSelection,
  error,
  challenge,
  authRequest,
  authResponse,
  accepted,
  rejected,
  registered,
  associateRequest,
  // More...
}

// Enum per i tipi di errore
enum ErrorType {
  usernameAlreadyExists,
  usernameNotFound,
  unknownError;

  static String message(ErrorType type) {
    switch (type) {
      case ErrorType.usernameAlreadyExists:
        return 'Username already exists.';
      case ErrorType.usernameNotFound:
        return 'Username not found.';
      case ErrorType.unknownError:
        return 'An unknown error occurred.';
      default:
        return 'Unknown error type.';
    }
  }
}
