import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/audio_provider.dart';
import '../utils/app_theme.dart';

class AudioScreen extends StatelessWidget {
  const AudioScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final audioProvider = Provider.of<AudioProvider>(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Devotional Audio Library')),
      body: ListView.separated(
        padding: const EdgeInsets.all(12),
        itemCount: audioProvider.tracks.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final track = audioProvider.tracks[index];
          final isSelected = audioProvider.currentTrack?.id == track.id;

          return Container(
            color: isSelected ? AppTheme.accentGold.withOpacity(0.08) : Colors.transparent,
            child: ListTile(
              title: Text(
                track.title,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              subtitle: Text(
                '${track.artist} • ${track.category}',
                style: const TextStyle(fontSize: 12),
              ),
              trailing: Icon(
                isSelected && audioProvider.isPlaying
                    ? Icons.pause_circle_filled
                    : Icons.play_circle_fill,
                color: Colors.orange,
              ),
              onTap: () {
                if (isSelected) {
                  audioProvider.togglePlay();
                } else {
                  audioProvider.playTrack(track);
                }
              },
            )
          );
        },
      ),
    );
  }
}