import 'package:flutter/material.dart';

class AppColors {
  static const Color primaryRed = Color(0xFFEF4444);
  static const Color backgroundLight = Color(0xFFFAF8F5);
  static const Color accentGold = Color(0xFFE9C46A);
  static const Color tileBackground = Colors.white;
  static const Color textDark = Color(0xFF1F2937);
  static const Color textLight = Color(0xFF6B7280);
  static const Color primaryButton = Color(0xFFE2C075);
  static const Color buttonText = Color(0xFF1C1B1F);
}

class AppStyles {
  static const TextStyle header1 = TextStyle(
    fontSize: 22,
    fontWeight: FontWeight.bold,
    color: Colors.white,
  );
  static const TextStyle header2 = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    color: AppColors.textDark,
  );
  static const TextStyle titleText = TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.w500,
    color: AppColors.textDark,
  );
  static const TextStyle bodyText = TextStyle(
    fontSize: 16,
    color: AppColors.textLight,
    height: 1.5,
  );
  static const TextStyle buttonText = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: AppColors.textDark,
  );
}