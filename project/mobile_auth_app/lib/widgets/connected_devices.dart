import 'package:flutter/material.dart';

class DeviceInfo {
  final String deviceName;
  final bool mainDevice;
  final bool isLoggedIn;

  DeviceInfo({
    required this.deviceName,
    required this.mainDevice,
    required this.isLoggedIn,
  });
}

class DevicesListWidget extends StatelessWidget {
  final String? username;
  final List<DeviceInfo> devices;

  const DevicesListWidget({
    required this.username,
    required this.devices,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SafeArea(
      child: Scaffold(
        appBar: AppBar(
          title: Text("Dispositivi di ${username ?? ''}"),
          backgroundColor: theme.colorScheme.primary,
          foregroundColor: theme.colorScheme.onPrimary,
        ),
        body: devices.isEmpty
            ? const Center(
                child: Text(
                  "Nessun dispositivo associato",
                  style: TextStyle(fontSize: 16),
                ),
              )
            : ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: devices.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final device = devices[index];
                  return Card(
                    elevation: 3,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ListTile(
                      leading: const Icon(Icons.devices, size: 30),
                      title: Text(
                        device.deviceName,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("Loggato?: ${device.isLoggedIn ? 'Sì' : 'No'}"),
                          if (device.mainDevice)
                            const Text(
                              "Dispositivo principale",
                              style: TextStyle(
                                fontStyle: FontStyle.italic,
                                color: Colors.green,
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
