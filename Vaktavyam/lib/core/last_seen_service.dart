class LastSeenService {
  static String lastTopicTitle = 'કામ';
  static int lastChapterIndex = 0;

  // Enclosing chapterIndex in brackets [] makes it optional (defaults to 0)
  static void saveLastSeen(String topicTitle, [int chapterIndex = 0]) {
    lastTopicTitle = topicTitle;
    lastChapterIndex = chapterIndex;
  }
}