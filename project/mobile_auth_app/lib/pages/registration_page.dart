import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:schnorr_auth_app/models/session_manager.dart';
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

  Widget _buildDescription(BuildContext context) {
    return Text(
      'Inserisci un nome utente per autenticarti con il protocollo di identificazione di Schnorr.',
      textAlign: TextAlign.center,
      style: TextStyle(fontSize: 16, color: Theme.of(context).colorScheme.primary, fontWeight: FontWeight.bold),
    );
  }

  Widget _buildActionButtons(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _ActionButton(
            label: 'REGISTRATI',
            color: Theme.of(context).colorScheme.primary,
            textColor: Theme.of(context).colorScheme.onPrimary,
            onPressed: () async {
              final username = _usernameController.text.trim();
              if (username.isEmpty) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(const SnackBar(content: Text('Il nome utente non può essere vuoto')));
                return;
              }

              try {
                final success = await widget.authService.register(username, context);
                if (!mounted) return;

                if (success) {
                  Provider.of<SessionManager>(context, listen: false).login(username);
                  ScaffoldMessenger.of(context)
                    ..hideCurrentMaterialBanner
                    ..showSnackBar(
                      SnackBar(content: Text('Registrazione Completata'), duration: const Duration(seconds: 2)),
                    );
                }
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context)
                  ..hideCurrentMaterialBanner
                  ..showSnackBar(
                    SnackBar(
                      content: Text('Errore durante la registrazione: $e'),
                      duration: const Duration(seconds: 2),
                    ),
                  );
              }
            },
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _ActionButton(
            label: 'ACCEDI',
            color: Theme.of(context).colorScheme.primary,
            textColor: Theme.of(context).colorScheme.onPrimary,
            onPressed: () async {
              final username = _usernameController.text.trim();
              if (username.isEmpty) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(const SnackBar(content: Text('Il nome utente non può essere vuoto')));
                return;
              }

              try {
                final success = await widget.authService.authenticate(username, context);
                if (!mounted) return;

                if (success) {
                  Provider.of<SessionManager>(context, listen: false).login(username);
                  ScaffoldMessenger.of(context)
                    ..hideCurrentSnackBar()
                    ..showSnackBar(
                      SnackBar(content: Text('Autenticazione riuscita'), duration: const Duration(seconds: 2)),
                    );
                } else {
                  ScaffoldMessenger.of(context)
                    ..hideCurrentSnackBar()
                    ..showSnackBar(
                      SnackBar(
                        content: Text('Non è stato possibile autenticarti'),
                        duration: const Duration(seconds: 2),
                      ),
                    );
                }
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Autenticazione fallita: $e')));
                print(e);
              }
            },
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            buildTitle(context),
            const SizedBox(height: 12),
            buildLogo(),
            const SizedBox(height: 12),
            _buildDescription(context),
            const SizedBox(height: 32),
            buildUsernameField(_usernameController),
            const SizedBox(height: 16),
            FractionallySizedBox(widthFactor: 1.0, child: _buildActionButtons(context)),
          ],
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final Color color;
  final Color textColor;
  final VoidCallback onPressed;

  const _ActionButton({required this.label, required this.color, required this.textColor, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: textColor,
        padding: const EdgeInsets.symmetric(vertical: 20),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      onPressed: onPressed,
      child: Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
    );
  }
}
