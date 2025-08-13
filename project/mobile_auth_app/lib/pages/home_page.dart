import 'package:flutter/material.dart';
import 'req_assoc.dart';       // Assumi che esista questa pagina
import 'registration_page.dart'; // Assumi che esista questa pagina
import 'qr_scanner_page.dart';

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int selectedIndex = 0;

  static final List<Widget> pages = [
    const ReqAssoc(),
    const RegistrationPage(),
    const QrCodeScannerPage(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: pages[selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: selectedIndex,
        onTap: (index) => setState(() => selectedIndex = index),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.devices), label: 'Associa Dispositivo'),
          BottomNavigationBarItem(icon: Icon(Icons.app_registration), label: 'Registrazione'),
          BottomNavigationBarItem(icon: Icon(Icons.qr_code_scanner), label: 'Scanner'),
        ],
      ),
    );
  }
}
