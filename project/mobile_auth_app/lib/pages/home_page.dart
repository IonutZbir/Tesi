import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter/foundation.dart';
import 'package:schnorr_auth_app/widgets/button.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:schnorr_auth_app/models/session_manager.dart';
import 'package:schnorr_auth_app/pages/input_token.dart';
import 'package:schnorr_auth_app/pages/settings_page.dart';
import 'package:schnorr_auth_app/services/auth_service.dart';
import 'package:schnorr_auth_app/services/socket_service.dart';
import 'package:schnorr_auth_app/widgets/connected_devices.dart';

import 'req_assoc.dart';
import 'registration_page.dart';
import 'qr_scanner_page.dart';

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  SocketService? _socketService;
  AuthService? _authService;

  int _selectedIndex = 0;
  List<DeviceInfo> _devices = [];
  bool _devicesLoading = false;
  bool _isInitialized = false;

  String _serverIp = "192.168.1.168";
  int _serverPort = 65432;

  @override
  void initState() {
    super.initState();
    _loadServerSettings().then((_) => _initSocket());
  }

  Future<void> _loadServerSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _serverIp = prefs.getString('server_ip') ?? _serverIp;
      _serverPort = prefs.getInt('server_port') ?? _serverPort;
    });
  }

  Future<void> _initSocket() async {
    try {
      final socket = SocketService(
        host: _serverIp,
        port: _serverPort,
        onMessage: (msg) => debugPrint("[SOCKET]: $msg"),
      );

      final connected = await socket.connect().timeout(const Duration(seconds: 3), onTimeout: () => false);

      if (!connected) {
        _showSnack(context, "Impossibile connettersi al server ($_serverIp:$_serverPort)");
        return;
      }

      final auth = AuthService(socket);

      final success = await auth.handshake().timeout(
        const Duration(seconds: 3),
        onTimeout: () {
          _showSnack(context, "Handshake scaduto");
          return AuthResult.failure("Handshake scaduto");
        },
      );

      if (!success.success) {
        _showSnack(context, "Handshake fallito");
      }

      setState(() {
        _socketService = socket;
        _authService = auth;
      });
    } catch (e) {
      _showSnack(context, "Errore di connessione: $e");
    } finally {
      if (mounted) {
        setState(() => _isInitialized = true);
      }
    }
  }

  void _restartSocket(String newIp, int newPort) {
    _socketService?.dispose();
    setState(() {
      _serverIp = newIp;
      _serverPort = newPort;
      _isInitialized = false;
      _authService = null;
    });
    _initSocket();
  }

  @override
  void dispose() {
    _socketService?.dispose();
    super.dispose();
  }

  Future<void> _fetchDevices(String username) async {
    if (_authService == null) return;
    setState(() => _devicesLoading = true);
    final devices = await _authService!.fetchAssociatedDevices(username);
    setState(() {
      _devices = devices ?? [];
      _devicesLoading = false;
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = Provider.of<SessionManager>(context, listen: false);
    if (_isInitialized && session.isLoggedIn && !_devicesLoading) {
      _fetchDevices(session.username ?? "");
    }
  }

  Future<void> _handleLogout(SessionManager session) async {
    session.logout();
    setState(() => _selectedIndex = 0);
  }

  Future<void> _handleAssoc(SessionManager session) async {
    if (_authService == null) return;
    final result = await _authService!.assoc(context);
    if (!mounted) return;

    if (result.success) {
      setState(() => _selectedIndex = 0);
    } else {
      _showSnack(context, result.message ?? "Associazione fallita");
    }
  }

  List<Widget> _buildPages(SessionManager session) {
    final isMobile = defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS;

    if (session.isLoggedIn) {
      return [
        DevicesListWidget(username: session.username ?? "", devices: _devices),
        isMobile ? QrCodeScannerPage(authService: _authService!) : TokenInputPage(authService: _authService!),
        const SizedBox.shrink(),
      ];
    } else {
      return [RegistrationPage(authService: _authService!), ReqAssoc(authService: _authService!)];
    }
  }

  List<BottomNavigationBarItem> _buildNavItems(SessionManager session) {
    if (session.isLoggedIn) {
      return [
        const BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
        if (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS)
          const BottomNavigationBarItem(icon: Icon(Icons.qr_code_scanner), label: 'Scanner')
        else
          const BottomNavigationBarItem(icon: Icon(Icons.keyboard), label: 'Inserisci Token'),
        const BottomNavigationBarItem(icon: Icon(Icons.logout), label: 'Logout'),
      ];
    } else {
      return const [
        BottomNavigationBarItem(icon: Icon(Icons.app_registration), label: 'Registrazione'),
        BottomNavigationBarItem(icon: Icon(Icons.devices), label: 'Associa Dispositivo'),
      ];
    }
  }

  void _showSnack(BuildContext context, String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message), duration: const Duration(seconds: 2)));
  }

  @override
  Widget build(BuildContext context) {
    final session = Provider.of<SessionManager>(context);

    if (!_isInitialized) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_authService == null) {
      // Server non disponibile → schermata di errore con retry
      return Scaffold(
        appBar: AppBar(
          actions: [
            IconButton(
              icon: const Icon(Icons.settings),
              onPressed: () async {
                final result = await Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => SettingsPage(initialIp: _serverIp, initialPort: _serverPort),
                  ),
                );
                if (result != null && result is Map<String, dynamic>) {
                  final newIp = result['ip'] as String;
                  final newPort = result['port'] as int;
                  if (newIp != _serverIp || newPort != _serverPort) {
                    _restartSocket(newIp, newPort);
                  }
                }
              },
            ),
          ],
        ),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
                const Text(
                "Impossibile collegarsi al server",
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
                ),
              const SizedBox(height: 16),
              SizedBox(
                width: 400,
                child: ActionButton(
                  label: 'RIPROVA',
                  color: Theme.of(context).colorScheme.primary,
                  textColor: Theme.of(context).colorScheme.onPrimary,
                  onPressed: () {
                    setState(() => _isInitialized = false);
                    _initSocket();
                  },
                ),
              ),
            ],
          ),
        ),
      );
    }

    final pages = _buildPages(session);
    final navItems = _buildNavItems(session);

    return Scaffold(
      appBar: AppBar(
        actions: [
          if (!session.isLoggedIn)
            IconButton(
              icon: const Icon(Icons.settings),
              onPressed: () async {
                final result = await Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => SettingsPage(initialIp: _serverIp, initialPort: _serverPort),
                  ),
                );
                if (result != null && result is Map<String, dynamic>) {
                  final newIp = result['ip'] as String;
                  final newPort = result['port'] as int;
                  if (newIp != _serverIp || newPort != _serverPort) {
                    _restartSocket(newIp, newPort);
                  }
                }
              },
            ),
        ],
      ),
      body: IndexedStack(index: _selectedIndex, children: pages),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        items: navItems,
        onTap: (index) async {
          if (session.isLoggedIn && index == 2) {
            await _handleLogout(session);
          } else if (!session.isLoggedIn && index == 1) {
            setState(() => _selectedIndex = index);
            await _handleAssoc(session);
          } else {
            setState(() => _selectedIndex = index);
          }
        },
      ),
    );
  }
}
