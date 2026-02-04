/// VRM Avatar display widget using WebView + Three.js
///
/// Renders the VRM model in a WebView using Three.js and @pixiv/three-vrm
/// Supports expressions, blinking, and emotion-based reactions

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../models/avatar_state.dart';
import '../models/phoneme_data.dart';
import '../services/audio_service.dart';

/// VRM avatar display widget using WebView-based Three.js rendering
class AvatarDisplayVRM extends StatefulWidget {
  /// Emotion state to display
  final Map<String, double> emotionState;

  /// Lip sync data (if available)
  final LipSyncData? lipSyncData;

  /// Whether avatar is currently talking
  final bool isTalking;

  /// Audio service for playback control
  final AudioService audioService;

  /// Callback when avatar interactions occur
  final VoidCallback? onAvatarInteraction;

  const AvatarDisplayVRM({
    Key? key,
    required this.emotionState,
    this.lipSyncData,
    this.isTalking = false,
    required this.audioService,
    this.onAvatarInteraction,
  }) : super(key: key);

  @override
  State<AvatarDisplayVRM> createState() => _AvatarDisplayVRMState();
}

class _AvatarDisplayVRMState extends State<AvatarDisplayVRM> {
  late WebViewController _webViewController;
  bool _isLoading = true;
  bool _hasError = false;
  String _loadingMessage = 'Summoning Demi...';

  @override
  void initState() {
    super.initState();
    _initWebView();
  }

  void _initWebView() {
    _webViewController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.transparent)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (String url) {
            setState(() {
              _isLoading = true;
            });
          },
          onPageFinished: (String url) {
            setState(() {
              _isLoading = false;
            });
            // Send initial expression after load
            _updateExpression();
          },
          onWebResourceError: (WebResourceError error) {
            setState(() {
              _hasError = true;
              _isLoading = false;
            });
          },
        ),
      )
      ..addJavaScriptChannel(
        'FlutterVRM',
        onMessageReceived: (JavaScriptMessage message) {
          if (message.message == 'loaded') {
            setState(() {
              _isLoading = false;
            });
          }
        },
      )
      ..loadFlutterAsset('assets/vrm_viewer/vrm_viewer.html');
  }

  @override
  void didUpdateWidget(AvatarDisplayVRM oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    // Update expression when emotion state changes
    if (oldWidget.emotionState != widget.emotionState) {
      _updateExpression();
    }
    
    // Handle talking state
    if (oldWidget.isTalking != widget.isTalking) {
      if (widget.isTalking) {
        _setExpression('happy', 0.3); // Slight smile when talking
      } else {
        _updateExpression(); // Return to emotion-based expression
      }
    }
  }

  void _updateExpression() {
    if (widget.emotionState.isEmpty) {
      _setExpression('neutral', 0);
      return;
    }

    // Find dominant emotion
    double maxIntensity = 0.0;
    String dominantEmotion = 'neutral';

    widget.emotionState.forEach((emotion, intensity) {
      if (intensity > maxIntensity) {
        maxIntensity = intensity;
        dominantEmotion = emotion;
      }
    });

    // Map emotion to VRM expression
    final expressionMap = {
      'excitement': 'happy',
      'affection': 'happy',
      'loneliness': 'sad',
      'vulnerability': 'sad',
      'frustration': 'angry',
      'jealousy': 'angry',
      'curiosity': 'surprised',
      'confidence': 'relaxed',
    };

    final expression = expressionMap[dominantEmotion.toLowerCase()] ?? 'neutral';
    _setExpression(expression, maxIntensity.clamp(0.0, 1.0));
  }

  void _setExpression(String expression, double value) {
    final command = jsonEncode({
      'type': 'setExpression',
      'expression': expression,
      'value': value,
    });
    
    _webViewController.runJavaScript(
      "handleCommand($command);"
    );
  }

  void _setAutoRotate(bool enabled) {
    final command = jsonEncode({
      'type': 'setAutoRotate',
      'enabled': enabled,
    });
    
    _webViewController.runJavaScript(
      "handleCommand($command);"
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 320,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.black.withOpacity(0.3),
            Colors.black.withOpacity(0.1),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: _getEmotionColor().withOpacity(0.5),
          width: 2,
        ),
        boxShadow: [
          BoxShadow(
            color: _getEmotionColor().withOpacity(0.3),
            blurRadius: 20,
            spreadRadius: 2,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          fit: StackFit.expand,
          children: [
            // WebView with VRM
            WebViewWidget(controller: _webViewController),

            // Loading overlay
            if (_isLoading)
              Container(
                color: Colors.black54,
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const CircularProgressIndicator(
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.purple),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _loadingMessage,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // Error overlay
            if (_hasError)
              Container(
                color: Colors.black87,
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.error_outline,
                        color: Colors.red,
                        size: 48,
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Failed to load avatar',
                        style: TextStyle(color: Colors.white),
                      ),
                      TextButton(
                        onPressed: () {
                          setState(() {
                            _hasError = false;
                            _isLoading = true;
                          });
                          _webViewController.reload();
                        },
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ),

            // Status indicator
            Positioned(
              top: 12,
              right: 12,
              child: _buildStatusIndicator(),
            ),

            // Emotion indicator
            Positioned(
              top: 12,
              left: 12,
              child: _buildEmotionIndicator(),
            ),

            // Gesture detector for interactions
            Positioned.fill(
              child: GestureDetector(
                onTap: () {
                  widget.onAvatarInteraction?.call();
                  _setAutoRotate(false); // Stop rotation on interaction
                  
                  // Resume rotation after 3 seconds
                  Future.delayed(const Duration(seconds: 3), () {
                    if (mounted) {
                      _setAutoRotate(true);
                    }
                  });
                },
                behavior: HitTestBehavior.translucent,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getEmotionColor() {
    if (widget.emotionState.isEmpty) return Colors.purple;

    double maxIntensity = 0.0;
    String dominantEmotion = 'neutral';

    widget.emotionState.forEach((emotion, intensity) {
      if (intensity > maxIntensity) {
        maxIntensity = intensity;
        dominantEmotion = emotion;
      }
    });

    switch (dominantEmotion.toLowerCase()) {
      case 'excitement':
      case 'affection':
        return Colors.pink;
      case 'frustration':
      case 'anger':
      case 'jealousy':
        return Colors.red;
      case 'loneliness':
      case 'vulnerability':
      case 'sadness':
        return Colors.blue;
      case 'curiosity':
        return Colors.green;
      case 'confidence':
        return Colors.purple;
      default:
        return Colors.purple;
    }
  }

  Widget _buildStatusIndicator() {
    if (!widget.isTalking) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.5),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.circle, color: Colors.green, size: 8),
            SizedBox(width: 4),
            Text('Online', style: TextStyle(color: Colors.white, fontSize: 10)),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.green.withOpacity(0.8),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
            ),
          ),
          SizedBox(width: 6),
          Text('Speaking', style: TextStyle(color: Colors.white, fontSize: 10)),
        ],
      ),
    );
  }

  Widget _buildEmotionIndicator() {
    if (widget.emotionState.isEmpty) return const SizedBox.shrink();

    double maxIntensity = 0.0;
    String dominantEmotion = '';

    widget.emotionState.forEach((emotion, intensity) {
      if (intensity > maxIntensity && intensity > 0.3) {
        maxIntensity = intensity;
        dominantEmotion = emotion;
      }
    });

    if (dominantEmotion.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _getEmotionColor().withOpacity(0.7),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        dominantEmotion.substring(0, 1).toUpperCase() + dominantEmotion.substring(1),
        style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w500),
      ),
    );
  }

  @override
  void dispose() {
    super.dispose();
  }
}
