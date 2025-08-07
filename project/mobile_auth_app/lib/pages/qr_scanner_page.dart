import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../services/socket_service.dart';

class QrCodeScannerPage extends StatefulWidget {
  const QrCodeScannerPage({super.key});

  @override
  State<QrCodeScannerPage> createState() => _QrCodeScannerPageState();
}

class _QrCodeScannerPageState extends State<QrCodeScannerPage> {
  final MobileScannerController _controller = MobileScannerController();
  bool _isProcessing = false;

  late SocketService _socket;

  @override
  void initState() {
    super.initState();

    var url = 'ws://192.168.1.168:65432';

    _socket = SocketService(
      url: url,
      onMessage: _handleServerMessage,
    );
    print("[CLIENT]: Mi sto collegando a: $url");
  }

  void _handleServerMessage(String message) {
    print('[CLIENT]: Ricevuto dal server -> $message');

    // Mostra un dialog con la risposta del server
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Risposta del server'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              _controller.start();
              _isProcessing = false;
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _onDetect(BarcodeCapture capture) {
  if (_isProcessing) return;

  if (capture.barcodes.isEmpty) return;

  final barcode = capture.barcodes.first;
  final String? token = barcode.rawValue;

  if (token == null || token.isEmpty) return;

  try {
    _isProcessing = true;
    _controller.stop();

    print('[CLIENT]: Token letto: $token');
    _socket.sendToken(token);
  } catch (e, stacktrace) {
    print('[ERROR] Errore in _onDetect: $e');
    print(stacktrace);

    // In caso di errore, riabilita la scansione
    _isProcessing = false;
    _controller.start();
  }
}


  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scanner QR Code')),
      body: MobileScanner(
        controller: _controller,
        onDetect: _onDetect,
      ),
    );
  }
}