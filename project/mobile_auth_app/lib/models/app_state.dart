import 'package:flutter/foundation.dart';

class MyAppState extends ChangeNotifier {
  String? _username;
  bool _isLoggedIn = false;

  String? get username => _username;
  bool get isLoggedIn => _isLoggedIn;

  // Metodo per fare il login
  void login(String username) {
    _username = username;
    _isLoggedIn = true;
    notifyListeners();
  }

  // Metodo per fare logout
  void logout() {
    _username = null;
    _isLoggedIn = false;
    notifyListeners();
  }

  // Puoi aggiungere altri metodi e proprietà per gestire lo stato globale
}
