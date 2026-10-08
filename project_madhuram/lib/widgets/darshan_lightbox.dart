import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/models.dart';
import '../utils/app_theme.dart';

class DarshanLightbox extends StatelessWidget {
  final DarshanItem darshan;

  const DarshanLightbox({super.key, required this.darshan});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text(darshan.templeName, style: const TextStyle(color: AppTheme.gold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.download, color: AppTheme.gold),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Downloading HD Wallpaper...')),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.share, color: AppTheme.gold),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Sharing Darshan link...')),
              );
            },
          ),
        ],
      ),
      body: Center(
        child: InteractiveViewer(
          minScale: 0.5,
          maxScale: 4.0,
          child: CachedNetworkImage(
            imageUrl: darshan.imageUrl,
            fit: BoxFit.contain,
            placeholder: (context, url) => const CircularProgressIndicator(color: AppTheme.gold),
            errorWidget: (context, url, error) => const Icon(Icons.error, color: Colors.red),
          ),
        ),
      ),
    );
  }
}