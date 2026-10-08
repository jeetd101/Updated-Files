import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import '../data/app_data.dart';

class AudioPlayerService extends ChangeNotifier {
  static final AudioPlayerService instance = AudioPlayerService._internal();
  factory AudioPlayerService() => instance;
  AudioPlayerService._internal() {
    _player.onPlayerStateChanged.listen((state) {
      isPlaying = state == PlayerState.playing;
      notifyListeners();
    });
  }

  final AudioPlayer _player = AudioPlayer();
  AudioTrack? currentTrack;
  bool isPlaying = false;

  Future<void> playTrack(AudioTrack track) async {
    if (currentTrack?.id == track.id && isPlaying) {
      await pause();
      return;
    }
    currentTrack = track;
    await _player.stop();
    await _player.play(UrlSource(track.audioUrl));
    isPlaying = true;
    notifyListeners();
  }

  Future<void> pause() async {
    await _player.pause();
    isPlaying = false;
    notifyListeners();
  }

  Future<void> resume() async {
    if (currentTrack != null) {
      await _player.resume();
      isPlaying = true;
      notifyListeners();
    }
  }
}