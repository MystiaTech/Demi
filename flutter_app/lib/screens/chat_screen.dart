import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../widgets/message_bubble.dart';
import '../widgets/avatar_display_vrm.dart';
import '../widgets/emotion_display.dart';
import '../widgets/connection_status.dart';
import '../widgets/metrics_drawer.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({Key? key}) : super(key: key);

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late TextEditingController _messageController;
  late ScrollController _scrollController;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  void initState() {
    super.initState();
    _messageController = TextEditingController();
    _scrollController = ScrollController();
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      appBar: AppBar(
        title: const Text('🔮 Demi'),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.menu),
          onPressed: () {
            _scaffoldKey.currentState?.openDrawer();
          },
        ),
        actions: [
          // Metrics button
          IconButton(
            icon: const Icon(Icons.analytics),
            tooltip: 'Status & Metrics',
            onPressed: () {
              _scaffoldKey.currentState?.openEndDrawer();
            },
          ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Center(
              child: Consumer<ChatProvider>(
                builder: (_, provider, __) =>
                    ConnectionStatus(
                      isConnected: provider.isConnected,
                      error: provider.error,
                    ),
              ),
            ),
          ),
        ],
      ),
      // Left drawer - Chat history or settings
      drawer: Drawer(
        child: SafeArea(
          child: Column(
            children: [
              // Header
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Theme.of(context).colorScheme.primary,
                      Theme.of(context).colorScheme.primaryContainer,
                    ],
                  ),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundImage: const AssetImage('assets/images/demi_avatar.png'),
                      backgroundColor: Colors.transparent,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Demi',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            'Your AI Companion',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.8),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              // Menu items
              Expanded(
                child: ListView(
                  padding: EdgeInsets.zero,
                  children: [
                    ListTile(
                      leading: const Icon(Icons.chat),
                      title: const Text('Current Chat'),
                      selected: true,
                      onTap: () {
                        Navigator.pop(context);
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.history),
                      title: const Text('Chat History'),
                      onTap: () {
                        Navigator.pop(context);
                        _showChatHistory(context);
                      },
                    ),
                  ListTile(
                    leading: const Icon(Icons.delete_outline, color: Colors.red),
                    title: const Text('Clear History', style: TextStyle(color: Colors.red)),
                    onTap: () {
                      Navigator.pop(context);
                      _confirmClearHistory(context);
                    },
                  ),
                    const Divider(),
                    ListTile(
                      leading: const Icon(Icons.settings),
                      title: const Text('Settings'),
                      onTap: () {
                        Navigator.pop(context);
                        _showSettings(context);
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.info_outline),
                      title: const Text('About'),
                      onTap: () {
                        Navigator.pop(context);
                        _showAbout(context);
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      // Right drawer - Metrics
      endDrawer: Consumer<ChatProvider>(
        builder: (context, provider, _) => MetricsDrawer(
          apiService: provider.apiService,
        ),
      ),
      body: Consumer<ChatProvider>(
        builder: (context, chatProvider, _) {
          if (chatProvider.isLoading) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (chatProvider.error != null && chatProvider.messages.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Connection Error',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(chatProvider.error ?? 'Unknown error'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => chatProvider.reconnect(),
                    child: const Text('Reconnect'),
                  ),
                ],
              ),
            );
          }

          WidgetsBinding.instance.addPostFrameCallback((_) {
            _scrollToBottom();
          });

          return Column(
            children: [
              // 3D Avatar Display with Lip Sync
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: AvatarDisplayVRM(
                  emotionState: chatProvider.emotionState.toMap(),
                  lipSyncData: chatProvider.currentLipSyncData,
                  isTalking: chatProvider.isAvatarTalking,
                  audioService: chatProvider.audioService,
                  onAvatarInteraction: () {
                    // Pause rotation on tap
                  },
                ),
              ),
              // Messages
              Expanded(
                child: chatProvider.messages.isEmpty
                    ? Center(
                        child: Text(
                          'Start a conversation with Demi! 💬',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(8.0),
                        itemCount: chatProvider.messages.length,
                        itemBuilder: (context, index) {
                          return MessageBubble(
                            message: chatProvider.messages[index],
                          );
                        },
                      ),
              ),
              // Message Input
              Container(
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  border: Border(
                    top: BorderSide(
                      color: Theme.of(context).dividerColor,
                    ),
                  ),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        decoration: InputDecoration(
                          hintText: 'Message Demi...',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(24),
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                        ),
                        maxLines: null,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _sendMessage(context),
                      ),
                    ),
                    const SizedBox(width: 8),
                    FloatingActionButton(
                      mini: true,
                      onPressed: () => _sendMessage(context),
                      child: const Icon(Icons.send),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  void _sendMessage(BuildContext context) {
    final message = _messageController.text.trim();
    if (message.isNotEmpty) {
      context.read<ChatProvider>().sendMessage(message);
      _messageController.clear();
    }
  }

  void _showChatHistory(BuildContext context) {
    final chatProvider = context.read<ChatProvider>();
    
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        height: 400,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Chat History',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Close'),
                ),
              ],
            ),
            const Divider(),
            Expanded(
              child: chatProvider.messages.isEmpty
                  ? const Center(child: Text('No messages yet'))
                  : ListView.builder(
                      itemCount: chatProvider.messages.length,
                      itemBuilder: (context, index) {
                        final msg = chatProvider.messages[index];
                        return ListTile(
                          dense: true,
                          leading: Icon(
                            msg.isDemiMessage ? Icons.smart_toy : Icons.person,
                            size: 20,
                          ),
                          title: Text(
                            msg.content.substring(0, msg.content.length > 50 ? 50 : msg.content.length) + 
                              (msg.content.length > 50 ? '...' : ''),
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(
                            '${msg.from} • ${msg.formattedTime}',
                            style: const TextStyle(fontSize: 12),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmClearHistory(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Chat History'),
        content: const Text('Are you sure you want to clear all messages? This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              context.read<ChatProvider>().clearMessages();
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Chat history cleared')),
              );
            },
            child: const Text('Clear', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  void _showSettings(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Settings'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Server URL: ${ChatProvider.serverUrl}'),
            const SizedBox(height: 8),
            const Text('To change settings, edit the configuration file.'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showAbout(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('About Demi'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Demi v1.0'),
            SizedBox(height: 8),
            Text('Your AI Companion with Emotional Depth'),
            SizedBox(height: 16),
            Text(
              'Features:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            Text('• Real-time chat'),
            Text('• Emotional responses'),
            Text('• Voice synthesis'),
            Text('• 3D avatar with lip sync'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}
