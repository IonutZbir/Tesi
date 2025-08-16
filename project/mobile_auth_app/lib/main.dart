import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'models/session_manager.dart';
import 'app.dart';

void main() {
  runApp(ChangeNotifierProvider(create: (_) => SessionManager(), child: MyApp()));
}
