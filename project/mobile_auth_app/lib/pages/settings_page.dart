import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:schnorr_auth_app/widgets/button.dart';

class SettingsPage extends StatefulWidget {
  final String initialIp;
  final int initialPort;

  const SettingsPage({
    super.key,
    required this.initialIp,
    required this.initialPort,
  });

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late TextEditingController _ipController;
  late TextEditingController _portController;

  @override
  void initState() {
    super.initState();
    _ipController = TextEditingController();
    _portController = TextEditingController();
    _loadSettings();
  }

  @override
  void dispose() {
    _ipController.dispose();
    _portController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _ipController.text = prefs.getString('ip') ?? widget.initialIp;
      _portController.text =
          (prefs.getInt('port') ?? widget.initialPort).toString();
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final ip = _ipController.text;
    final port = int.tryParse(_portController.text) ?? widget.initialPort;

    await prefs.setString('ip', ip);
    await prefs.setInt('port', port);

    if (mounted) {
      Navigator.pop(context, {
        'ip': ip,
        'port': port,
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Impostazioni")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // Riquadro con info server online
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: const [
                    Icon(Icons.cloud_done, color: Colors.green),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        "Server Online: 51.210.242.104:65432",
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
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
