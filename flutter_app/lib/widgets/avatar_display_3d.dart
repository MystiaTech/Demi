/// Avatar display widget for Demi.
///
/// Shows a 3D VRM model with lip sync animation if available,
/// otherwise falls back to the Demi image with visual effects.
/// Uses flutter_3d_controller for 3D rendering and audioplayers for audio playback.

import 'package:flutter/material.dart';
import 'package:demi_mobile/models/avatar_state.dart';
import 'package:demi_mobile/models/phoneme_data.dart';
import 'package:demi_mobile/controllers/avatar_controller.dart';
import 'package:demi_mobile/services/audio_service.dart';

/// Avatar display widget with 3D/2D fallback
class AvatarDisplay3D extends StatefulWidget {
  /// Emotion state to display
  final Map<String, double> emotionState;

  /// Lip sync data (if available)
  final LipSyncData? lipSyncData;

  /// Whether avatar is currently talking
  final bool isTalking;

  /// Audio service for playback control
  final AudioService audioService;

  /// Model path (VRM file in assets)
  final String modelPath;

  /// Callback when avatar interactions occur
  final VoidCallback? onAvatarInteraction;

  /// Creates a new AvatarDisplay3D widget
  const AvatarDisplay3D({
    Key? key,
    required this.emotionState,
    this.lipSyncData,
    this.isTalking = false,
    required this.audioService,
    this.modelPath = 'assets/models/Demi_.vrm',
    this.onAvatarInteraction,
  }) : super(key: key);

  @override
  State<AvatarDisplay3D> createState() => _AvatarDisplay3DState();
}

class _AvatarDisplay3DState extends State<AvatarDisplay3D>
    with TickerProviderStateMixin {
  late AvatarController _avatarController;

  /// Loading state
  bool _isLoading = true;
  bool _use3D = false;  // Set to true if 3D loads successfully
  String _loadingMessage = 'Loading avatar...';

  /// Current viseme for lip sync
  String _currentViseme = 'neutral';
  double _visemeIntensity = 0.0;

  /// Animation controllers for effects
  late AnimationController _breathingController;
  late AnimationController _glowController;
  late AnimationController _talkController;

  @override
  void initState() {
    super.initState();

    // Initialize animation controllers
    _breathingController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat(reverse: true);

    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    _talkController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
    );

    // Initialize audio service
    _avatarController = AvatarController(
      audioService: widget.audioService,
    );

    // Setup animation callbacks
    _avatarController.onVisemeChanged = _onVisemeChanged;
    _avatarController.onExpressionChanged = _onExpressionChanged;
    _avatarController.onIdleAnimation = _onIdleAnimation;

    // Initialize animation loop
    _avatarController.initialize(this);

    // Simulate loading (3D models take time to load)
    Future.delayed(const Duration(milliseconds: 500), () {
      if (mounted) {
        setState(() {
          _isLoading = false;
          // VRM loading not fully supported by flutter_3d_controller
          // Use 2D image with effects instead
          _use3D = false;
        });
      }
    });

    // Update expression based on emotion state
    _updateExpression();

    // Set initial lip sync data
    if (widget.lipSyncData != null) {
      _avatarController.setLipSyncData(widget.lipSyncData!);
    }
  }

  /// Called when viseme (mouth shape) should change
  void _onVisemeChanged(String viseme, double weight) {
    setState(() {
      _currentViseme = viseme;
      _visemeIntensity = weight;
    });

    // Animate talking indicator
    if (weight > 0.3) {
      _talkController.forward(from: 0);
    }
  }

  /// Called when expression should change
  void _onExpressionChanged(String expression, double intensity) {
    // Update visual effects based on expression
    setState(() {});
  }

  /// Called for idle animation updates (breathing, blinking)
  void _onIdleAnimation(double breathing, double blinking) {
    // Handled by animation controllers
  }

  /// Updates expression based on emotion state
  void _updateExpression() {
    if (widget.emotionState.isEmpty) {
      _avatarController.setExpression(AvatarExpression.neutral);
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

    // Map emotion to expression
    final expression = _mapEmotionToExpression(dominantEmotion);
    _avatarController.setExpression(expression, intensity: maxIntensity);
  }

  /// Maps emotion name to avatar expression
  AvatarExpression _mapEmotionToExpression(String emotion) {
    const emotionMap = {
      'loneliness': AvatarExpression.sad,
      'vulnerability': AvatarExpression.sad,
      'excitement': AvatarExpression.happy,
      'affection': AvatarExpression.happy,
      'frustration': AvatarExpression.angry,
      'jealousy': AvatarExpression.angry,
      'defensiveness': AvatarExpression.angry,
      'curiosity': AvatarExpression.surprised,
      'confidence': AvatarExpression.neutral,
    };

    return emotionMap[emotion.toLowerCase()] ?? AvatarExpression.neutral;
  }

  /// Get emotion color based on current state
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

  @override
  void didUpdateWidget(AvatarDisplay3D oldWidget) {
    super.didUpdateWidget(oldWidget);

    // Update expression if emotion state changed
    if (oldWidget.emotionState != widget.emotionState) {
      _updateExpression();
    }

    // Update lip sync data if changed
    if (oldWidget.lipSyncData != widget.lipSyncData &&
        widget.lipSyncData != null) {
      _avatarController.setLipSyncData(widget.lipSyncData!);
    }

    // Update talking state if changed
    if (oldWidget.isTalking != widget.isTalking) {
      if (!widget.isTalking) {
        _avatarController.reset();
      }
    }
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
            // Avatar image with effects
            _buildAvatarView(),

            // Loading overlay
            if (_isLoading)
              Container(
                color: Colors.black54,
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const CircularProgressIndicator(
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
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

            // Emotion glow effect
            AnimatedBuilder(
              animation: _glowController,
              builder: (context, child) {
                return Container(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: Alignment.center,
                      radius: 0.8 + (_glowController.value * 0.2),
                      colors: [
                        _getEmotionColor().withOpacity(0.1 + (_glowController.value * 0.1)),
                        Colors.transparent,
                      ],
                    ),
                  ),
                );
              },
            ),

            // Lip sync overlay (when talking)
            if (widget.isTalking) _buildLipSyncOverlay(),

            // Status indicator (talking/idle)
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
          ],
        ),
      ),
    );
  }

  /// Builds the avatar view (2D image with effects)
  Widget _buildAvatarView() {
    return GestureDetector(
      onTap: () {
        widget.onAvatarInteraction?.call();
      },
      child: AnimatedBuilder(
        animation: _breathingController,
        builder: (context, child) {
          // Breathing animation - subtle scale
          final scale = 1.0 + (_breathingController.value * 0.02);

          return Transform.scale(
            scale: scale,
            child: Container(
              decoration: BoxDecoration(
                image: DecorationImage(
                  image: const AssetImage('assets/images/demi_avatar.png'),
                  fit: BoxFit.cover,
                  alignment: Alignment.topCenter,
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  /// Builds lip sync visualization overlay
  Widget _buildLipSyncOverlay() {
    // Map viseme to visual indicator
    final visemeColors = {
      'aa': Colors.red,
      'ih': Colors.orange,
      'ou': Colors.yellow,
      'E': Colors.green,
      'neutral': Colors.transparent,
    };

    final color = visemeColors[_currentViseme] ?? Colors.transparent;
    final intensity = _visemeIntensity.clamp(0.0, 1.0);

    return Positioned(
      bottom: 40,
      left: 0,
      right: 0,
      child: Center(
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 50),
          width: 60 + (intensity * 40),
          height: 20 + (intensity * 30),
          decoration: BoxDecoration(
            color: color.withOpacity(intensity * 0.5),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(intensity * 0.8),
                blurRadius: 20,
                spreadRadius: 5,
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Builds status indicator (showing if avatar is talking)
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
            Icon(
              Icons.circle,
              color: Colors.green,
              size: 8,
            ),
            SizedBox(width: 4),
            Text(
              'Online',
              style: TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
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
          Text(
            'Speaking',
            style: TextStyle(
              color: Colors.white,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// Builds emotion indicator
  Widget _buildEmotionIndicator() {
    if (widget.emotionState.isEmpty) return const SizedBox.shrink();

    // Find dominant emotion
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
        style: const TextStyle(
          color: Colors.white,
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _breathingController.dispose();
    _glowController.dispose();
    _talkController.dispose();
    _avatarController.dispose();
    super.dispose();
  }
}
