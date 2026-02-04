import 'package:intl/intl.dart';

class Message {
  final String id;
  final String content;
  final String from; // 'user' or 'demi'
  final DateTime timestamp;
  final bool isLoading;
  final String? error;

  Message({
    required this.content,
    required this.from,
    required this.timestamp,
    String? id,
    this.isLoading = false,
    this.error,
  }) : id = id ?? DateTime.now().millisecondsSinceEpoch.toString();

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'] ?? '',
      content: json['content'] ?? '',
      from: json['from'] ?? 'demi',
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
      isLoading: json['isLoading'] ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'content': content,
    'from': from,
    'timestamp': timestamp.toIso8601String(),
    'isLoading': isLoading,
  };

  String get formattedTime {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return DateFormat('MMM d').format(timestamp);
    }
  }

  bool get isUserMessage => from == 'user';
  bool get isDemiMessage => from == 'demi';
}
