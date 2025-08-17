import 'package:flutter/material.dart';
import 'package:schnorr_auth_app/widgets/button.dart';
import 'package:schnorr_auth_app/widgets/logo.dart';
import 'package:schnorr_auth_app/widgets/title.dart';
import 'package:schnorr_auth_app/services/auth_service.dart';

class TokenInputPage extends StatefulWidget {
  final AuthService authService;
  const TokenInputPage({super.key, required this.authService});

  @override
  State<TokenInputPage> createState() => _TokenInputPageState();
}

class _TokenInputPageState extends State<TokenInputPage> {
  final TextEditingController _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submitToken() {
    final token = _controller.text.trim();

    if (token.isEmpty || token.length != 32) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text("Il token deve essere lungo 32 caratteri")));
      return;
    }

    widget.authService.confirmAssoc(context, token);

    print("[CLIENT]: Token inserito manualmente: $token");

    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Token inviato con successo")));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false, // non serve sugli schermi desktop
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center, // centra verticalmente
            crossAxisAlignment: CrossAxisAlignment.center, // centra orizzontalmente
            mainAxisSize: MainAxisSize.min,
            children: [
              buildTitle(context),
              const SizedBox(height: 12),
              buildLogo(),
              const SizedBox(height: 12),
              Text(
                "Inserisci il token fornito per completare l’associazione.",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: 600, // fisso per desktop
                child: TextField(
                  controller: _controller,
                  decoration: const InputDecoration(border: OutlineInputBorder(), labelText: "Token"),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: 600, // uguale al TextField
                child: ActionButton(
                  label: 'INVIA TOKEN',
                  color: Theme.of(context).colorScheme.primary,
                  textColor: Theme.of(context).colorScheme.onPrimary,
                  onPressed: _submitToken, // nota: aggiunto () qui
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
