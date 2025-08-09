import 'dart:convert';
import 'dart:io';
import '../models/messages.dart';

class SocketService {
  Socket? _socket;
  final String host;
  final int port;
  final void Function(String message)? onMessage;

  SocketService({required this.host, required this.port, this.onMessage});

  Future<void> connectAndSendToken(String token) async {
    try {
      _socket = await Socket.connect(host, port);
      print('[SOCKET]: Connessione aperta verso $host:$port');

      // Ascolta i messaggi in arrivo dal server
      _socket!.listen(
        (data) {
          final message = utf8.decode(data);
          print('[SOCKET]: Messaggio ricevuto -> $message');
          if (onMessage != null) {
            onMessage!(message);
          }
        },
        onError: (error) {
          print('[SOCKET ERROR]: Errore nella connessione: $error');
        },
        onDone: () {
          print('[SOCKET]: Connessione chiusa dal server.');
          dispose();
        },
      );

      final message = jsonEncode({
        'type': MessageType.tokenAssoc.index,
        'token': token,
      });

      print('[SOCKET]: Invio token -> $message');

      // Invia il messaggio al server (aggiungi newline se il server lo richiede)
      _socket!.write(message);
      // Se necessario, puoi inviare un delimitatore come newline: _socket!.write("$message\n");

    } catch (e) {
      print('[SOCKET ERROR]: Errore durante la connessione -> $e');
    }
  }

  void dispose() {
    _socket?.destroy();
    _socket = null;
  }
}
