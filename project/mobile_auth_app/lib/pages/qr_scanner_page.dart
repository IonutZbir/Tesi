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
  final String host = '192.168.1.168';
  final int port = 65432;

  @override
  void initState() {
    super.initState();
    _socket = SocketService(host: host, port: port);
    print("[CLIENT]: Scanner pronto, in attesa di QR...");
  }

  void _onDetect(BarcodeCapture capture) {
    if (_isProcessing || capture.barcodes.isEmpty) return;

    final barcode = capture.barcodes.first;
    final String? token = barcode.rawValue;

    if (token == null || token.isEmpty) return;

    setState(() => _isProcessing = true);
    _controller.stop();

    print('[CLIENT]: Token letto: $token');
    print('[CLIENT]: Mi sto collegando a: $host:$port');

    _socket.connectAndSendToken(token);

    // Mostra subito il dialog con il token letto
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: Colors.white,
        title: const Text('Token letto'),
        content: Text(token),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              _controller.start();
              setState(() => _isProcessing = false);
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _socket.dispose();
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
