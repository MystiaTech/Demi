class EmotionState {
  final double loneliness;
  final double excitement;
  final double frustration;
  final double jealousy;
  final double vulnerability;
  final double confidence;
  final double curiosity;
  final double affection;
  final double defensiveness;

  EmotionState({
    this.loneliness = 0,
    this.excitement = 0,
    this.frustration = 0,
    this.jealousy = 0,
    this.vulnerability = 0,
    this.confidence = 0,
    this.curiosity = 0,
    this.affection = 0,
    this.defensiveness = 0,
  });

  factory EmotionState.fromJson(Map<String, dynamic> json) {
    return EmotionState(
      loneliness: (json['loneliness'] ?? 0).toDouble(),
      excitement: (json['excitement'] ?? 0).toDouble(),
      frustration: (json['frustration'] ?? 0).toDouble(),
      jealousy: (json['jealousy'] ?? 0).toDouble(),
      vulnerability: (json['vulnerability'] ?? 0).toDouble(),
      confidence: (json['confidence'] ?? 0).toDouble(),
      curiosity: (json['curiosity'] ?? 0).toDouble(),
      affection: (json['affection'] ?? 0).toDouble(),
      defensiveness: (json['defensiveness'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
    'loneliness': loneliness,
    'excitement': excitement,
    'frustration': frustration,
    'jealousy': jealousy,
    'vulnerability': vulnerability,
    'confidence': confidence,
    'curiosity': curiosity,
    'affection': affection,
    'defensiveness': defensiveness,
  };

  Map<String, double> toMap() => {
    'loneliness': loneliness,
    'excitement': excitement,
    'frustration': frustration,
    'jealousy': jealousy,
    'vulnerability': vulnerability,
    'confidence': confidence,
    'curiosity': curiosity,
    'affection': affection,
    'defensiveness': defensiveness,
  };

  String get dominantEmotion {
    final emotions = {
      'Lonely': loneliness,
      'Excited': excitement,
      'Frustrated': frustration,
      'Jealous': jealousy,
      'Vulnerable': vulnerability,
      'Confident': confidence,
      'Curious': curiosity,
      'Affectionate': affection,
      'Defensive': defensiveness,
    };

    final dominant = emotions.entries.reduce((a, b) => a.value > b.value ? a : b);
    return dominant.key;
  }

  double get dominantEmotionValue {
    final emotions = [
      loneliness,
      excitement,
      frustration,
      jealousy,
      vulnerability,
      confidence,
      curiosity,
      affection,
      defensiveness,
    ];
    return emotions.reduce((a, b) => a > b ? a : b);
  }
}
