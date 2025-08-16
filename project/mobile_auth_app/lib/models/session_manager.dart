import 'package:flutter/material.dart';

class SessionManager extends ChangeNotifier {
  String? _username;
  bool get isLoggedIn => _username != null;
  String? get username => _username;
  String? _token;
  String? get token => _token;
  
  set token(String? value) {
    _token = value;
    notifyListeners();
  }

  void login(String username) {
    _username = username;
    notifyListeners(); // notifica le UI che lo stato è cambiato
  }

  void logout() {
    _username = null;
    notifyListeners();
  }

}
