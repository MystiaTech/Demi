import 'package:flutter/material.dart';
import '../providers/chat_provider.dart';

class ConnectionStatus extends StatelessWidget {
  final bool isConnected;
  final String? error;

  const ConnectionStatus({
    Key? key,
    required this.isConnected,
    this.error,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: error != null ? () => _showErrorDetails(context) : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isConnected 
            ? Colors.green.withOpacity(0.2) 
            : Colors.red.withOpacity(0.2),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isConnected ? Colors.green : Colors.red,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: isConnected ? Colors.green : Colors.red,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              isConnected ? 'Connected' : (error != null ? 'Tap for details' : 'Offline'),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: isConnected ? Colors.green : Colors.red,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showErrorDetails(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Connection Error'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Error:',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(error ?? 'Unknown error'),
              const SizedBox(height: 16),
              Text(
                'Server URL:',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              SelectableText(ChatProvider.serverUrl),
              const SizedBox(height: 16),
              Text(
                'Troubleshooting:',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              const Text('1. Ensure server is running: python main.py'),
              const Text('2. Check phone and server are on same WiFi'),
              const Text('3. Verify server URL in chat_provider.dart'),
              const Text('4. Check firewall settings (port 8081)'),
              const SizedBox(height: 8),
              Text(
                'To change server URL, edit:',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SelectableText(
                'lib/providers/chat_provider.dart',
                style: TextStyle(fontFamily: 'monospace'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}
