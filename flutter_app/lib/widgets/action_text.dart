import 'package:flutter/material.dart';

/// Text widget that renders actions (*action* or _action_) in italics
class ActionText extends StatelessWidget {
  final String text;
  final TextStyle? style;

  const ActionText({
    Key? key,
    required this.text,
    this.style,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final defaultStyle = style ?? DefaultTextStyle.of(context).style;
    final spans = _parseActions(text, defaultStyle);
    
    return RichText(
      text: TextSpan(children: spans),
    );
  }

  List<TextSpan> _parseActions(String text, TextStyle baseStyle) {
    final spans = <TextSpan>[];
    final actionPattern = RegExp(r'\*(.+?)\*|_(.+?)_');
    
    int lastEnd = 0;
    for (final match in actionPattern.allMatches(text)) {
      // Add text before the action
      if (match.start > lastEnd) {
        spans.add(TextSpan(
          text: text.substring(lastEnd, match.start),
          style: baseStyle,
        ));
      }
      
      // Add the action in italics with a slight color change
      final actionText = match.group(1) ?? match.group(2) ?? '';
      spans.add(TextSpan(
        text: actionText,
        style: baseStyle.copyWith(
          fontStyle: FontStyle.italic,
          fontWeight: FontWeight.w500,
          // Slightly lighter/different color for actions
          color: baseStyle.color?.withOpacity(0.9),
        ),
      ));
      
      lastEnd = match.end;
    }
    
    // Add remaining text
    if (lastEnd < text.length) {
      spans.add(TextSpan(
        text: text.substring(lastEnd),
        style: baseStyle,
      ));
    }
    
    return spans;
  }
}
