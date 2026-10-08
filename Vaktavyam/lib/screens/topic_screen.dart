import 'package:flutter/material.dart';
import 'chapter_list_screen.dart';
import 'search_screen.dart';
import 'upload_screen.dart';
import '../core/last_seen_service.dart';
import 'package:vaktavyam/screens/upload_screen.dart';
// Adjust the path above if your file is located in a different folder

class TopicListScreen extends StatelessWidget {
  const TopicListScreen({super.key});

  final List<String> topics = const [
    '૧. કામ',
    '૨. ક્રોધ',
    '૩. લોભ',
    '૪. મોહ',
    '૫. મદ',
    '૬. મત્સર'
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFED3237),
      appBar: AppBar(
        backgroundColor: const Color(0xFFED3237),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
          onPressed: () {},
        ),
        title: const Text(
          'Vaktyavyam',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 20),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search, color: Colors.white),
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => const SearchScreen()));
            },
          ),
          IconButton(
            icon: const Icon(Icons.menu_book, color: Colors.white),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ChapterListScreen(
                    topicTitle: LastSeenService.lastTopicTitle,
                    initialChapterIndex: LastSeenService.lastChapterIndex,
                  ),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.add_circle_outline, color: Colors.white),
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => UploadScreen()));
            },
          ),
        ],
      ),
      body: Container(
        width: double.infinity,
        margin: const EdgeInsets.only(top: 8),
        decoration: const BoxDecoration(
          color: Color(0xFFFBF8F5),
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: topics.length,
          itemBuilder: (context, index) {
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              elevation: 1,
              shadowColor: Colors.black12,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              color: Colors.white,
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                title: Text(
                  topics[index],
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.black87),
                ),
                trailing: const Icon(Icons.chevron_right, color: Colors.grey),
                onTap: () {
                  final topicName = topics[index].replaceAll(RegExp(r'^[૦-૯1-9].\s*'), '');
                  LastSeenService.saveLastSeen(topicName,0);

                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ChapterListScreen(topicTitle: topicName),
                    ),
                  );
                },
              ),
            );
          },
        ),
      ),
    );
  }
}