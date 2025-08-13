import 'package:flutter/material.dart';

Widget buildTitle(BuildContext context) {
  final theme = Theme.of(context);
  final base = theme.textTheme.headlineMedium ?? const TextStyle();
  final width = MediaQuery.sizeOf(context).width;
  final fontSize = (width / 10).clamp(24.0, 48.0);

  return Text(
    'Schnorr Auth App',
    textAlign: TextAlign.center,
    maxLines: 1,
    overflow: TextOverflow.ellipsis,
    style: base.copyWith(
      fontWeight: FontWeight.bold,
      fontSize: fontSize,
      color: theme.colorScheme.primary,
    ),
  );
}
