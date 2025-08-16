import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:schnorr_auth_app/models/session_manager.dart';
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
  late SocketService _socketService;
  late AuthService _authService;
  int selectedIndex = 0;
  List<DeviceInfo> _devices = [];
  bool _devicesLoading = false;

  @override
  void initState() {
    super.initState();

    _socketService = SocketService(
      host: "192.168.1.168",
      port: 65432,
      onConnect: () async {
        final ok = await _authService.handshake();
        if (!ok) {
          print("[CLIENT] Handshake fallito!");
        }
      },
      onMessage: (msg) {
        print("[SOCKET]: Messaggio ricevuto -> $msg");
      },
    );

    _authService = AuthService(_socketService);
    _socketService.connect();
  }

  @override
  void dispose() {
    _socketService.dispose();
    super.dispose();
  }

  Future<void> _fetchDevices(String username) async {
    final devices = await _authService.fetchAssociatedDevices(username);
    setState(() {
      _devices = devices ?? [];
      _devicesLoading = false;
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = Provider.of<SessionManager>(context, listen: false);
    if (session.isLoggedIn && !_devicesLoading) {
      _devicesLoading = true;
      _fetchDevices(session.username ?? "");
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = Provider.of<SessionManager>(context);

    final List<Widget> pages = session.isLoggedIn
        ? [
            DevicesListWidget(
              username: session.username ?? "",
              devices: _devices,
            ),
            QrCodeScannerPage(authService: _authService),
          ]
        : [
            RegistrationPage(authService: _authService),
            ReqAssoc(authService: _authService),
          ];

    final List<BottomNavigationBarItem> navItems = session.isLoggedIn
        ? [
            const BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
            const BottomNavigationBarItem(icon: Icon(Icons.qr_code_scanner), label: 'Scanner'),
            const BottomNavigationBarItem(icon: Icon(Icons.logout), label: 'Logout'),
          ]
        : [
            const BottomNavigationBarItem(icon: Icon(Icons.app_registration), label: 'Registrazione'),
            const BottomNavigationBarItem(icon: Icon(Icons.devices), label: 'Associa Dispositivo'),
          ];

    return Scaffold(
      body: pages[selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: selectedIndex,
        onTap: (index) async {
          if (session.isLoggedIn && index == 2) {
            // Logout
            session.logout();
            setState(() => selectedIndex = 0); // Torna alla prima pagina non loggato
            return;
          }

          setState(() => selectedIndex = index);

          // Se utente non loggato e clicca "Associa", chiama assoc
          if (!session.isLoggedIn && index == 1) {
            final success = await _authService.assoc(context);
            if (success) {
              setState(() => selectedIndex = 0);
            }
          }
        },
        items: navItems,
      ),
    );
  }
}
