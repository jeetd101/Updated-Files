import 'package:flutter/material.dart';
import '../core/app_styles.dart';

class TopicCard extends StatelessWidget {
  final String title;
  final VoidCallback onTap;

  const TopicCard({
    Key? key,
    required this.title,
    required this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.tileBackground,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            spreadRadius: 1,
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        title: Text(title, style: AppStyles.titleText),
        trailing: const Icon(Icons.arrow_forward_ios, color: Colors.grey, size: 20),
        onTap: onTap,
      ),
    );
  }
}