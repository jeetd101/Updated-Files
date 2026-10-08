import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/audio_provider.dart';
import '../utils/app_theme.dart';

class MiniPlayer extends StatelessWidget {
  const MiniPlayer({super.key});

  @override
  Widget build(BuildContext context) {
    final audioProvider = Provider.of<AudioProvider>(context);
    final currentTrack = audioProvider.currentTrack;

    if (currentTrack == null) return const SizedBox.shrink();

    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.royalBlue,
        boxShadow: [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 8,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Linear Playback Progress Line
          LinearProgressIndicator(
            value: audioProvider.playbackPosition,
            backgroundColor: Colors.white10,
            valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.accentGold),
            minHeight: 2.5,
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.accentGold.withOpacity(0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.music_note, color: AppTheme.accentGold, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        currentTrack.title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        '${currentTrack.artist} • ${currentTrack.category}',
                        style: const TextStyle(color: Colors.white70, fontSize: 11),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.skip_previous_rounded, color: Colors.white70, size: 26),
                  onPressed: () => audioProvider.playPreviousTrack(),
                ),
                IconButton(
                  icon: Icon(
                    audioProvider.isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill,
                    color: AppTheme.accentGold,
                    size: 36,
                  ),
                  onPressed: () => audioProvider.togglePlay(),
                ),
                IconButton(
                  icon: const Icon(Icons.skip_next_rounded, color: Colors.white70, size: 26),
                  onPressed: () => audioProvider.playNextTrack(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}