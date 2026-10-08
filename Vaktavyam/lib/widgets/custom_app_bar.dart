import 'package:flutter/material.dart';
import '../core/app_styles.dart';

class CustomAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final bool showBackButton;
  final List<Widget>? actions;
  final Color? backgroundColor;
  final Color? textColor;

  const CustomAppBar({
    Key? key,
    required this.title,
    this.showBackButton = true,
    this.actions,
    this.backgroundColor,
    this.textColor,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final effectiveBgColor = backgroundColor ?? AppColors.primaryRed;
    final effectiveTextColor = textColor ?? Colors.white;

    return Container(
      color: effectiveBgColor,
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                if (showBackButton)
                  IconButton(
                    icon: Icon(Icons.arrow_back_ios, color: effectiveTextColor),
                    onPressed: () => Navigator.of(context).pop(),
                  )
                else
                  const SizedBox(width: 16),

                Text(
                  title,
                  style: AppStyles.header2.copyWith(color: effectiveTextColor),
                ),

                const Spacer(),

                if (actions != null) ...actions!,
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(60);
}