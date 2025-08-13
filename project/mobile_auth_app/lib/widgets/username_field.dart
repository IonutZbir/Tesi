import 'package:flutter/material.dart';

Widget buildUsernameField(usernameController) {
    return TextField(
      controller: usernameController,
      decoration: const InputDecoration(
        labelText: 'Username',
        border: OutlineInputBorder(),
      ),
    );
  }