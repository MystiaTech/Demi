import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:logger/logger.dart';
import 'dart:convert';

typedef MessageCallback = void Function(Map<String, dynamic>);

class WebSocketService {
  late WebSocketChannel _channel;
  final Logger logger = Logger();
  bool _isConnected = false;
  late MessageCallback onMessage;

  bool get isConnected => _isConnected;

  /// Connect to WebSocket server
  Future<bool> connect(String url) async {
    try {
      logger.i('Connecting to WebSocket: $url');
      _channel = WebSocketChannel.connect(Uri.parse(url));

      // Listen for messages
      _channel.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message);
            onMessage(data);
          } catch (e) {
            logger.e('Error parsing message: $e');
          }
        },
        onError: (error) {
          logger.e('WebSocket error: $error');
          _isConnected = false;
        },
        onDone: () {
          logger.i('WebSocket disconnected');
          _isConnected = false;
        },
      );

      _isConnected = true;
      logger.i('WebSocket connected');
      return true;
    } catch (e) {
      logger.e('WebSocket connection failed: $e');
      return false;
    }
  }

  /// Send a message
  void sendMessage(String content) {
    if (!_isConnected) {
      logger.w('WebSocket not connected');
      return;
    }

    try {
      final message = jsonEncode({'message': content});
      _channel.sink.add(message);
      logger.i('Message sent: $content');
    } catch (e) {
      logger.e('Error sending message: $e');
    }
  }

  /// Disconnect from WebSocket
  void disconnect() {
    try {
      _channel.sink.close();
      _isConnected = false;
      logger.i('WebSocket disconnected');
    } catch (e) {
      logger.e('Error closing WebSocket: $e');
    }
  }

  /// Reconnect to WebSocket
  Future<bool> reconnect(String url) async {
    disconnect();
    await Future.delayed(const Duration(seconds: 2));
    return connect(url);
  }
}
