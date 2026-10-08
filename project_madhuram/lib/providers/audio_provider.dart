import 'package:flutter/material.dart';
import '../models/models.dart';

class AudioProvider with ChangeNotifier {
  AudioTrack? _currentTrack;
  bool _isPlaying = false;
  double _playbackPosition = 0.3; // Progress bar value (0.0 to 1.0)

  AudioTrack? get currentTrack => _currentTrack;
  bool get isPlaying => _isPlaying;
  double get playbackPosition => _playbackPosition;

  final List<AudioTrack> tracks = [
    AudioTrack(
      id: '1',
      title: 'Hare Krishna Mahamantra',
      artist: 'HG Aindra Das',
      category: 'Kirtan',
      duration: '09:40',
      audioUrl: '',
    ),
    AudioTrack(
      id: '2',
      title: 'Flute Melodies of Vrindavan',
      artist: 'Classical Devotional',
      category: 'Flute Meditation',
      duration: '08:15',
      audioUrl: '',
    ),
    AudioTrack(
      id: '3',
      title: 'Achyutam Keshavam Krishna Damodaram',
      artist: 'Devotional Bhajan',
      category: 'Bhajans',
      duration: '05:22',
      audioUrl: '',
    ),
    AudioTrack(
      id: '4',
      title: 'Shree Madhurashtakam',
      artist: 'Traditional Chants',
      category: 'Stotram',
      duration: '04:10',
      audioUrl: '',
    ),
  ];

  void playTrack(AudioTrack track) {
    _currentTrack = track;
    _isPlaying = true;
    _playbackPosition = 0.0;
    notifyListeners();
  }

  void togglePlay() {
    if (_currentTrack == null && tracks.isNotEmpty) {
      _currentTrack = tracks.first;
    }
    _isPlaying = !_isPlaying;
    notifyListeners();
  }

  void playNextTrack() {
    if (_currentTrack == null) return;
    int currentIndex = tracks.indexWhere((t) => t.id == _currentTrack!.id);
    if (currentIndex < tracks.length - 1) {
      playTrack(tracks[currentIndex + 1]);
    } else {
      playTrack(tracks.first);
    }
  }

  void playPreviousTrack() {
    if (_currentTrack == null) return;
    int currentIndex = tracks.indexWhere((t) => t.id == _currentTrack!.id);
    if (currentIndex > 0) {
      playTrack(tracks[currentIndex - 1]);
    } else {
      playTrack(tracks.last);
    }
  }

  void seekPosition(double value) {
    _playbackPosition = value;
    notifyListeners();
  }

  void toggleTrackFavorite(String id) {
    final index = tracks.indexWhere((t) => t.id == id);
    if (index != -1) {
      tracks[index].isFavorite = !tracks[index].isFavorite;
      notifyListeners();
    }
  }
}