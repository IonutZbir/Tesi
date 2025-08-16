// lib/utils/utils.dart
// Requires: device_info_plus: ^10.1.0 (or latest) in pubspec.yaml

import 'dart:io' show File, Platform, Process;
import 'dart:math';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

BigInt randomBigInt(BigInt max) {
  final random = Random.secure();
  BigInt result;
  do {
    // genera un BigInt casuale della stessa lunghezza di max
    final bytes = (max.bitLength + 7) >> 3;
    final randomBytes = List<int>.generate(bytes, (_) => random.nextInt(256));
    result = BigInt.parse(randomBytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join(), radix: 16);
  } while (result >= max || result == BigInt.zero);
  return result;
}

/// Returns a concise descriptor like: "HP Linux x86_64" or "Samsung Android arm64".
Future<String> getDeviceName() async {
  final deviceInfo = DeviceInfoPlugin();
  final name = await _detectDeviceName(deviceInfo);
  final os = _osLabel();
  final arch = await _detectArch(deviceInfo);
  return [name, os, arch].where((e) => e.trim().isNotEmpty).join(' ').trim();
}


String _osLabel() {
  if (kIsWeb) return 'Web';
  if (Platform.isAndroid) return 'Android';
  if (Platform.isIOS) return 'iOS';
  if (Platform.isLinux) return 'Linux';
  if (Platform.isMacOS) return 'macOS';
  if (Platform.isWindows) return 'Windows';
  if (Platform.isFuchsia) return 'Fuchsia';
  return Platform.operatingSystem;
}

Future<String> _detectDeviceName(DeviceInfoPlugin deviceInfo) async {
  try {
    if (kIsWeb) return 'Browser';
    if (Platform.isAndroid) {
      final info = await deviceInfo.androidInfo;
      final manu = (info.manufacturer ?? '').trim();
      final model = (info.model ?? '').trim();
      final name = [manu, model].where((e) => e.isNotEmpty).join(' ');
      return name.isNotEmpty ? name : 'Android';
    }
    if (Platform.isIOS) {
      final info = await deviceInfo.iosInfo;
      final name = (info.name ?? '').trim();
      final model = (info.model ?? '').trim();
      return name.isNotEmpty ? name : (model.isNotEmpty ? model : 'iPhone');
    }
    if (Platform.isWindows) {
      // Prefer hostname/computer name.
      final envName = (Platform.environment['COMPUTERNAME'] ?? '').trim();
      if (envName.isNotEmpty) return envName;
      final info = await deviceInfo.windowsInfo;
      final comp = (info.computerName ?? '').trim();
      return comp.isNotEmpty ? comp : 'Windows PC';
    }
    if (Platform.isMacOS) {
      // Try model; fallback to hostname.
      final info = await deviceInfo.macOsInfo;
      final model = (info.model ?? '').trim(); // e.g., "MacBookPro18,3"
      if (model.isNotEmpty) return model;
      final host = Platform.localHostname;
      return host.isNotEmpty ? host : 'Mac';
    }
    if (Platform.isLinux) {
      // Try DMI vendor/product (common on PCs); fallback to hostname.
      final vendor = await _readFirstLine('/sys/devices/virtual/dmi/id/sys_vendor');
      final product = await _readFirstLine('/sys/devices/virtual/dmi/id/product_name');
      final combined = [vendor, product].where((e) => e.isNotEmpty).join(' ').trim();
      if (combined.isNotEmpty) return combined;
      final host = Platform.localHostname;
      if (host.isNotEmpty) return host;
      final info = await deviceInfo.linuxInfo;
      final pretty = (info.prettyName ?? '').trim();
      return pretty.isNotEmpty ? pretty : 'Linux';
    }
  } catch (_) {
    // Ignore and fall through to default
  }
  return 'Device';
}

Future<String> _detectArch(DeviceInfoPlugin deviceInfo) async {
  try {
    if (kIsWeb) return 'web';
    if (Platform.isAndroid) {
      final info = await deviceInfo.androidInfo;
      final abi = (info.supportedAbis.isNotEmpty ? info.supportedAbis.first : '').trim();
      return _normalizeAbi(abi);
    }
    if (Platform.isIOS) {
      final info = await deviceInfo.iosInfo;
      final m = (info.utsname.machine ?? '').toLowerCase();
      if (m.contains('x86_64')) return 'x86_64'; // simulator (Intel)
      if (m.contains('arm64')) return 'arm64';   // device or Apple Silicon simulator
      return 'arm64'; // modern iOS devices
    }
    if (Platform.isWindows) {
      final arch = (Platform.environment['PROCESSOR_ARCHITEW6432'] ??
              Platform.environment['PROCESSOR_ARCHITECTURE'] ??
              '')
          .trim();
      return _normalizeWindowsArch(arch);
    }
    if (Platform.isLinux || Platform.isMacOS) {
      final uname = await _tryUnameM();
      if (uname != null && uname.isNotEmpty) return uname;
    }
  } catch (_) {
    // Ignore and fall through
  }
  return 'unknown';
}

String _normalizeAbi(String abi) {
  switch (abi) {
    case 'arm64-v8a':
      return 'arm64';
    case 'armeabi-v7a':
      return 'armv7';
    case 'armeabi':
      return 'arm';
    case 'x86_64':
      return 'x86_64';
    case 'x86':
      return 'x86';
    default:
      return abi.isEmpty ? 'unknown' : abi;
  }
}

String _normalizeWindowsArch(String arch) {
  final a = arch.toUpperCase();
  if (a.contains('ARM64')) return 'arm64';
  if (a.contains('AMD64') || a.contains('X64')) return 'x86_64';
  if (a.contains('X86')) return 'x86';
  return arch.isEmpty ? 'unknown' : arch;
}

Future<String> _readFirstLine(String path) async {
  try {
    final exists = await File(path).exists();
    if (!exists) return '';
    final lines = await File(path).readAsLines();
    if (lines.isEmpty) return '';
    return lines.first.trim();
  } catch (_) {
    return '';
  }
}

Future<String?> _tryUnameM() async {
  try {
    final res = await Process.run('uname', ['-m']);
    if (res.exitCode == 0) {
      final out = (res.stdout as String?)?.trim() ?? '';
      if (out.isNotEmpty) return out;
    }
  } catch (_) {
    // Process may be unavailable/sandboxed; ignore.
  }
  return null;
}