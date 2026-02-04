/// Maps Demi's 9 emotional dimensions to avatar expressions and intensity.
///
/// Converts EmotionState (continuous 0.0-1.0 values for each emotion)
/// to discrete avatar expressions with appropriate intensity levels.

import 'package:demi_mobile/models/avatar_state.dart';

/// Emotion to expression mapping configuration
class EmotionExpressionMapping {
  /// Dominant emotion name
  final String emotionName;

  /// Corresponding avatar expression
  final AvatarExpression expression;

  /// Intensity of the expression (0.0-1.0)
  final double intensity;

  /// Creates a mapping
  const EmotionExpressionMapping({
    required this.emotionName,
    required this.expression,
    required this.intensity,
  });
}

/// Maps Demi's emotional state to avatar expressions.
class EmotionMapper {
  /// Maps emotion dimensions to avatar expressions
  /// Returns the dominant emotion expression
  static EmotionExpressionMapping mapEmotionToExpression(
    Map<String, double> emotionState,
  ) {
    if (emotionState.isEmpty) {
      return EmotionExpressionMapping(
        emotionName: 'neutral',
        expression: AvatarExpression.neutral,
        intensity: 0.5,
      );
    }

    // Find dominant emotions and their intensities
    double loneliness = emotionState['loneliness'] ?? 0.0;
    double excitement = emotionState['excitement'] ?? 0.0;
    double frustration = emotionState['frustration'] ?? 0.0;
    double jealousy = emotionState['jealousy'] ?? 0.0;
    double vulnerability = emotionState['vulnerability'] ?? 0.0;
    double confidence = emotionState['confidence'] ?? 0.0;
    double curiosity = emotionState['curiosity'] ?? 0.0;
    double affection = emotionState['affection'] ?? 0.0;
    double defensiveness = emotionState['defensiveness'] ?? 0.0;

    // Group emotions by expression type
    final sadIntensity = (loneliness + vulnerability) / 2;
    final happyIntensity = (excitement + affection) / 2;
    final angryIntensity = (frustration + jealousy + defensiveness) / 3;
    final surprisedIntensity = curiosity;
    final neutralIntensity = (confidence + (1.0 - sadIntensity - happyIntensity - angryIntensity - surprisedIntensity)) / 2;

    // Find the dominant emotion group
    final emotionIntensities = {
      'sad': sadIntensity,
      'happy': happyIntensity,
      'angry': angryIntensity,
      'surprised': surprisedIntensity,
      'neutral': neutralIntensity,
    };

    // Get dominant emotion (highest intensity)
    String dominantEmotion = 'neutral';
    double maxIntensity = 0.0;

    emotionIntensities.forEach((emotion, intensity) {
      if (intensity > maxIntensity) {
        maxIntensity = intensity;
        dominantEmotion = emotion;
      }
    });

    // Map to avatar expression
    final expressionMap = {
      'sad': AvatarExpression.sad,
      'happy': AvatarExpression.happy,
      'angry': AvatarExpression.angry,
      'surprised': AvatarExpression.surprised,
      'neutral': AvatarExpression.neutral,
    };

    return EmotionExpressionMapping(
      emotionName: dominantEmotion,
      expression: expressionMap[dominantEmotion] ?? AvatarExpression.neutral,
      intensity: maxIntensity.clamp(0.0, 1.0),
    );
  }

  /// Gets specific emotion value
  static double getEmotionValue(
    Map<String, double> emotionState,
    String emotionName,
  ) {
    return (emotionState[emotionName] ?? 0.0).clamp(0.0, 1.0);
  }

  /// Checks if an emotion is significantly expressed
  /// Returns true if intensity is above threshold (default 0.3)
  static bool isEmotionActive(
    Map<String, double> emotionState,
    String emotionName, {
    double threshold = 0.3,
  }) {
    return getEmotionValue(emotionState, emotionName) >= threshold;
  }

  /// Gets all active emotions above threshold
  static List<String> getActiveEmotions(
    Map<String, double> emotionState, {
    double threshold = 0.2,
  }) {
    final active = <String>[];
    emotionState.forEach((emotion, value) {
      if (value >= threshold) {
        active.add(emotion);
      }
    });
    return active;
  }

  /// Describes the emotion state in human-readable text
  static String describeEmotionState(Map<String, double> emotionState) {
    final mapping = mapEmotionToExpression(emotionState);

    final descriptions = {
      'sad': 'Demi seems lonely and vulnerable...',
      'happy': 'Demi is excited and affectionate!',
      'angry': 'Demi seems frustrated or defensive.',
      'surprised': 'Demi is curious and intrigued!',
      'neutral': 'Demi is calm and composed.',
    };

    return descriptions[mapping.emotionName] ?? 'Demi appears neutral.';
  }

  /// Gets color for emotion (for UI visualization)
  static String getEmotionColor(String emotion) {
    const colorMap = {
      'loneliness': '#9C27B0', // Purple
      'excitement': '#4CAF50', // Green
      'frustration': '#F44336', // Red
      'jealousy': '#FF9800', // Orange
      'vulnerability': '#E91E63', // Pink
      'confidence': '#2196F3', // Blue
      'curiosity': '#00BCD4', // Cyan
      'affection': '#FF5722', // Deep Orange
      'defensiveness': '#9E9E9E', // Grey
    };

    return colorMap[emotion] ?? '#9E9E9E';
  }
}
