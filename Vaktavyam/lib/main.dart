import 'package:flutter/material.dart';
import 'package:vaktavyam/screens/topic_screen.dart';

void main() {
  runApp(const VaktavyamApp());
}

class VaktavyamApp extends StatelessWidget {
  const VaktavyamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Vaktavyam',
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFED3237),
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFED3237),
          primary: const Color(0xFFED3237),
        ),
        fontFamily: 'Roboto',
      ),
      home: TopicListScreen(), // Fixed: Changed Topic_Screen to TopicScreen (no underscore)
    );
  }
}