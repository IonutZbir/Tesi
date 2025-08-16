import 'dart:io';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';

class KeyManager {
  /// Restituisce la directory dove salvare le chiavi (multipiattaforma)
  static Future<Directory> _getSchnorrDir() async {
    Directory baseDir;

    if (Platform.isAndroid || Platform.isIOS) {
      // Directory interna dell’app
      baseDir = await getApplicationDocumentsDirectory();
    } else if (Platform.isLinux || Platform.isMacOS) {
      // Usa la cartella .config nella home
      final home = Directory(Platform.environment['HOME'] ?? '');
      baseDir = Directory(path.join(home.path, '.config'));
    } else if (Platform.isWindows) {
      // Usa APPDATA su Windows
      final appData = Directory(Platform.environment['APPDATA'] ?? '');
      baseDir = appData;
    } else {
      throw UnsupportedError('Sistema non supportato');
    }

    final schnorrDir = Directory(path.join(baseDir.path, 'schnorr'));
    if (!await schnorrDir.exists()) {
      await schnorrDir.create(recursive: true);
    }

    return schnorrDir;
  }

  /// Salva la chiave privata
  static Future<void> savePrivateKey(String username, BigInt key) async {
    final dir = await _getSchnorrDir();
    final file = File(path.join(dir.path, '${username}_privkey.txt'));
    await file.writeAsString(key.toString());
    print('[KEY] Chiave privata salvata in ${file.path}');
  }

  /// Carica la chiave privata
  static Future<BigInt?> loadPrivateKey(String username) async {
    final dir = await _getSchnorrDir();
    final file = File(path.join(dir.path, '${username}_privkey.txt'));
    if (await file.exists()) {
      final content = (await file.readAsString()).trim();
      return BigInt.parse(content);
    } else {
      print('[KEY] Chiave privata non trovata per $username');
      return null;
    }
  }
}
