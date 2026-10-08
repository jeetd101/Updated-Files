import 'hd_darshan_view.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../providers/audio_provider.dart';
import '../utils/app_theme.dart';
import '../widgets/darshan_lightbox.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../data/app_data.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final appProvider = Provider.of<AppProvider>(context);
    final audioProvider = Provider.of<AudioProvider>(context);
    final todayDarshan = appProvider.darshans.first;
    final dailyVerse = appProvider.filteredGitaVerses.first;

    return Scaffold(
      appBar: AppBar(
        title: const Text('MADHURAM', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_active_outlined, color: AppTheme.accentGold),
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => AlertDialog(
                  backgroundColor: AppTheme.cardBg,
                  title: const Text('Daily Devotional Updates', style: TextStyle(color: AppTheme.accentGold)),
                  content: const Text(
                    '• Morning Aarti Darshan available now.\n• Daily Gita Wisdom updated.\n• Evening Satsang Stream scheduled at 7:00 PM.',
                    style: TextStyle(color: Colors.white70, height: 1.5),
                  ),
                  actions: [
                    TextButton(
                      child: const Text('OK', style: TextStyle(color: AppTheme.accentGold)),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Welcome Card
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppTheme.primaryNavy, AppTheme.cardBg],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.accentGold.withOpacity(0.3)),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Radhe Radhe 🙏', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                  SizedBox(height: 6),
                  Text('Begin your day with divine grace & spiritual reflection.', style: TextStyle(color: Colors.white70, fontSize: 13)),
                ],
              ),
            ),

            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Live Darshan Today', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy)),
                TextButton(
                  onPressed: () => appProvider.setNavIndex(1),
                  child: const Text('View All', style: TextStyle(color: AppTheme.accentGold, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Live Darshan Action Card
            GestureDetector(
              onTap: () {
                final vrindavanTemple = AppData.temples.firstWhere((t) => t.id == '5');
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => HDDarshanViewScreen(temple: vrindavanTemple),
                  ),
                );
              },
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Stack(
                  children: [
                    CachedNetworkImage(
                      imageUrl: AppData.temples.firstWhere((t) => t.id == '5').imageUrl,
                      height: 200,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      placeholder: (context, url) => Container(
                        height: 200,
                        color: Colors.grey[800],
                      ),
                      errorWidget: (context, url, error) => const Icon(Icons.error),
                    ),
                    Positioned(
                      bottom: 0,
                      left: 0,
                      right: 0,
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        color: Colors.black.withOpacity(0.6),
                        child: const Text(
                          'Live Darshan Today - Bankey Bihari Ji',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Featured Chants & Music', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy)),
                TextButton(
                  onPressed: () => appProvider.setNavIndex(2),
                  child: const Text('Playlist', style: TextStyle(color: AppTheme.accentGold, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Quick Play Card
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              color: AppTheme.cardBg,
              child: ListTile(
                leading: const CircleAvatar(
                  backgroundColor: AppTheme.accentGold,
                  child: Icon(Icons.play_arrow, color: Colors.white),
                ),
                title: Text(audioProvider.tracks.first.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                subtitle: Text(audioProvider.tracks.first.artist, style: const TextStyle(color: Colors.white70, fontSize: 12)),
                trailing: const Icon(Icons.equalizer, color: AppTheme.accentGold),
                onTap: () {
                  audioProvider.playTrack(audioProvider.tracks.first);
                },
              ),
            ),

            const SizedBox(height: 24),
            const Text('Gita Wisdom of the Day', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy)),
            const SizedBox(height: 10),

            // Gita Verse Card
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Chapter ${dailyVerse.chapter}, Verse ${dailyVerse.verse}', style: const TextStyle(color: AppTheme.accentGold, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Text(dailyVerse.sanskrit, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, height: 1.4)),
                    const SizedBox(height: 10),
                    Text(dailyVerse.translation, style: const TextStyle(fontSize: 13, color: Colors.black87)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}