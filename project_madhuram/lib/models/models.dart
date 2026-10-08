class DarshanItem {
  final String id;
  final String templeName;
  final String location;
  final String imageUrl;
  final String date;
  final String category;
  bool isFavorite;

  DarshanItem({
    required this.id,
    required this.templeName,
    required this.location,
    required this.imageUrl,
    required this.date,
    required this.category,
    this.isFavorite = false,
  });
}

class AudioTrack {
  final String id;
  final String title;
  final String artist;
  final String category;
  final String duration;
  final String audioUrl;
  bool isFavorite;

  AudioTrack({
    required this.id,
    required this.title,
    required this.artist,
    required this.category,
    required this.duration,
    required this.audioUrl,
    this.isFavorite = false,
  });
}

class GitaVerse {
  final int chapter;
  final int verse;
  final String sanskrit;
  final String translation;
  final String explanation;
  bool isBookmarked;

  GitaVerse({
    required this.chapter,
    required this.verse,
    required this.sanskrit,
    required this.translation,
    required this.explanation,
    this.isBookmarked = false,
  });
}