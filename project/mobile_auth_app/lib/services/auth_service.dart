import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:schnorr_auth_app/models/errorType.dart';
import 'package:schnorr_auth_app/models/groups.dart';
import 'package:schnorr_auth_app/models/messageType.dart';
import 'package:schnorr_auth_app/models/session_manager.dart';
import 'package:schnorr_auth_app/services/socket_service.dart';
import 'package:schnorr_auth_app/utils/key_manager.dart';
import 'package:schnorr_auth_app/utils/utils.dart';
import 'package:schnorr_auth_app/widgets/connected_devices.dart';

/// Risultato di un’operazione di autenticazione/registrazione
class AuthResult {
  final bool success;
  final String? message;

  AuthResult.success() : success = true, message = null;
  AuthResult.failure(this.message) : success = false;
}

class AuthService {
  final SocketService _socketService;

  BigInt? p, g, q;

  AuthService(this._socketService);

  // --- HANDSHAKE ---
  Future<AuthResult> handshake() async {
    _socketService.send(MessageType.handshakeReq);
    final response = await _socketService.receiveOnce();

    if (response == null) {
      return AuthResult.failure("Nessuna risposta dal server");
    }

    if (response["type_code"] != MessageType.groupSelection.code) {
      return AuthResult.failure("Handshake fallito: risposta inattesa");
    }

    final group = response["group_id"];
    if (!groups.containsKey(group)) {
      return AuthResult.failure("Gruppo crittografico non supportato");
    }

    p = groups[group]!["p"]!;
    g = groups[group]!["g"]!;
    q = (p! - BigInt.one) ~/ BigInt.two;

    _socketService.send(MessageType.handshakeRes);
    return AuthResult.success();
  }

  // --- REGISTRAZIONE ---
  Future<AuthResult> register(String username) async {
    if (!_checkParams()) {
      return AuthResult.failure("Parametri crittografici non inizializzati");
    }

    try {
      final alpha = randomBigInt(q!);
      final deviceName = await getDeviceName();
      final publicKey = g!.modPow(alpha, p!).toRadixString(16);

      final payload = {"username": username, "public_key": publicKey, "device": deviceName};
      _socketService.send(MessageType.register, extraData: payload);

      final response = await waitForResponse({MessageType.registered.code});
      if (response == null || response.containsKey("error")) {
        return AuthResult.failure(response?["error"] ?? "Registrazione fallita");
      }

      await KeyManager.savePrivateKey(username, alpha);
      return AuthResult.success();
    } catch (e) {
      return AuthResult.failure("Errore durante la registrazione: $e");
    }
  }

  // --- AUTENTICAZIONE ---
  Future<AuthResult> authenticate(String username) async {
    final alpha = await KeyManager.loadPrivateKey(username);
    if (alpha == null) {
      return AuthResult.failure("Chiave privata non trovata. Registrati prima!");
    }

    final alphaT = randomBigInt(q!);
    final uT = g!.modPow(alphaT, p!);

    _socketService.send(MessageType.authRequest, extraData: {
      "username": username,
      "temp": uT.toRadixString(16),
    });

    final challengeMsg = await waitForResponse({MessageType.challenge.code, MessageType.error.code});
    if (challengeMsg == null || challengeMsg["type_code"] == MessageType.error.code) {
      return AuthResult.failure(challengeMsg?["error"] ?? "Errore dal server");
    }

    final challengeHex = challengeMsg["challenge"];
    if (challengeHex == null) return AuthResult.failure("Challenge mancante");

    final hexStr = challengeHex.toString().trim().substring(2);
    final c = BigInt.parse(hexStr, radix: 16);

    final alphaZ = (alphaT + alpha * c) % q!;
    _socketService.send(MessageType.authResponse, extraData: {"response": alphaZ.toRadixString(16)});

    final finalResponse = await waitForResponse({MessageType.accepted.code, MessageType.rejected.code});
    if (finalResponse == null) return AuthResult.failure("Nessuna risposta finale dal server");

    return finalResponse["type_code"] == MessageType.accepted.code
        ? AuthResult.success()
        : AuthResult.failure("Autenticazione rifiutata");
  }

  // --- ASSOCIAZIONE ---
  Future<AuthResult> assoc(BuildContext context) async {
    if (!_checkParams()) {
      return AuthResult.failure("Parametri crittografici non inizializzati");
    }

    final deviceName = await getDeviceName();
    final alpha = randomBigInt(q!);
    final publicKey = g!.modPow(alpha, p!);

    _socketService.send(MessageType.assocRequest, extraData: {
      "device": deviceName,
      "pk": publicKey.toRadixString(16),
    });

    final tokenResponse = await waitForResponse({MessageType.tokenAssoc.code, MessageType.error.code});
    if (tokenResponse == null || tokenResponse["type_code"] != MessageType.tokenAssoc.code) {
      return AuthResult.failure("Errore durante l'associazione (token non ricevuto)");
    }

    Provider.of<SessionManager>(context, listen: false).token = tokenResponse['token'];

    final confirmResponse = await waitForResponse({MessageType.accepted.code, MessageType.error.code});
    if (confirmResponse == null || confirmResponse['type_code'] != MessageType.accepted.code) {
      return AuthResult.failure("Errore durante l'associazione (nessuna conferma)");
    }

    final username = confirmResponse['username'];
    Provider.of<SessionManager>(context, listen: false).login(username);

    await KeyManager.savePrivateKey(username, alpha);
    return AuthResult.success();
  }

  // --- CONFERMA ASSOCIAZIONE ---
  Future<AuthResult> confirmAssoc(String token) async {
    _socketService.send(MessageType.tokenAssoc, extraData: {"token": token});
    final response = await waitForResponse({MessageType.accepted.code, MessageType.error.code});

    if (response == null || response['type_code'] != MessageType.accepted.code) {
      return AuthResult.failure("Errore durante la conferma di associazione");
    }

    return AuthResult.success();
  }

  // --- DISPOSITIVI ASSOCIATI ---
  Future<List<DeviceInfo>?> fetchAssociatedDevices(String username) async {
    _socketService.send(MessageType.devicesRequest, extraData: {"username": username});
    final response = await waitForResponse({MessageType.devicesResponse.code});

    if (response == null || response.containsKey("error")) return null;

    final devices = response["devices"];
    if (devices is! List) return null;

    return devices.map((d) {
      return DeviceInfo(
        deviceName: d["device_name"] ?? "Sconosciuto",
        mainDevice: d["main_device"] ?? "",
        isLoggedIn: d["logged"] ?? "",
      );
    }).toList();
  }

  // --- HELPER ---
  bool _checkParams() => p != null && g != null && q != null;

  Future<Map<String, dynamic>?> waitForResponse(Set<int> expectedTypes) async {
    while (true) {
      final msg = await _socketService.receiveOnce();
      if (msg == null) return {"error": "Connessione chiusa o messaggio vuoto"};

      final typeCode = msg['type_code'];
      if (typeCode == null) continue;

      if (expectedTypes.contains(typeCode)) {
        return msg;
      } else if (typeCode == MessageType.error.code) {
        final errCode = msg['error_code'];
        final err = ErrorType.fromCode(errCode);
        return {"error": err?.message() ?? 'Errore sconosciuto dal server'};
      } else {
        print("[CLIENT] Messaggio inatteso: $msg");
      }
    }
  }
}
