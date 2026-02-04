import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/message.dart';
import '../models/emotion.dart';
import '../models/phoneme_data.dart';
import '../services/api_service.dart';
import '../services/audio_service.dart';
import '../services/websocket_service.dart';

class ChatProvider extends ChangeNotifier {
  // Server URL - change this to match your backend
  // 
  // LOCAL DEVELOPMENT:
  // - Android emulator: 'http://10.0.2.2:8081' (maps to host localhost)
  // - Physical device same WiFi: 'http://192.168.1.245:8081' (your PC's IP)
  //
  // REMOTE ACCESS (via Cloudflare/ngrok):
  // - Cloudflare Tunnel: 'https://demi-api.yourdomain.com'
  // - ngrok: 'https://abc123.ngrok.io' (temporary)
  //
  // See docs/setup/REMOTE_ACCESS.md for remote access setup
  static const String serverUrl = String.fromEnvironment(
    'SERVER_URL',
    defaultValue: 'http://192.168.1.245:8081',  // Change to your server IP/domain
  );

  final ApiService apiService = ApiService(baseUrl: serverUrl);
  final WebSocketService wsService = WebSocketService();
  final AudioService audioService = AudioService();
  final Logger logger = Logger();

  List<Message> messages = [];
  EmotionState emotionState = EmotionState();
  LipSyncData? currentLipSyncData;
  bool isConnected = false;
  bool isLoading = false;
  bool isAvatarTalking = false;
  String? error;
  String? userId;

  static const String _messagesKey = 'chat_messages';
  SharedPreferences? _prefs;

  ChatProvider() {
    initialize();
  }

  /// Load saved messages from local storage
  Future<void> _loadSavedMessages() async {
    try {
      _prefs = await SharedPreferences.getInstance();
      final savedMessages = _prefs?.getStringList(_messagesKey) ?? [];
      
      if (savedMessages.isNotEmpty) {
        messages = savedMessages.map((json) {
          try {
            return Message.fromJson(jsonDecode(json));
          } catch (e) {
            logger.w('Failed to parse message: $e');
            return null;
          }
        }).whereType<Message>().toList();
        
        logger.i('Loaded ${messages.length} saved messages');
        notifyListeners();
      }
    } catch (e) {
      logger.e('Failed to load saved messages: $e');
    }
  }

  /// Save messages to local storage
  Future<void> _saveMessages() async {
    try {
      if (_prefs == null) return;
      
      // Keep only last 100 messages
      final messagesToSave = messages.length > 100 
          ? messages.sublist(messages.length - 100) 
          : messages;
          
      final jsonList = messagesToSave
          .map((m) => jsonEncode(m.toJson()))
          .toList();
          
      await _prefs?.setStringList(_messagesKey, jsonList);
    } catch (e) {
      logger.e('Failed to save messages: $e');
    }
  }

  /// Initialize connection
  Future<void> initialize() async {
    isLoading = true;
    error = null;
    notifyListeners();

    try {
      // Load saved messages first
      await _loadSavedMessages();
      
      // Give backend time to fully initialize
      await Future.delayed(const Duration(seconds: 2));

      // Check health first
      final healthy = await apiService.checkHealth();
      if (!healthy) {
        throw Exception('Server not available');
      }

      // Login
      final loginSuccess = await apiService.login();
      if (!loginSuccess) {
        throw Exception('Login failed');
      }

      userId = apiService.userId;

      // Setup WebSocket callback
      wsService.onMessage = _handleWebSocketMessage;

      // Connect WebSocket
      final wsUrl = apiService.getWebSocketUrl();
      final wsConnected = await wsService.connect(wsUrl);

      if (!wsConnected) {
        throw Exception('WebSocket connection failed');
      }

      isConnected = true;
      isLoading = false;

      // Load initial emotion state
      await loadEmotions();

      logger.i('ChatProvider initialized');
    } catch (e) {
      error = e.toString();
      isLoading = false;
      logger.e('Initialization error: $e');
    }

    notifyListeners();
  }

  /// Handle incoming WebSocket messages
  void _handleWebSocketMessage(Map<String, dynamic> data) {
    final type = data['type'];

    switch (type) {
      case 'connected':
        logger.i('Connected to chat server');
        break;

      case 'typing':
        // Show typing indicator
        logger.i('Demi is typing...');
        break;

      case 'message':
        final content = data['content'] ?? '';
        final timestamp = DateTime.parse(
          data['timestamp'] ?? DateTime.now().toIso8601String(),
        );
        final message = Message(
          content: content,
          from: 'demi',
          timestamp: timestamp,
        );
        messages.add(message);
        _saveMessages(); // Persist messages

        // Handle audio and lip sync data if present
        final audioUrl = data['audioUrl'] as String?;
        final phonemesData = data['phonemes'] as List?;
        final duration = data['duration'] as double?;

        if (audioUrl != null && phonemesData != null && duration != null) {
          // Parse phoneme data
          final phonemes = (phonemesData as List)
              .map((p) => PhonemeFrame.fromJson(p as Map<String, dynamic>))
              .toList();

          // Create lip sync data
          currentLipSyncData = LipSyncData(
            audioUrl: audioUrl,
            phonemes: phonemes,
            duration: duration,
          );

          // Convert relative URL to absolute URL if needed
          final absoluteAudioUrl = _resolveAudioUrl(audioUrl);

          // Play audio (fire and forget - don't block callback)
          audioService.playFromUrl(
            absoluteAudioUrl,
            onComplete: () {
              isAvatarTalking = false;
              notifyListeners();
            },
            onError: (error) {
              logger.e('Audio playback error: $error');
            },
          );

          isAvatarTalking = true;
        }

        logger.i('Received message: $content');
        notifyListeners();
        break;

      case 'emotions':
        final emotions = data['emotions'] ?? {};
        emotionState = EmotionState.fromJson(emotions);
        logger.i('Emotions updated: ${emotionState.dominantEmotion}');
        notifyListeners();
        break;

      case 'error':
        error = data['content'] ?? 'Unknown error';
        logger.e('Server error: $error');
        notifyListeners();
        break;

      default:
        logger.w('Unknown message type: $type');
    }
  }

  /// Send a message
  Future<void> sendMessage(String content) async {
    if (content.trim().isEmpty) return;

    try {
      // Add user message to list
      final userMessage = Message(
        content: content,
        from: 'user',
        timestamp: DateTime.now(),
      );
      messages.add(userMessage);
      _saveMessages(); // Persist messages

      // Send through WebSocket
      wsService.sendMessage(content);

      notifyListeners();
    } catch (e) {
      error = 'Failed to send message: $e';
      logger.e('Send message error: $e');
      notifyListeners();
    }
  }

  /// Load emotional state
  Future<void> loadEmotions() async {
    try {
      final emotionData = await apiService.getEmotions();
      if (emotionData != null) {
        final emotions = emotionData['emotions'] ?? {};
        emotionState = EmotionState.fromJson(emotions);
        notifyListeners();
      }
    } catch (e) {
      logger.e('Load emotions error: $e');
    }
  }

  /// Reconnect to server
  Future<void> reconnect() async {
    try {
      isLoading = true;
      error = null;
      notifyListeners();

      // If userId not set, need to re-initialize first
      if (userId == null) {
        logger.i('UserId not set, running full initialization');
        await initialize();
        return;
      }

      final wsUrl = apiService.getWebSocketUrl();
      final success = await wsService.reconnect(wsUrl);

      if (success) {
        isConnected = true;
        isLoading = false;
        await loadEmotions();
      } else {
        throw Exception('Reconnection failed');
      }
    } catch (e) {
      error = 'Reconnection failed: $e';
      isLoading = false;
      logger.e('Reconnect error: $e');
    }

    notifyListeners();
  }

  /// Resolves audio URL to absolute URL
  String _resolveAudioUrl(String url) {
    if (url.startsWith('http')) {
      return url;
    }
    // Relative URL - resolve against API base URL
    final baseUrl = apiService.baseUrl;
    return '$baseUrl$url';
  }

  /// Clear messages
  void clearMessages() {
    messages.clear();
    currentLipSyncData = null;
    isAvatarTalking = false;
    notifyListeners();
  }

  /// Disconnect
  void disconnect() {
    wsService.disconnect();
    audioService.stop();
    isConnected = false;
    isAvatarTalking = false;
    notifyListeners();
  }

  @override
  void dispose() {
    disconnect();
    audioService.dispose();
    super.dispose();
  }
}
