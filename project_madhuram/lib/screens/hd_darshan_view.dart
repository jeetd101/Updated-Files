import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../data/app_data.dart';

class HDDarshanViewScreen extends StatelessWidget {
  final TempleDarshan temple;
  const HDDarshanViewScreen({super.key, required this.temple});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text(temple.title, style: const TextStyle(color: Colors.amber)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: Column(
        children: [
          Expanded(
            child: InteractiveViewer(
              minScale: 0.5,
              maxScale: 4.0,
              child: Center(
                child: CachedNetworkImage(
                  imageUrl: temple.imageUrl,
                  placeholder: (context, url) => const CircularProgressIndicator(color: Colors.amber),
                  errorWidget: (context, url, error) => const Icon(Icons.error, color: Colors.white),
                  fit: BoxFit.contain,
                ),
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            color: const Color(0xFF0F172A),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(temple.location, style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(temple.description, style: const TextStyle(color: Colors.white70, fontSize: 13)),
                const SizedBox(height: 8),
                Text('🕒 Aarti Timings: ${temple.aartiTiming}', style: const TextStyle(color: Colors.amberAccent, fontSize: 12)),
              ],
            ),
          )
        ],
      ),
    );
  }
}