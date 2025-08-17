import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:schnorr_auth_app/models/session_manager.dart';
import 'package:schnorr_auth_app/widgets/button.dart';
import 'package:schnorr_auth_app/widgets/logo.dart';
import 'package:schnorr_auth_app/widgets/title.dart';
import 'package:schnorr_auth_app/widgets/username_field.dart';
import 'package:schnorr_auth_app/services/auth_service.dart';

class RegistrationPage extends StatefulWidget {
  final AuthService authService;
  const RegistrationPage({super.key, required this.authService});

  @override
  State<RegistrationPage> createState() => _RegistrationPageState();
}

class _RegistrationPageState extends State<RegistrationPage> {
  final TextEditingController _usernameController = TextEditingController();

  @override
  void dispose() {
    _usernameController.dispose();
    super.dispose();
  }

  Future<void> _handleRegister(BuildContext context) async {
    final username = _usernameController.text.trim();
    if (username.isEmpty) {
      _showSnack(context, 'Il nome utente non può essere vuoto');
      return;
    }

    try {
      final success = await widget.authService.register(username, context);
      if (!mounted) return;

      if (success) {
        Provider.of<SessionManager>(context, listen: false).login(username);
        _showSnack(context, 'Registrazione completata');
      }
    } catch (e) {
      if (!mounted) return;
      _showSnack(context, 'Errore durante la registrazione: $e');
    }
  }

  Future<void> _handleLogin(BuildContext context) async {
    final username = _usernameController.text.trim();
    if (username.isEmpty) {
      _showSnack(context, 'Il nome utente non può essere vuoto');
      return;
    }

    try {
      final success = await widget.authService.authenticate(username, context);
      if (!mounted) return;

      if (success) {
        Provider.of<SessionManager>(context, listen: false).login(username);
        _showSnack(context, 'Autenticazione riuscita');
      } else {
        _showSnack(context, 'Non è stato possibile autenticarti');
      }
    } catch (e) {
      if (!mounted) return;
      _showSnack(context, 'Autenticazione fallita: $e');
    }
  }

  void _showSnack(BuildContext context, String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message), duration: const Duration(seconds: 2)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: true, // fondamentale per adattarsi alla tastiera
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                buildTitle(context),
                const SizedBox(height: 12),
                buildLogo(),
                const SizedBox(height: 12),
                Text(
                  'Inserisci un nome utente per autenticarti con il protocollo di identificazione di Schnorr.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 16,
                    color: Theme.of(context).colorScheme.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 32),
                buildUsernameField(_usernameController),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: ActionButton(
                        label: 'REGISTRATI',
                        color: Theme.of(context).colorScheme.primary,
                        textColor: Theme.of(context).colorScheme.onPrimary,
                        onPressed: () => _handleRegister(context),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ActionButton(
                        label: 'ACCEDI',
                        color: Theme.of(context).colorScheme.primary,
                        textColor: Theme.of(context).colorScheme.onPrimary,
                        onPressed: () => _handleLogin(context),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}


