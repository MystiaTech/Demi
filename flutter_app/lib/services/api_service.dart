import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:logger/logger.dart';

class ApiService {
  final String baseUrl;
  final Logger logger = Logger();
  late String userId;
  late String sessionId;

  // Default server URL - can be overridden via constructor
  // Use 10.0.2.2 for Android emulator (maps to host localhost)
  // Use your machine's LAN IP for physical devices (e.g., http://192.168.1.245:8081)
  static const String defaultServerUrl = String.fromEnvironment(
    'SERVER_URL',
    defaultValue: 'http://192.168.1.245:8081',
  );

  ApiService({String? baseUrl}) : baseUrl = baseUrl ?? defaultServerUrl;

  /// Login to get a session with retry logic
  Future<bool> login({String? customUserId}) async {
    const maxRetries = 5;
    const delayBetweenRetries = Duration(seconds: 1);

    for (int attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        final Uri loginUri = Uri.parse('$baseUrl/api/auth/login').replace(
          queryParameters: customUserId != null ? {'user_id': customUserId} : {},
        );

        logger.i('Attempting login to: $loginUri (attempt $attempt/$maxRetries)');
        final response = await http.post(loginUri).timeout(const Duration(seconds: 5));

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          userId = data['user_id'] ?? '';
          sessionId = data['session_id'] ?? '';
          logger.i('Login successful: $userId');
          return true;
        } else if (response.statusCode == 404) {
          // 404 means the server is reachable but endpoint doesn't exist
          logger.e('Login endpoint not found (404). Server: $baseUrl');
          logger.e('Response body: ${response.body}');
          if (attempt < maxRetries) {
            logger.w('Retrying... (attempt $attempt/$maxRetries)');
            await Future.delayed(delayBetweenRetries);
            continue;
          }
          return false;
        } else if (response.statusCode >= 500) {
          // Server errors - retry
          logger.w('Server error (${response.statusCode}), retrying... (attempt $attempt/$maxRetries)');
          if (attempt < maxRetries) {
            await Future.delayed(delayBetweenRetries);
            continue;
          }
          return false;
        } else {
          logger.e('Login failed: ${response.statusCode} - ${response.body}');
          return false;
        }
      } on http.ClientException catch (e) {
        // Network/connection errors
        logger.w('Connection error: $e (attempt $attempt/$maxRetries)');
        if (attempt < maxRetries) {
          logger.w('Server may not be ready, retrying...');
          await Future.delayed(delayBetweenRetries);
        } else {
          logger.e('Login failed: Cannot connect to server at $baseUrl');
          logger.e('Please check:');
          logger.e('  1. Server is running (python main.py)');
          logger.e('  2. Phone and server are on the same WiFi network');
          logger.e('  3. IP address $baseUrl is correct and reachable');
          logger.e('  4. Firewall is not blocking port 8081');
          return false;
        }
      } catch (e) {
        logger.e('Unexpected error during login: $e');
        return false;
      }
    }

    return false;
  }

  /// Get health status
  Future<bool> checkHealth() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/health'),
      ).timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      logger.e('Health check failed: $e');
      return false;
    }
  }

  /// Get user's emotional state
  Future<Map<String, dynamic>?> getEmotions() async {
    if (userId.isEmpty) return null;

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/user/emotions?user_id=$userId'),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data;
      } else {
        logger.e('Get emotions failed: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      logger.e('Get emotions error: $e');
      return null;
    }
  }

  /// Get WebSocket URL for chat
  String getWebSocketUrl() => '$baseUrl/ws/chat/$userId'.replaceFirst('http', 'ws');
}
