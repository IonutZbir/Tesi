import 'package:flutter/material.dart';
import 'package:schnorr_auth_app/widgets/logo.dart';
import 'package:schnorr_auth_app/widgets/title.dart';
import 'package:schnorr_auth_app/widgets/username_field.dart';

class RegistrationPage extends StatefulWidget {
  const RegistrationPage({super.key});

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
      style: TextStyle(
        fontSize: 16,
        color: Theme.of(context).colorScheme.primary,
        fontWeight: FontWeight.bold,
      ),
    );
  }

  

  // Extracted as a widget stored on the state
  late final Widget _actionButtons = Builder(
    builder: (context) {
      final scheme = Theme.of(context).colorScheme;
      return Row(
        children: [
          Expanded(
            child: _ActionButton(
              label: 'REGISTRATI',
              color: scheme.primary,
              textColor: scheme.onPrimary,
              onPressed: () {
                final username = _usernameController.text;
                print('Username: $username');
              },
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _ActionButton(
              label: 'ACCEDI',
              color: scheme.primary,
              textColor: scheme.onPrimary,
              onPressed: () {
                print('Accedi premuto');
                // Navigator.pushNamed(context, '/login');
              },
            ),
          ),
        ],
      );
    },
  );

  // Keep the same method signature for existing usage
  Widget _buildActionButtons(BuildContext context) => _actionButtons;

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
            FractionallySizedBox(
              widthFactor: 1.0,
              child: _buildActionButtons(context),
            ),
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

  const _ActionButton({
    required this.label,
    required this.color,
    required this.textColor,
    required this.onPressed,
  });

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
