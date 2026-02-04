import 'package:flutter/material.dart';
import '../models/emotion.dart';

class EmotionDisplay extends StatelessWidget {
  final EmotionState emotionState;

  const EmotionDisplay({
    Key? key,
    required this.emotionState,
  }) : super(key: key);

  Color _getEmotionColor(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'lonely':
      case 'loneliness':
        return Colors.purple;
      case 'excited':
      case 'excitement':
        return Colors.green;
      case 'frustrated':
      case 'frustration':
        return Colors.red;
      case 'jealous':
      case 'jealousy':
        return Colors.orange;
      case 'vulnerable':
      case 'vulnerability':
        return Colors.pink;
      case 'confident':
      case 'confidence':
        return Colors.blue;
      case 'curious':
      case 'curiosity':
        return Colors.cyan;
      case 'affectionate':
      case 'affection':
        return Colors.deepOrange;
      case 'defensive':
      case 'defensiveness':
        return Colors.grey;
      default:
        return Colors.blueGrey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final dominant = emotionState.dominantEmotion;
    final dominantValue = emotionState.dominantEmotionValue;
    final color = _getEmotionColor(dominant);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Demi\'s Mood',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  dominant,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: color,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            // Progress bar for emotion intensity
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: dominantValue / 10,
                minHeight: 4,
                backgroundColor: color.withOpacity(0.2),
                valueColor: AlwaysStoppedAnimation<Color>(color),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
