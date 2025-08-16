import 'dart:convert';
import 'dart:io';
import '../models/messageType.dart';

class SocketService {
  Socket? _socket;
  late Stream<List<int>> _socketStream;
  final String host;
  final int port;
  final void Function(Map<String, dynamic> message)? onMessage;
  final Future<void> Function() onConnect;

  // coda dei messaggi ricevuti
  final List<Map<String, dynamic>> _messageQueue = [];

  SocketService({
    required this.host,
    required this.port,
    this.onMessage,
    required this.onConnect,
  });

  /// Connessione al server
  Future<void> connect() async {
    try {
      _socket = await Socket.connect(host, port);

      print('[SOCKET]: Connessione aperta verso $host:$port');

      // Trasforma lo stream in broadcast così possiamo ascoltarlo più volte
      _socketStream = _socket!.asBroadcastStream();

      // ascolta i messaggi in arrivo e mettili nella coda
      _socketStream.listen(_onData, onDone: () {
        print('[SOCKET]: Connessione chiusa dal server');
        dispose();
      }, onError: (error) {
        print('[SOCKET ERROR]: $error');
      });

      // notifica la connessione avvenuta
      await onConnect();
    } catch (e) {
      print('[SOCKET ERROR]: Errore durante la connessione -> $e');
    }
  }

  void _onData(List<int> data) {
    try {
      final messageString = utf8.decode(data);
      final decoded = jsonDecode(messageString);
      if (decoded is Map<String, dynamic>) {
        _messageQueue.add(decoded);
        if (onMessage != null) onMessage!(decoded);
      } else {
        print('[SOCKET ERROR]: Messaggio non valido -> $decoded');
      }
    } catch (e) {
      print('[SOCKET ERROR]: Errore nel parsing del messaggio JSON -> $e');
    }
  }

  /// Riceve un singolo messaggio dalla coda
  Future<Map<String, dynamic>?> receiveOnce() async {
    while (_messageQueue.isEmpty) {
      // attende che arrivi almeno un messaggio
      await Future.delayed(const Duration(milliseconds: 50));
    }
    return _messageQueue.removeAt(0);
  }

  /// Invio messaggi generici in formato JSON
  void send(MessageType msgType, {Map<String, dynamic>? extraData}) {
    final payload = {
      "type_code": msgType.code,
      "type": msgType.label,
      if (extraData != null) ...extraData,
    };

    final jsonString = jsonEncode(payload);
    _socket?.write(jsonString);
    print("[SOCKET]: Messaggio inviato -> $jsonString");
  }

  /// Chiude la connessione
  void dispose() {
    _socket?.destroy();
    _socket = null;
  }
}
