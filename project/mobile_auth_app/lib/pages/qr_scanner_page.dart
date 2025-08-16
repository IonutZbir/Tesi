import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:schnorr_auth_app/services/auth_service.dart';

class QrCodeScannerPage extends StatefulWidget {
  final AuthService authService;
  const QrCodeScannerPage({super.key, required this.authService});

  @override
  State<QrCodeScannerPage> createState() => _QrCodeScannerPageState();
}

class _QrCodeScannerPageState extends State<QrCodeScannerPage> {
  final MobileScannerController _controller = MobileScannerController();
  bool _isProcessing = false;


  void _onDetect(BarcodeCapture capture) {
    if (_isProcessing || capture.barcodes.isEmpty) return;

    final barcode = capture.barcodes.first;
    final String? token = barcode.rawValue;

    if (token == null || token.isEmpty) return;

    setState(() => _isProcessing = true);
    _controller.stop();

    print('[CLIENT]: Token letto: $token');

    // _socket.connectAndSendToken(token);

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
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scanner QR Code')),
      // body: MobileScanner(controller: _controller, onDetect: _onDetect),
    );
  }
}
