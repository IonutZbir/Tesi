import 'package:flutter/material.dart';
import 'pages/home_page.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    const primary = Color(0xFF153146);
    final colorScheme =
        ColorScheme.fromSeed(seedColor: primary).copyWith(primary: primary);

    return MaterialApp(
      title: 'Schnorr Auth App',
      theme: ThemeData(
        colorScheme: colorScheme,
        useMaterial3: true,
      ),
      home: const MyHomePage(),
    );
  }
}
