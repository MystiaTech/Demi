/// Avatar animation and emotional state model.
///
/// Defines the avatar's animation states, expressions, and emotional responses.

import 'package:demi_mobile/models/phoneme_data.dart';

/// Animation state of the avatar.
enum AvatarAnimationState {
  /// Avatar is idle/breathing
  idle,

  /// Avatar is speaking/lip syncing to audio
  talking,

  /// Avatar is performing a gesture (wave, nod, etc.)
  gesture,

  /// Avatar is in transition between states
  transitioning,
}

/// Emotion to expression mapping for the avatar.
enum AvatarExpression {
  /// Neutral - no expression
  neutral,

  /// Happy/excited - smile
  happy,

  /// Sad/lonely - frown
  sad,

  /// Angry/frustrated - angry expression
  angry,

  /// Surprised/curious - surprised expression
  surprised,
}

/// Complete avatar state including animation and emotion.
class AvatarState {
  /// Current animation state
  final AvatarAnimationState animationState;

  /// Current emotional expression
  final AvatarExpression currentExpression;

  /// Current lip sync data (if talking)
  final LipSyncData? lipSyncData;

  /// Current audio playback position in seconds
  final double audioPlaybackPosition;

  /// Whether the avatar is actively talking
  final bool isTalking;

  /// Intensity of the current expression (0.0-1.0)
  final double expressionIntensity;

  /// Creates a new AvatarState
  AvatarState({
    this.animationState = AvatarAnimationState.idle,
    this.currentExpression = AvatarExpression.neutral,
    this.lipSyncData,
    this.audioPlaybackPosition = 0.0,
    this.isTalking = false,
    this.expressionIntensity = 1.0,
  });

  /// Creates a copy with some fields replaced
  AvatarState copyWith({
    AvatarAnimationState? animationState,
    AvatarExpression? currentExpression,
    LipSyncData? lipSyncData,
    double? audioPlaybackPosition,
    bool? isTalking,
    double? expressionIntensity,
  }) {
    return AvatarState(
      animationState: animationState ?? this.animationState,
      currentExpression: currentExpression ?? this.currentExpression,
      lipSyncData: lipSyncData ?? this.lipSyncData,
      audioPlaybackPosition: audioPlaybackPosition ?? this.audioPlaybackPosition,
      isTalking: isTalking ?? this.isTalking,
      expressionIntensity: expressionIntensity ?? this.expressionIntensity,
    );
  }

  /// Gets idle animation parameters
  /// Returns breathing parameters: amplitude and frequency
  (double amplitude, double frequency) getIdleAnimationParams() {
    // Subtle breathing animation
    // Amplitude: 0.02 (2% of body sway)
    // Frequency: 0.5 Hz (one breath every 2 seconds)
    return (0.02, 0.5);
  }

  /// Gets blinking parameters
  /// Returns blink interval in seconds (random between min-max)
  (double minInterval, double maxInterval) getBlinkingParams() {
    // Random blink every 3-5 seconds
    return (3.0, 5.0);
  }

  @override
  String toString() =>
      'AvatarState(animation: $animationState, expression: $currentExpression, talking: $isTalking)';
}
