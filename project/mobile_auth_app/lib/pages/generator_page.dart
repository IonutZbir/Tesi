import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/app_state.dart';
import '../widgets/big_card.dart';
import '../services/socket_service.dart';

class GeneratorPage extends StatefulWidget {
  const GeneratorPage({super.key});

  @override
  State<GeneratorPage> createState() => _GeneratorPageState();
}

class _GeneratorPageState extends State<GeneratorPage> {
  late SocketService socket;

  @override
  void initState() {
    super.initState();
    socket = SocketService(url: 'ws://192.168.1.168:65432', onMessage: _handleServerMessage);
  }

  void _handleServerMessage(String message) {
    print('[GENERATOR]: Ricevuto messaggio -> $message');
    // Puoi aggiungere un dialog o un snackbar se vuoi
  }

  void _sendTestMessage() {
    socket.sendMessage({'type': 'generator', 'message': 'Invio da GeneratorPage'});
  }

  @override
  void dispose() {
    socket.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    var appState = context.watch<MyAppState>();
    var pair = appState.current;

    IconData icon = appState.favorites.contains(pair) ? Icons.favorite : Icons.favorite_border;

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          BigCard(pair: pair),
          const SizedBox(height: 10),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ElevatedButton.icon(icon: Icon(icon), label: const Text('Like'), onPressed: appState.toggleFavorite),
              const SizedBox(width: 10),
              ElevatedButton(onPressed: appState.getNext, child: const Text('Next')),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [ElevatedButton(onPressed: _sendTestMessage, child: const Text('Invia Messaggio'))],
          ),
        ],
      ),
    );
  }
}
