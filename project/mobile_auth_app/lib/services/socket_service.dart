import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/messages.dart';

class SocketService {
  late final WebSocketChannel _channel;
  final void Function(String message)? onMessage;

  SocketService({required String url, this.onMessage}) {
    _channel = WebSocketChannel.connect(Uri.parse(url));

    _channel.stream.listen(
      _handleMessage,
      onError: _handleError,
      onDone: _handleDone,
      cancelOnError: true,
    );
  }

  void _handleMessage(dynamic message) {
    try {
      print('[SOCKET]: Messaggio ricevuto -> $message');

      // Qui puoi già fare il decode se vuoi lavorare direttamente con JSON
      if (onMessage != null) {
        onMessage!(message.toString());
      }
    } catch (e) {
      print('[SOCKET ERROR]: Errore nella gestione del messaggio: $e');
    }
  }

  void _handleError(error) {
    print('[SOCKET ERROR]: Connessione fallita o interrotta: $error');
    // Potresti voler invocare una callback, o mostrare un messaggio all’utente
  }

  void _handleDone() {
    print('[SOCKET]: Connessione chiusa dal server.');
  }

  void sendToken(String token) {
    final message = jsonEncode({
      'type': MessageType.associateRequest.index,
      'token': token,
    });

    print('[SOCKET]: Invio token -> $message');
    _channel.sink.add(message);
  }

  void sendMessage(Map<String, dynamic> data) {
    final message = jsonEncode(data);
    print('[SOCKET]: Invio messaggio generico -> $message');
    _channel.sink.add(message);
  }

  void dispose() {
    _channel.sink.close();
  }
}
