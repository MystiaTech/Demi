/// Phoneme data models for lip sync animation.
///
/// Contains data structures for phoneme frames and lip sync data
/// that drive the avatar's mouth animations synchronized with audio.

import 'package:json_annotation/json_annotation.dart';

part 'phoneme_data.g.dart';

/// A single phoneme frame with timing and viseme information.
@JsonSerializable()
class PhonemeFrame {
  /// Time in seconds when this phoneme should be active
  final double time;

  /// Viseme target (aa, ih, ou, E, neutral)
  final String viseme;

  /// Blend shape weight 0.0-1.0 (1.0 = full intensity)
  final double weight;

  /// Optional duration of this phoneme in seconds
  final double? duration;

  /// Creates a new PhonemeFrame
  PhonemeFrame({
    required this.time,
    required this.viseme,
    this.weight = 1.0,
    this.duration,
  });

  /// Creates a PhonemeFrame from JSON
  factory PhonemeFrame.fromJson(Map<String, dynamic> json) =>
      _$PhonemeFrameFromJson(json);

  /// Converts to JSON
  Map<String, dynamic> toJson() => _$PhonemeFrameToJson(this);

  @override
  String toString() =>
      'PhonemeFrame(time: $time, viseme: $viseme, weight: $weight)';
}

/// Complete lip sync data for a response.
///
/// Contains audio URL, phoneme frames, and total duration
/// for a complete speech response.
@JsonSerializable()
class LipSyncData {
  /// URL to audio file for streaming
  final String audioUrl;

  /// List of phoneme frames with timing
  final List<PhonemeFrame> phonemes;

  /// Total duration in seconds
  final double duration;

  /// Creates a new LipSyncData
  LipSyncData({
    required this.audioUrl,
    required this.phonemes,
    required this.duration,
  });

  /// Creates LipSyncData from JSON
  factory LipSyncData.fromJson(Map<String, dynamic> json) =>
      _$LipSyncDataFromJson(json);

  /// Converts to JSON
  Map<String, dynamic> toJson() => _$LipSyncDataToJson(this);

  /// Gets the phoneme frame at a specific time (for animation)
  PhonemeFrame? getPhonemeAtTime(double timeSeconds) {
    // Find current and next phoneme frames
    PhonemeFrame? current;
    PhonemeFrame? next;

    for (int i = 0; i < phonemes.length; i++) {
      if (phonemes[i].time <= timeSeconds) {
        current = phonemes[i];
        if (i + 1 < phonemes.length) {
          next = phonemes[i + 1];
        }
      } else {
        break;
      }
    }

    return current;
  }

  /// Gets interpolation between two phoneme frames
  /// Returns [PhonemeFrame, weight] where weight indicates blend between frames
  (PhonemeFrame?, double) getInterpolationAtTime(double timeSeconds) {
    PhonemeFrame? current;
    PhonemeFrame? next;

    for (int i = 0; i < phonemes.length; i++) {
      if (phonemes[i].time <= timeSeconds) {
        current = phonemes[i];
        if (i + 1 < phonemes.length) {
          next = phonemes[i + 1];
        }
      }
    }

    if (current == null) {
      return (null, 0.0);
    }

    if (next == null) {
      return (current, 1.0);
    }

    // Calculate interpolation weight
    final timeDiff = next.time - current.time;
    if (timeDiff <= 0) {
      return (current, 1.0);
    }

    final weight = (timeSeconds - current.time) / timeDiff;
    return (current, weight.clamp(0.0, 1.0));
  }

  @override
  String toString() =>
      'LipSyncData(audioUrl: $audioUrl, phonemes: ${phonemes.length}, duration: $duration)';
}
