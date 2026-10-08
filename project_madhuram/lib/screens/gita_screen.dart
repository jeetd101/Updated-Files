import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../utils/app_theme.dart';

class GitaScreen extends StatelessWidget {
  const GitaScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final appProvider = Provider.of<AppProvider>(context);
    final verses = appProvider.filteredGitaVerses;

    return Scaffold(
      appBar: AppBar(title: const Text('Bhagavad Gita Upadesh')),
      body: Column(
        children: [
          // Live Search Bar
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              onChanged: (val) => appProvider.setGitaSearchQuery(val),
              decoration: InputDecoration(
                hintText: 'Search verse or keyword...',
                prefixIcon: const Icon(Icons.search, color: AppTheme.accentGold),
                filled: true,
                fillColor: Colors.white,
                contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(30),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),

          // Verse Cards List
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: verses.length,
              itemBuilder: (context, index) {
                final v = verses[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'Chapter ${v.chapter}, Verse ${v.verse}',
                              style: const TextStyle(color: AppTheme.accentGold, fontWeight: FontWeight.bold),
                            ),
                            IconButton(
                              icon: Icon(
                                v.isBookmarked ? Icons.bookmark : Icons.bookmark_border,
                                color: v.isBookmarked ? AppTheme.accentGold : Colors.grey,
                              ),
                              onPressed: () => appProvider.toggleGitaBookmark(v.chapter, v.verse),
                            ),
                          ],
                        ),
                        Text(
                          v.sanskrit,
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, height: 1.4),
                        ),
                        const Divider(height: 20),
                        Text(
                          v.translation,
                          style: const TextStyle(fontSize: 13, color: Colors.black87, fontWeight: FontWeight.w500),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          v.explanation,
                          style: const TextStyle(fontSize: 12, color: Colors.grey, fontStyle: FontStyle.italic),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}