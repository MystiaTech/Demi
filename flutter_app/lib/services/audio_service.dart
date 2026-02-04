/// Audio playback service for TTS and lip sync.
///
/// Handles streaming audio from backend, playback control,
/// and position tracking for synchronized lip sync animation.

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:audioplayers/audioplayers.dart';

/// Audio playback state
enum AudioPlaybackState {
  /// Audio is not loaded
  idle,

  /// Audio is loading/buffering
  loading,

  /// Audio is currently playing
  playing,

  /// Audio playback is paused
  paused,

  /// Audio playback is complete
  completed,

  /// Error occurred during playback
  error,
}

/// Audio service for managing TTS playback.
class AudioService {
  late AudioPlayer _audioPlayer;
  late StreamSubscription<Duration> _positionSubscription;
  late StreamSubscription<PlayerState> _stateSubscription;

  /// Current playback position
  Duration _currentPosition = Duration.zero;

  /// Total audio duration
  Duration _duration = Duration.zero;

  /// Current playback state
  AudioPlaybackState _state = AudioPlaybackState.idle;

  /// Stream controller for position updates
  final _positionController = StreamController<Duration>.broadcast();

  /// Stream controller for state changes
  final _stateController = StreamController<AudioPlaybackState>.broadcast();

  /// Completion callback
  VoidCallback? _onComplete;

  /// Error callback
  void Function(String)? _onError;

  /// Creates a new AudioService
  AudioService() {
    _audioPlayer = AudioPlayer();
    _setupListeners();
  }

  /// Sets up internal listeners for player events
  void _setupListeners() {
    // Listen to player state changes
    _audioPlayer.onPlayerStateChanged.listen((PlayerState state) {
      _updateState(state);
    });

    // Listen to position updates
    _audioPlayer.onPositionChanged.listen((Duration position) {
      _currentPosition = position;
      _positionController.add(position);
    });

    // Listen to duration changes
    _audioPlayer.onDurationChanged.listen((Duration duration) {
      _duration = duration;
    });
  }

  /// Updates internal state based on player state
  void _updateState(PlayerState playerState) {
    AudioPlaybackState newState;

    switch (playerState) {
      case PlayerState.stopped:
        newState = AudioPlaybackState.completed;
        _onComplete?.call();
        break;
      case PlayerState.playing:
        newState = AudioPlaybackState.playing;
        break;
      case PlayerState.paused:
        newState = AudioPlaybackState.paused;
        break;
      case PlayerState.completed:
        newState = AudioPlaybackState.completed;
        _onComplete?.call();
        break;
      case PlayerState.disposed:
        newState = AudioPlaybackState.idle;
        break;
    }

    _state = newState;
    _stateController.add(newState);
  }

  /// Plays audio from a network URL
  ///
  /// Args:
  ///   url: Full URL to audio file
  ///   onComplete: Callback when playback completes
  ///   onError: Callback if playback fails
  ///
  /// Returns:
  ///   True if playback started, false if error occurred
  Future<bool> playFromUrl(
    String url, {
    VoidCallback? onComplete,
    void Function(String)? onError,
  }) async {
    try {
      _onComplete = onComplete;
      _onError = onError;

      _state = AudioPlaybackState.loading;
      _stateController.add(_state);

      // Play from URL
      await _audioPlayer.play(UrlSource(url));

      return true;
    } catch (e) {
      _state = AudioPlaybackState.error;
      _stateController.add(_state);
      _onError?.call('Failed to play audio: $e');
      return false;
    }
  }

  /// Pauses playback
  Future<void> pause() async {
    await _audioPlayer.pause();
  }

  /// Resumes playback
  Future<void> resume() async {
    await _audioPlayer.resume();
  }

  /// Stops playback and resets position
  Future<void> stop() async {
    await _audioPlayer.stop();
    _currentPosition = Duration.zero;
  }

  /// Sets playback position
  Future<void> seek(Duration position) async {
    await _audioPlayer.seek(position);
  }

  /// Disposes resources
  Future<void> dispose() async {
    await _positionSubscription.cancel();
    await _stateSubscription.cancel();
    await _positionController.close();
    await _stateController.close();
    await _audioPlayer.dispose();
  }

  // Getters
  AudioPlaybackState get state => _state;
  Duration get currentPosition => _currentPosition;
  Duration get duration => _duration;
  Stream<Duration> get positionStream => _positionController.stream;
  Stream<AudioPlaybackState> get stateStream => _stateController.stream;

  bool get isPlaying => _state == AudioPlaybackState.playing;
  bool get isPaused => _state == AudioPlaybackState.paused;
  bool get isCompleted => _state == AudioPlaybackState.completed;

  /// Gets playback progress as a percentage (0.0-1.0)
  double get progress {
    if (_duration.inMilliseconds == 0) return 0.0;
    return (_currentPosition.inMilliseconds / _duration.inMilliseconds)
        .clamp(0.0, 1.0);
  }
}
