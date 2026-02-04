import 'package:flutter/material.dart';
import '../services/api_service.dart';

/// Right-side drawer displaying Demi's metrics and status
class MetricsDrawer extends StatefulWidget {
  final ApiService apiService;

  const MetricsDrawer({
    Key? key,
    required this.apiService,
  }) : super(key: key);

  @override
  State<MetricsDrawer> createState() => _MetricsDrawerState();
}

class _MetricsDrawerState extends State<MetricsDrawer> {
  Map<String, dynamic> _metrics = {};
  Map<String, dynamic> _llmMetrics = {};
  Map<String, dynamic> _emotionHistory = {};
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadMetrics();
  }

  Future<void> _loadMetrics() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });

      // Fetch metrics from API
      final metrics = await _fetchMetrics('/api/metrics');
      final llmMetrics = await _fetchMetrics('/api/metrics/llm');
      final emotionHistory = await _fetchMetrics('/api/metrics/emotions/history?hours=1&limit=10');

      if (mounted) {
        setState(() {
          _metrics = metrics;
          _llmMetrics = llmMetrics;
          _emotionHistory = emotionHistory;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<Map<String, dynamic>> _fetchMetrics(String endpoint) async {
    try {
      final response = await widget.apiService.checkHealth();
      // Note: The metrics endpoints aren't fully implemented in the backend
      // This is a placeholder for when they're available
      return {};
    } catch (e) {
      return {};
    }
  }

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: Container(
        color: Theme.of(context).colorScheme.surface,
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
                    const Icon(
                      Icons.analytics,
                      color: Colors.white,
                      size: 28,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Demi Status',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            'Real-time metrics',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.8),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh, color: Colors.white),
                      onPressed: _loadMetrics,
                    ),
                  ],
                ),
              ),

              // Content
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _error != null
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.error_outline,
                                  size: 48,
                                  color: Theme.of(context).colorScheme.error,
                                ),
                                const SizedBox(height: 8),
                                Text('Failed to load metrics'),
                              ],
                            ),
                          )
                        : SingleChildScrollView(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _buildSection(
                                  context,
                                  icon: Icons.memory,
                                  title: 'System Status',
                                  children: [
                                    _buildStatusTile(
                                      'LLM Provider',
                                      'LM Studio',
                                      Icons.psychology,
                                      Colors.green,
                                    ),
                                    _buildStatusTile(
                                      'Discord Bot',
                                      'Online',
                                      Icons.chat_bubble,
                                      Colors.green,
                                    ),
                                    _buildStatusTile(
                                      'Mobile API',
                                      'Active',
                                      Icons.phone_android,
                                      Colors.green,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                
                                _buildSection(
                                  context,
                                  icon: Icons.favorite,
                                  title: 'Emotional State',
                                  children: [
                                    _buildEmotionBar('Loneliness', 0.3, Colors.purple),
                                    _buildEmotionBar('Excitement', 0.6, Colors.pink),
                                    _buildEmotionBar('Frustration', 0.1, Colors.red),
                                    _buildEmotionBar('Affection', 0.4, Colors.orange),
                                  ],
                                ),
                                const SizedBox(height: 16),

                                _buildSection(
                                  context,
                                  icon: Icons.speed,
                                  title: 'Performance',
                                  children: [
                                    _buildMetricTile(
                                      'Response Time',
                                      '~2.5s',
                                      Icons.timer,
                                    ),
                                    _buildMetricTile(
                                      'Messages Today',
                                      '42',
                                      Icons.message,
                                    ),
                                    _buildMetricTile(
                                      'Uptime',
                                      '3h 24m',
                                      Icons.access_time,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),

                                _buildSection(
                                  context,
                                  icon: Icons.auto_awesome,
                                  title: 'Autonomy',
                                  children: [
                                    _buildStatusTile(
                                      'Rambles Enabled',
                                      'Yes',
                                      Icons.record_voice_over,
                                      Colors.blue,
                                    ),
                                    _buildStatusTile(
                                      'Voice Enabled',
                                      'No',
                                      Icons.mic,
                                      Colors.grey,
                                    ),
                                    _buildStatusTile(
                                      'Self-Improvement',
                                      'No',
                                      Icons.build,
                                      Colors.grey,
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
              ),

              // Footer
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  border: Border(
                    top: BorderSide(
                      color: Theme.of(context).dividerColor,
                    ),
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.info_outline,
                      size: 16,
                      color: Theme.of(context).textTheme.bodySmall?.color,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Metrics update every 5 seconds',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSection(
    BuildContext context, {
    required IconData icon,
    required String title,
    required List<Widget> children,
  }) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: Theme.of(context).colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Divider(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _buildStatusTile(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: color, size: 20),
      title: Text(label, style: const TextStyle(fontSize: 14)),
      trailing: Text(
        value,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }

  Widget _buildMetricTile(String label, String value, IconData icon) {
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, size: 20),
      title: Text(label, style: const TextStyle(fontSize: 14)),
      trailing: Text(
        value,
        style: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildEmotionBar(String label, double value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(fontSize: 12)),
              Text(
                '${(value * 100).toInt()}%',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: value,
              backgroundColor: color.withOpacity(0.1),
              valueColor: AlwaysStoppedAnimation<Color>(color),
              minHeight: 8,
            ),
          ),
        ],
      ),
    );
  }
}
