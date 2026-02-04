import 'package:flutter/material.dart';
import '../models/message.dart';
import 'action_text.dart';

class MessageBubble extends StatelessWidget {
  final Message message;

  const MessageBubble({
    Key? key,
    required this.message,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDemi = message.isDemiMessage;
    final colors = Theme.of(context).colorScheme;

    return Align(
      alignment: isDemi ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        child: Column(
          crossAxisAlignment:
              isDemi ? CrossAxisAlignment.start : CrossAxisAlignment.end,
          children: [
            Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.75,
              ),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: isDemi
                    ? colors.surfaceVariant
                    : colors.primary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: ActionText(
                text: message.content,
                style: TextStyle(
                  color: isDemi
                      ? colors.onSurfaceVariant
                      : colors.onPrimary,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Text(
                message.formattedTime,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
