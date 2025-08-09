import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'models/app_state.dart';
import 'app.dart';

void main() {
  runApp(ChangeNotifierProvider(create: (context) => MyAppState(), child: const MyApp()));
}
