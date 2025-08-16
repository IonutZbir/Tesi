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

class AuthService {
  final SocketService _socketService;

  BigInt? p;
  BigInt? g;
  BigInt? q;

  AuthService(this._socketService);

  /// Handshake iniziale con il server
  Future<bool> handshake() async {
    // 1. Mando richiesta handshake
    _socketService.send(MessageType.handshakeReq);

    print("[CLIENT] Richiesta di handshake inviata al server...");

    // 2. Aspetto la risposta del server
    final response = await _socketService.receiveOnce();
    if (response == null) {
      print("[CLIENT] Nessuna risposta dal server.");
      return false;
    }

    print("[CLIENT] Fase di handshake... risposta ricevuta: $response");

    // 3. Verifico che la risposta sia di tipo GROUP_SELECTION
    if (response["type_code"] == MessageType.groupSelection.code) {
      final group = response["group_id"];
      print("[CLIENT] Gruppo selezionato dal server: $group");

      if (!groups.containsKey(group)) {
        print("[CLIENT] Gruppo crittografico non supportato.");
        return false;
      }

      // prendi direttamente i parametri come BigInt
      p = groups[group]!["p"]!;
      g = groups[group]!["g"]!;
      q = (p! - BigInt.one) ~/ BigInt.two;

      // invio HANDSHAKE_RES
      _socketService.send(MessageType.handshakeRes);

      return true;
    }

    return false;
  }

  /// Registrazione dell'utente
  Future<bool> register(String username, BuildContext context) async {
    if (p == null || g == null || q == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text("Parametri crittografici non inizializzati")));
      return false;
    }

    try {
      // Genera alpha casuale
      final alpha = randomBigInt(q!);

      // Nome del dispositivo
      final deviceName = await getDeviceName();

      // Calcola chiave pubblica
      final publicKey = g!.modPow(alpha, p!).toRadixString(16);

      // Prepara il messaggio
      final payload = {"username": username, "public_key": publicKey, "device": deviceName};

      // Invia al server
      _socketService.send(MessageType.register, extraData: payload);

      // Attende la risposta
      final response = await waitForResponse({MessageType.registered.code});

      print("[SOCKET] $response");

      if (response == null) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar
          ..showSnackBar(
            const SnackBar(content: Text("Nessuna risposta dal server"), duration: const Duration(seconds: 2)),
          );
        return false;
      }

      if (response.containsKey("error")) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SnackBar(content: Text(response["error"] ?? "Errore sconosciuto"), duration: const Duration(seconds: 2)),
          );

        return false;
      }

      // Registrazione riuscita

      KeyManager.savePrivateKey(username, alpha);

      return true;
    } catch (e) {
      rethrow;
    }
  }

  /// Autenticazione dell'utente
  Future<bool> authenticate(String username, BuildContext context) async {
    // Carica la chiave privata salvata
    final alpha = await KeyManager.loadPrivateKey(username);
    if (alpha == null) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar
        ..showSnackBar(
          const SnackBar(
            content: Text("Chiave privata non trovata. Registrati prima!"),
            duration: const Duration(seconds: 2),
          ),
        );
      return false;
    }

    // Genera alpha temporaneo casuale
    final alphaT = randomBigInt(q!);

    // Calcola u_t = g^alphaT mod p
    final uT = g!.modPow(alphaT, p!);

    // Invia AUTH_REQUEST al server
    _socketService.send(MessageType.authRequest, extraData: {"username": username, "temp": uT.toRadixString(16)});

    // Attende la challenge dal server
    final challengeMsg = await waitForResponse({MessageType.challenge.code});
    if (challengeMsg == null) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(content: Text("Nessuna challenge ricevuta dal server."), duration: const Duration(seconds: 2)),
        );
      return false;
    }

    final hexStr = challengeMsg["challenge"].trim().substring(2);
    final c = BigInt.parse(hexStr, radix: 16);

    // Calcola la risposta alphaZ = (alphaT + alpha * c) % q
    final alphaZ = (alphaT + alpha * c) % q!;

    // Invia AUTH_RESPONSE al server
    _socketService.send(MessageType.authResponse, extraData: {"response": alphaZ.toRadixString(16)});

    // Attende accettazione o rifiuto
    final finalResponse = await waitForResponse({MessageType.accepted.code, MessageType.rejected.code});

    if (finalResponse == null) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(content: Text("Nessuna risposta finale dal server."), duration: const Duration(seconds: 2)),
        );
      return false;
    }

    if (finalResponse["type_code"] == MessageType.accepted.code) {
      return true;
    } else if (finalResponse["type_code"] == MessageType.rejected.code) {
      return false;
    }

    return false;
  }

  /// Associazione del dispositivo
  Future<bool> assoc(BuildContext context) async {
    if (p == null || g == null || q == null) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(content: Text("Parametri crittografici non inizializzati"), duration: Duration(seconds: 2)),
        );
      return false;
    }

    final deviceName = await getDeviceName();

    // Genera alpha casuale
    final alpha = randomBigInt(q!);

    // Calcola la chiave pubblica: g^alpha mod p
    final publicKey = g!.modPow(alpha, p!);

    // Invia richiesta di associazione
    final payload = {"device": deviceName, "pk": publicKey.toRadixString(16)};
    _socketService.send(MessageType.assocRequest, extraData: payload);

    // Primo step: attendere il token da mostrare come QR
    final tokenResponse = await waitForResponse({MessageType.tokenAssoc.code, MessageType.error.code});
    if (tokenResponse == null) return false;

    if (tokenResponse['type_code'] == MessageType.tokenAssoc.code) {
      final token = tokenResponse['token'];

      Provider.of<SessionManager>(context, listen: false).token = token;

      print("[CLIENT] Token ricevuto: $token");
    }

    // Secondo step: attendere conferma di associazione
    final confirmResponse = await waitForResponse({MessageType.accepted.code, MessageType.error.code});
    if (confirmResponse == null) return false;

    if (confirmResponse['type_code'] == MessageType.accepted.code) {
      final username = confirmResponse['username'];

      // TODO: messaggi nella snack bar
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text("Associazione completata, benvenuto $username!"),
            duration: const Duration(seconds: 2),
          ),
        );

      Provider.of<SessionManager>(context, listen: false).login(username);

      print("[CLIENT] Associazione completata, login effettuato!");
      print("[CLIENT] Benvenuto $username!");
      await KeyManager.savePrivateKey(username, alpha);
      return true;
    }

    // se riceve errore o risposta inattesa
    return false;
  }

  /// Recupera i dispositivi associati ad un username dal server
  Future<List<DeviceInfo>?> fetchAssociatedDevices(String username) async {
    // Invia la richiesta al server
    _socketService.send(MessageType.devicesRequest, extraData: {"username": username});

    // Attende la risposta
    final response = await waitForResponse({MessageType.devicesResponse.code});

    if (response == null || response.containsKey("error")) {
      print("[CLIENT] Errore nel recupero dei dispositivi: ${response?["error"]}");
      return null;
    }

    if (response["type_code"] == MessageType.devicesResponse.code) {
      final devices = response["devices"];
      if (devices is List) {
        try {
          // Converto ogni elemento della lista in DeviceInfo
          return devices.map((d) {
            return DeviceInfo(
              deviceName: d["device_name"] ?? "Sconosciuto",
              mainDevice: d["main_device"] ?? "",
              isLoggedIn: d["logged"] ?? "",
            );
          }).toList();
        } catch (e) {
          print("[CLIENT] Errore parsing devices: $e");
          return null;
        }
      }
    }

    return null;
  }

  /// Attende un messaggio con type_code atteso, oppure gestisce ERROR
  Future<Map<String, dynamic>?> waitForResponse(Set<int> expectedTypes) async {
    while (true) {
      final msg = await _socketService.receiveOnce();
      if (msg == null) {
        return {"error": "Connessione chiusa o messaggio vuoto"};
      }

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
