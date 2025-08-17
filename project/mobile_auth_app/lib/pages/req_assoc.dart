import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:schnorr_auth_app/models/session_manager.dart';
import 'package:schnorr_auth_app/services/auth_service.dart';
import 'package:schnorr_auth_app/widgets/logo.dart';
import 'package:schnorr_auth_app/widgets/title.dart';

class ReqAssoc extends StatefulWidget {
  final AuthService authService;
  const ReqAssoc({super.key, required this.authService});

  @override
  State<ReqAssoc> createState() => _ReqAssocState();
}

class _ReqAssocState extends State<ReqAssoc> {
  bool _showToken = false;

  @override
  Widget build(BuildContext context) {
    final token = Provider.of<SessionManager>(context).token;
    final hasToken = token != null && token.isNotEmpty;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                buildTitle(context),
                const SizedBox(height: 12),
                buildLogo(),
                const SizedBox(height: 12),
                _buildQrDescription(context),
                const SizedBox(height: 32),
                if (hasToken)
                  QrImageView(data: token, size: 260)
                else
                  _buildLoadingSection(),
                const SizedBox(height: 16),
                if (hasToken) _buildTokenSection(context, token!),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildQrDescription(BuildContext context) {
    return Text(
      'Scansiona il codice QR con il tuo dispositivo per completare l’associazione.',
      textAlign: TextAlign.center,
      style: TextStyle(
        fontSize: 16,
        color: Theme.of(context).colorScheme.primary,
        fontWeight: FontWeight.bold,
      ),
    );
  }

  Widget _buildLoadingSection() {
    return Column(
      children: const [
        CircularProgressIndicator(),
        SizedBox(height: 8),
        Text('In attesa del token dal server...'),
      ],
    );
  }

  Widget _buildTokenSection(BuildContext context, String token) {
    final theme = Theme.of(context);

    return Column(
      children: [
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: theme.colorScheme.primary,
            foregroundColor: theme.colorScheme.onPrimary,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            textStyle: const TextStyle(fontSize: 14),
          ),
          onPressed: () => setState(() => _showToken = !_showToken),
          icon: Icon(
            _showToken ? Icons.visibility_off : Icons.visibility,
            size: 18,
          ),
          label: Text(_showToken ? 'Nascondi token' : 'Mostra token'),
        ),
        if (_showToken) ...[
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Flexible(
                child: SelectableText(
                  token,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 14, fontFamily: 'monospace'),
                ),
              ),
              IconButton(
                tooltip: 'Copia token',
                icon: const Icon(Icons.copy, size: 18),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: token));
                  _showSnack(context, theme);
                },
              ),
            ],
          ),
        ],
      ],
    );
  }

  void _showSnack(BuildContext context, ThemeData theme) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        duration: const Duration(seconds: 2),
        backgroundColor: theme.colorScheme.primary,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        content: Text(
          'Token copiato nella clipboard',
          style: TextStyle(
            color: theme.colorScheme.onPrimary,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}
