import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryNavy = Color(0xFF0F172A);
  static const Color accentGold = Color(0xFFD97706);
  static const Color bgLight = Color(0xFFF8FAFC);

  // Missing color aliases referenced in audio_screen, gita_screen, and mini_player
  static const Color royalBlue = Color(0xFF0F172A);
  static const Color cardBg = Color(0xFF1E293B);
  static const Color gold = accentGold;
  static const Color textMuted = Colors.white70;

  static ThemeData get themeData {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: bgLight,
      colorScheme: ColorScheme.fromSeed(
        seedColor: accentGold,
        primary: primaryNavy,
        secondary: accentGold,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: primaryNavy,
        foregroundColor: accentGold,
        elevation: 0,
      ),
    );
  }
}