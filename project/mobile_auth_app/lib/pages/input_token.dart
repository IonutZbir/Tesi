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
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submitToken() async {
    if (!_formKey.currentState!.validate()) return;

    final token = _controller.text.trim();
    debugPrint("[CLIENT]: Token inserito manualmente: $token");

    await widget.authService.confirmAssoc(token);

    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Token inviato con successo")));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: false, // irrilevante su desktop
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 600),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.center,
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
                    TextFormField(
                      controller: _controller,
                      decoration: const InputDecoration(border: OutlineInputBorder(), labelText: "Token"),
                      validator: (value) {
                        final token = value?.trim() ?? "";
                        if (token.isEmpty) {
                          return "Il token non può essere vuoto";
                        }
                        if (token.length != 32) {
                          return "Il token deve essere lungo 32 caratteri";
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity, // prende tutta la larghezza del form
                      height: 50, // altezza personalizzata
                      child: ActionButton(
                        label: 'INVIA TOKEN',
                        color: Theme.of(context).colorScheme.primary,
                        textColor: Theme.of(context).colorScheme.onPrimary,
                        onPressed: _submitToken,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
