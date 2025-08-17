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

    widget.authService.confirmAssoc(context, token);

    print('[CLIENT]: Token letto: $token');

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("Token letto: $token"),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 3),
      ),
    );

    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        _controller.start();
        setState(() => _isProcessing = false);
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Qr Scanner')),
      body: Stack(
        children: [
          // Scanner
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),
          // Overlay
          Column(
            children: [
              const SizedBox(height: 40),
              Center(
                child: Text(
                  "Scannerizza il codice",
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    shadows: [
                      Shadow(
                        blurRadius: 4,
                        color: Colors.black,
                        offset: Offset(1, 1),
                      )
                    ],
                  ),
                ),
              ),
              const Spacer(),
              Center(
                child: Container(
                  width: 250,
                  height: 250,
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: Colors.red,
                      width: 3,
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const Spacer(),
            ],
          ),
        ],
      ),
    );
  }
}
