import 'package:flutter/material.dart';
import 'package:schnorr_auth_app/widgets/button.dart';

class SettingsPage extends StatefulWidget {
  final String initialIp;
  final int initialPort;

  const SettingsPage({super.key, required this.initialIp, required this.initialPort});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late TextEditingController _ipController;
  late TextEditingController _portController;
  bool _darkMode = false;

  @override
  void initState() {
    super.initState();
    _ipController = TextEditingController(text: widget.initialIp);
    _portController = TextEditingController(text: widget.initialPort.toString());
  }

  @override
  void dispose() {
    _ipController.dispose();
    _portController.dispose();
    super.dispose();
  }

  void _saveSettings() {
    Navigator.pop(context, {
      'ip': _ipController.text,
      'port': int.tryParse(_portController.text) ?? widget.initialPort,
      'darkMode': _darkMode,
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Impostazioni")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _ipController,
              decoration: const InputDecoration(labelText: "IP Server"),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _portController,
              decoration: const InputDecoration(labelText: "Porta Server"),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: 400,
              child: ActionButton(
                label: 'SALVA',
                color: Theme.of(context).colorScheme.primary,
                textColor: Theme.of(context).colorScheme.onPrimary,
                onPressed: _saveSettings,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
