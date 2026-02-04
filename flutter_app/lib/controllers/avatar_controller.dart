/// Avatar animation controller with lip sync and idle animations.
///
/// Manages the avatar's animation state machine, lip sync timing,
/// idle animations (breathing/blinking), and emotion expressions.
/// Runs at 60 FPS with smooth interpolation between animation frames.

import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:demi_mobile/models/avatar_state.dart';
import 'package:demi_mobile/models/phoneme_data.dart';
import 'package:demi_mobile/services/audio_service.dart';

/// Callback for viseme (mouth shape) changes
typedef VisemeCallback = void Function(String viseme, double weight);

/// Callback for expression changes
typedef ExpressionCallback = void Function(String expression, double intensity);

/// Callback for idle animation updates
typedef IdleAnimationCallback = void Function(double breathing, double blinking);

/// Avatar animation controller with state machine and lip sync.
class AvatarController {
  /// Current avatar state
  AvatarState _state = AvatarState();

  /// Ticker for 60 FPS animation loop
  late Ticker _ticker;

  /// Audio service for playback control
  final AudioService audioService;

  /// Current time in milliseconds (for animation)
  int _elapsedMs = 0;

  /// Last blink time (for randomized blinking)
  late DateTime _lastBlinkTime;

  /// Random number generator for idle animations
  final _random = math.Random();

  /// Next blink interval in seconds (randomized 3-5s)
  late double _nextBlinkInterval;

  /// Callbacks for animation updates
  VisemeCallback? onVisemeChanged;
  ExpressionCallback? onExpressionChanged;
  IdleAnimationCallback? onIdleAnimation;

  /// Creates a new AvatarController
  AvatarController({required this.audioService}) {
    _lastBlinkTime = DateTime.now();
    _nextBlinkInterval = _randomBlinkInterval();
  }

  /// Initializes the animation controller and starts the ticker
  void initialize(TickerProvider vsync) {
    _ticker = Ticker(_animationTick);
    _ticker.start();
  }

  /// Main animation tick (called at 60 FPS)
  void _animationTick(Duration elapsed) {
    _elapsedMs = elapsed.inMilliseconds;

    // Update state based on audio playback
    final audioState = audioService.state;
    final wasPlaying = _state.isTalking;
    final isPlaying = audioState == AudioPlaybackState.playing;

    if (isPlaying != wasPlaying) {
      if (isPlaying) {
        _state = _state.copyWith(
          animationState: AvatarAnimationState.talking,
          isTalking: true,
        );
      } else {
        _state = _state.copyWith(
          animationState: AvatarAnimationState.idle,
          isTalking: false,
          audioPlaybackPosition: 0.0,
        );
      }
    }

    // Update audio position
    if (isPlaying) {
      _state = _state.copyWith(
        audioPlaybackPosition: audioService.currentPosition.inMilliseconds / 1000.0,
      );
    }

    // Update animations based on state
    if (_state.isTalking && _state.lipSyncData != null) {
      _updateLipSync(_state.audioPlaybackPosition);
    } else {
      _updateIdleAnimations(_elapsedMs);
    }
  }

  /// Updates lip sync based on current audio position
  void _updateLipSync(double currentTimeSeconds) {
    final lipSyncData = _state.lipSyncData;
    if (lipSyncData == null || lipSyncData.phonemes.isEmpty) {
      return;
    }

    // Get current and next phoneme frames
    PhonemeFrame? current;
    PhonemeFrame? next;

    for (int i = 0; i < lipSyncData.phonemes.length; i++) {
      if (lipSyncData.phonemes[i].time <= currentTimeSeconds) {
        current = lipSyncData.phonemes[i];
        if (i + 1 < lipSyncData.phonemes.length) {
          next = lipSyncData.phonemes[i + 1];
        }
      }
    }

    if (current == null) {
      // Before first phoneme, set to neutral
      onVisemeChanged?.call('neutral', 0.0);
      return;
    }

    // Interpolate between frames if next exists
    if (next != null) {
      final timeDiff = next.time - current.time;
      if (timeDiff > 0) {
        final t = (currentTimeSeconds - current.time) / timeDiff;
        final interpolation = t.clamp(0.0, 1.0);

        // Blend between current and next viseme
        // For smooth transitions, we crossfade between them
        if (interpolation < 0.5) {
          // First half: current viseme fading out
          final weight = 1.0 - (interpolation * 2);
          onVisemeChanged?.call(current.viseme, weight);
        } else {
          // Second half: next viseme fading in
          final weight = (interpolation - 0.5) * 2;
          onVisemeChanged?.call(next.viseme, weight);
        }
      } else {
        // Same time frame
        onVisemeChanged?.call(current.viseme, current.weight);
      }
    } else {
      // Last frame
      onVisemeChanged?.call(current.viseme, current.weight);
    }
  }

  /// Updates idle animations (breathing and blinking)
  void _updateIdleAnimations(int elapsedMs) {
    // Breathing animation: subtle sine wave
    final (breatheAmplitude, breatheFrequency) = _state.getIdleAnimationParams();
    final breathingPhase = (elapsedMs % (1000 / breatheFrequency).toInt()) /
        (1000 / breatheFrequency) *
        2 *
        math.pi;
    final breathing = math.sin(breathingPhase) * breatheAmplitude;

    // Blinking animation: random blinks every 3-5 seconds
    final now = DateTime.now();
    final timeSinceLastBlink = now.difference(_lastBlinkTime).inSeconds;

    double blinking = 0.0;
    if (timeSinceLastBlink >= _nextBlinkInterval) {
      _lastBlinkTime = now;
      _nextBlinkInterval = _randomBlinkInterval();
      blinking = 1.0; // Trigger blink
    }

    onIdleAnimation?.call(breathing, blinking);
  }

  /// Gets a random blink interval between 3-5 seconds
  double _randomBlinkInterval() {
    return 3.0 + _random.nextDouble() * 2.0; // 3-5 seconds
  }

  /// Sets lip sync data for a new response
  void setLipSyncData(LipSyncData lipSyncData) {
    _state = _state.copyWith(
      lipSyncData: lipSyncData,
      audioPlaybackPosition: 0.0,
    );
  }

  /// Sets the current emotional expression
  /// Automatically maps emotion to avatar expression
  void setExpression(AvatarExpression expression, {double intensity = 1.0}) {
    _state = _state.copyWith(
      currentExpression: expression,
      expressionIntensity: intensity.clamp(0.0, 1.0),
    );

    // Get expression name for callback
    final expressionName = _expressionToString(expression);
    onExpressionChanged?.call(expressionName, intensity);
  }

  /// Maps an emotion name to an avatar expression
  /// Used to convert Demi's emotional state to visual expression
  AvatarExpression mapEmotionToExpression(String emotion, double intensity) {
    // Map Demi's 9 emotions to avatar expressions
    final expressionMap = {
      'lonely': AvatarExpression.sad,
      'vulnerability': AvatarExpression.sad,
      'excitement': AvatarExpression.happy,
      'affection': AvatarExpression.happy,
      'frustrated': AvatarExpression.angry,
      'frustration': AvatarExpression.angry,
      'jealousy': AvatarExpression.angry,
      'jealous': AvatarExpression.angry,
      'defensive': AvatarExpression.angry,
      'defensiveness': AvatarExpression.angry,
      'curiosity': AvatarExpression.surprised,
      'curious': AvatarExpression.surprised,
      'confidence': AvatarExpression.neutral,
      'affection': AvatarExpression.happy,
    };

    final expression = expressionMap[emotion.toLowerCase()] ?? AvatarExpression.neutral;
    setExpression(expression, intensity: intensity);
    return expression;
  }

  /// Converts expression enum to string for animation system
  String _expressionToString(AvatarExpression expression) {
    switch (expression) {
      case AvatarExpression.neutral:
        return 'neutral';
      case AvatarExpression.happy:
        return 'happy';
      case AvatarExpression.sad:
        return 'sad';
      case AvatarExpression.angry:
        return 'angry';
      case AvatarExpression.surprised:
        return 'surprised';
    }
  }

  /// Resets to idle state
  void reset() {
    _state = AvatarState();
    _elapsedMs = 0;
    onVisemeChanged?.call('neutral', 0.0);
    onExpressionChanged?.call('neutral', 1.0);
  }

  /// Disposes resources
  void dispose() {
    _ticker.stop();
    _ticker.dispose();
  }

  // Getters
  AvatarState get state => _state;
  AvatarAnimationState get animationState => _state.animationState;
  AvatarExpression get currentExpression => _state.currentExpression;
  bool get isTalking => _state.isTalking;
  double get expressionIntensity => _state.expressionIntensity;
}
