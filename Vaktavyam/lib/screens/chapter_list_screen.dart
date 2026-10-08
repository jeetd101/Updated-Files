import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/last_seen_service.dart';
import 'package:share_plus/share_plus.dart';

class ChapterListScreen extends StatelessWidget {
  final String topicTitle;
  final int initialChapterIndex;

  const ChapterListScreen({
    super.key,
    required this.topicTitle,
    this.initialChapterIndex = 0,
  });

  final List<String> chapters = const [
    '૧. સંત આશ્રમ',
    '૨. સંત ભંડાર',
    '૩. સત્સંગ પ્રચાર',
    '૪. સંતો/હરિભક્તોની કેર',
    '૨. સંત ભંડાર',
    '૩. સત્સંગ પ્રચાર',
    '૪. સંતો/હરિભક્તોની કેર',
    '૪. સંતો/હરિભક્તોની કેર',
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
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Chapters - $topicTitle',
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
        ),
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
          itemCount: chapters.length,
          itemBuilder: (context, index) {
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              elevation: 1,
              shadowColor: Colors.black12,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              color: Colors.white,
              child: Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  initiallyExpanded: index == initialChapterIndex,
                  onExpansionChanged: (isExpanded) {
                    if (isExpanded) {
                      LastSeenService.saveLastSeen(topicTitle, index);
                    }
                  },
                  tilePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                  title: Text(
                    chapters[index],
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.black87),
                  ),
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '.................................................................................................................\n'
                                '.................................................................................................................\n'
                                '.................................................................................................................\n'
                                '.................................................................................................................',
                            style: TextStyle(color: Colors.grey, fontSize: 12, height: 1.4),
                          ),
                          Align(
                            alignment: Alignment.centerRight,
                            child: TextButton(
                              onPressed: () {},
                              style: TextButton.styleFrom(padding: EdgeInsets.zero),
                              child: const Text('Read more', style: TextStyle(color: Colors.green, fontSize: 13, fontWeight: FontWeight.bold)),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              ElevatedButton.icon(
                                onPressed: () {
                                  Clipboard.setData(const ClipboardData(text: 'Sample chapter text copied!'));
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Content copied to clipboard!')),
                                  );
                                },
                                icon: const Icon(Icons.copy, size: 16, color: Colors.black87),
                                label: const Text('Copy', style: TextStyle(color: Colors.black87)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFFE2C075),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                                  elevation: 0,
                                ),
                              ),
                              const SizedBox(width: 12),
                              ElevatedButton.icon(
                                onPressed: () {
                                  Share.share(
                                    '૧. સંત આશ્રમ\n\nWrite or pass your chapter content here...',
                                    subject: 'Chapters - કામ',
                                  );
                                },
                                icon: const Icon(Icons.send, size: 16, color: Colors.black87),
                                label: const Text('Share', style: TextStyle(color: Colors.black87)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFFE2C075),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                                  elevation: 0,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}