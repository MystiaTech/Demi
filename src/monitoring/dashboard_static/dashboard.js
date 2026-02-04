/**
 * Demi Health Dashboard - Real-time updates and visualization
 */

class DemiDashboard {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.updateInterval = null;
        this.memoryHistory = [];
        this.responseTimeHistory = [];
        this.maxHistoryPoints = 120; // 10 minutes at 5s intervals
        this._metricsInterval = null;
        this._metricsIntervalActive = false;
        this.emotionColors = {
            loneliness: '#ff6b6b',
            excitement: '#4ecdc4',
            frustration: '#ffe66d',
            jealousy: '#95e1d3',
            vulnerability: '#f38181',
            confidence: '#a8e6cf',
            curiosity: '#c7ceea',
            affection: '#ffd3b6',
            defensiveness: '#ffaaa5'
        };
        this.emotions = ['loneliness', 'excitement', 'frustration', 'jealousy', 'vulnerability',
                        'confidence', 'curiosity', 'affection', 'defensiveness'];

        this.init();
    }

    init() {
        this.setupTheme();
        this.connectWebSocket();
        this.setupEventListeners();
        this.fetchInitialData();
        this.initEmotionLegend();
        this.startMetricsUpdates();
    }

    startMetricsUpdates() {
        // Update specialized metrics every 5 seconds
        // Only run once - prevent multiple intervals
        if (this._metricsIntervalActive) return;
        this._metricsIntervalActive = true;

        this._metricsInterval = setInterval(() => {
            this.fetchLLMMetrics();
            this.fetchPlatformMetrics();
            this.fetchConversationMetrics();
            this.fetchEmotionHistory();
            this.fetchDiscordStatus();
        }, 5000);
    }

    stopMetricsUpdates() {
        if (this._metricsInterval) {
            clearInterval(this._metricsInterval);
            this._metricsIntervalActive = false;
        }
    }

    setupTheme() {
        // Check for saved theme or default to dark
        const savedTheme = localStorage.getItem('demi-dashboard-theme');
        const theme = savedTheme || 'dark';

        // Apply theme
        this.setTheme(theme);

        // Setup theme toggle button with retry logic
        const setupToggleButton = () => {
            const toggleBtn = document.getElementById('theme-toggle');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleTheme();
                });
                console.log('Theme toggle button attached');
            } else {
                console.warn('Theme toggle button not found, retrying...');
                setTimeout(setupToggleButton, 100);
            }
        };

        setupToggleButton();
    }

    setTheme(theme) {
        const html = document.documentElement;

        if (theme === 'dark') {
            html.setAttribute('data-theme', 'dark');
            localStorage.setItem('demi-dashboard-theme', 'dark');
        } else {
            html.removeAttribute('data-theme');
            localStorage.setItem('demi-dashboard-theme', 'light');
        }

        // Update icon
        const icon = document.getElementById('theme-icon');
        if (icon) {
            icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }

    toggleTheme() {
        const html = document.documentElement;
        const isDark = html.getAttribute('data-theme') === 'dark';
        this.setTheme(isDark ? 'light' : 'dark');
    }

    connectWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus('connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus('disconnected');

            // Attempt to reconnect
            setTimeout(() => this.connectWebSocket(), this.reconnectInterval);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
        };
    }

    updateConnectionStatus(status) {
        const statusEl = document.getElementById('connection-status');
        const wsStatusEl = document.getElementById('websocket-status');

        const statusMap = {
            'connected': { text: '● Live', class: 'connected' },
            'disconnected': { text: '○ Disconnected', class: 'disconnected' },
            'connecting': { text: '⋯ Connecting', class: 'connecting' },
            'error': { text: '✕ Error', class: 'error' },
        };

        const statusInfo = statusMap[status] || statusMap['disconnected'];

        if (statusEl) {
            statusEl.textContent = statusInfo.text;
            statusEl.className = `connection-status ${statusInfo.class}`;
        }

        if (wsStatusEl) {
            wsStatusEl.textContent = statusInfo.text;
        }
    }

    handleMessage(data) {
        if (data.type === 'update') {
            this.updateMetrics(data.metrics);
            this.updateEmotions(data.emotions);
            if (data.alerts) {
                this.updateAlerts(data.alerts);
            }
            this.updateTimestamp(data.timestamp);
            // Fetch mobile metrics with each update
            this.fetchMobileMetrics();
        } else if (data.type === 'alert') {
            this.addAlert(data.alert);
        } else if (data.type === 'pong') {
            // Keepalive response
        }
    }

    async fetchInitialData() {
        try {
            // Fetch health status
            const healthRes = await fetch('/api/health');
            if (healthRes.ok) {
                const health = await healthRes.json();
                this.updateHealthStatus(health);
            }

            // Fetch emotions
            const emotionsRes = await fetch('/api/emotions');
            if (emotionsRes.ok) {
                const emotions = await emotionsRes.json();
                this.updateEmotions(emotions);
            }

            // Fetch alerts
            const alertsRes = await fetch('/api/alerts?active_only=true');
            if (alertsRes.ok) {
                const alerts = await alertsRes.json();
                this.updateAlerts(alerts.alerts);
            }

            // Fetch platforms
            const platformsRes = await fetch('/api/platforms');
            if (platformsRes.ok) {
                const platforms = await platformsRes.json();
                this.updatePlatforms(platforms.platforms);
            }

            // Fetch mobile metrics
            this.fetchMobileMetrics();

        } catch (error) {
            console.error('Failed to fetch initial data:', error);
        }
    }

    async fetchMobileMetrics() {
        try {
            const metricsRes = await fetch('http://localhost:8081/api/metrics');
            if (metricsRes.ok) {
                const metrics = await metricsRes.json();
                this.updateMobileMetrics(metrics);
            } else {
                this.updateMobileMetrics({ status: 'offline', active_connections: 0, total_sessions: 0 });
            }
        } catch (error) {
            console.warn('Failed to fetch mobile metrics:', error);
            this.updateMobileMetrics({ status: 'offline', active_connections: 0, total_sessions: 0 });
        }
    }

    updateMobileMetrics(metrics) {
        const connectionsEl = document.getElementById('mobile-connections');
        const sessionsEl = document.getElementById('mobile-sessions');
        const statusEl = document.getElementById('mobile-status');
        const detailsEl = document.getElementById('mobile-details');

        if (connectionsEl) {
            connectionsEl.textContent = metrics.active_connections || 0;
        }

        if (sessionsEl) {
            sessionsEl.textContent = metrics.total_sessions || 0;
        }

        if (statusEl) {
            const isHealthy = metrics.status === 'healthy';
            statusEl.textContent = isHealthy ? '✅ Healthy' : '⚠️ Offline';
            statusEl.style.color = isHealthy ? '#4ecdc4' : '#ff6b6b';
        }

        if (detailsEl && metrics.connections && metrics.connections.length > 0) {
            const connectionList = metrics.connections.map(conn => `<div>👤 ${conn}</div>`).join('');
            detailsEl.innerHTML = `<strong>Connected Users:</strong><div style="margin-top: 8px;">${connectionList}</div>`;
        } else if (detailsEl) {
            detailsEl.innerHTML = '<em>No active connections</em>';
        }
    }

    updateMetrics(metrics) {
        if (!metrics || metrics.error) return;

        // Update memory
        const memoryPercent = metrics.memory_percent || 0;
        const memoryBar = document.getElementById('memory-bar');
        const memoryValue = document.getElementById('memory-value');
        const memoryUsed = document.getElementById('memory-used');
        const memoryAvailable = document.getElementById('memory-available');
        const memoryTotal = document.getElementById('memory-total');

        if (memoryBar) {
            memoryBar.style.width = `${Math.min(memoryPercent, 100)}%`;
            memoryBar.className = 'metric-fill';
            if (memoryPercent > 90) memoryBar.classList.add('critical');
            else if (memoryPercent > 80) memoryBar.classList.add('warning');
        }

        if (memoryValue) memoryValue.textContent = `${memoryPercent.toFixed(1)}%`;
        if (memoryUsed) memoryUsed.textContent = (metrics.memory_used_gb || 0).toFixed(2);
        if (memoryAvailable) memoryAvailable.textContent = (metrics.memory_available_gb || 0).toFixed(2);
        if (memoryTotal) memoryTotal.textContent = (metrics.memory_total_gb || 0).toFixed(2);

        // Update CPU
        const cpuPercent = metrics.cpu_percent || 0;
        const cpuBar = document.getElementById('cpu-bar');
        const cpuValue = document.getElementById('cpu-value');

        if (cpuBar) {
            cpuBar.style.width = `${Math.min(cpuPercent, 100)}%`;
            cpuBar.className = 'metric-fill';
            if (cpuPercent > 90) cpuBar.classList.add('critical');
            else if (cpuPercent > 80) cpuBar.classList.add('warning');
        }

        if (cpuValue) cpuValue.textContent = `${cpuPercent.toFixed(1)}%`;

        // Update Disk
        const diskPercent = metrics.disk_percent || 0;
        const diskBar = document.getElementById('disk-bar');
        const diskValue = document.getElementById('disk-value');

        if (diskBar) {
            diskBar.style.width = `${Math.min(diskPercent, 100)}%`;
            diskBar.className = 'metric-fill';
            if (diskPercent > 90) diskBar.classList.add('critical');
            else if (diskPercent > 80) diskBar.classList.add('warning');
        }

        if (diskValue) diskValue.textContent = `${diskPercent.toFixed(1)}%`;

        // Update history charts
        this.updateMemoryHistory(metrics.memory_used_gb || 0);
        this.updateResponseTimeHistory(metrics.response_time_p90 || 0);

        // Update health status based on metrics
        this.updateHealthFromMetrics(metrics);
    }

    updateHealthFromMetrics(metrics) {
        const healthStatus = document.getElementById('health-status');
        const healthGrid = document.getElementById('health-grid');

        let status = 'healthy';
        if (metrics.memory_percent > 90 || metrics.cpu_percent > 90) {
            status = 'critical';
        } else if (metrics.memory_percent > 80 || metrics.cpu_percent > 80) {
            status = 'warning';
        }

        if (healthStatus) {
            healthStatus.textContent = status.toUpperCase();
            healthStatus.className = `value status-${status}`;
        }

        // Update health items styling
        if (healthGrid) {
            const items = healthGrid.querySelectorAll('.health-item');
            items.forEach(item => {
                item.className = 'health-item';
                item.classList.add(status);
            });
        }
    }

    updateHealthStatus(health) {
        const healthStatus = document.getElementById('health-status');
        const healthGrid = document.getElementById('health-grid');

        if (healthStatus && health.status) {
            healthStatus.textContent = health.status.toUpperCase();
            healthStatus.className = `value status-${health.status}`;
        }

        // Update health items styling
        if (healthGrid) {
            const items = healthGrid.querySelectorAll('.health-item');
            items.forEach(item => {
                item.className = 'health-item';
                item.classList.add(health.status);
            });
        }

        // Update alert count
        if (health.alerts_count > 0) {
            document.getElementById('alert-count').textContent = `(${health.alerts_count})`;
        }
    }

    updateMemoryHistory(memoryGb) {
        this.memoryHistory.push({
            time: new Date(),
            value: memoryGb
        });

        if (this.memoryHistory.length > this.maxHistoryPoints) {
            this.memoryHistory.shift();
        }

        this.drawMemoryChart();
    }

    updateResponseTimeHistory(responseTime) {
        this.responseTimeHistory.push({
            time: new Date(),
            value: responseTime
        });

        if (this.responseTimeHistory.length > this.maxHistoryPoints) {
            this.responseTimeHistory.shift();
        }

        this.drawResponseChart();
    }

    drawMemoryChart() {
        const canvas = document.getElementById('memory-chart');
        if (!canvas || this.memoryHistory.length < 2) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Find min/max for scaling
        const values = this.memoryHistory.map(h => h.value);
        const min = Math.max(0, Math.min(...values) * 0.9);
        const max = Math.max(...values) * 1.1;
        const range = max - min || 1;

        // Draw grid
        ctx.strokeStyle = '#eee';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = height - padding - (i / 4) * (height - 2 * padding);
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - 10, y);
            ctx.stroke();

            // Y-axis labels
            ctx.fillStyle = '#666';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'right';
            const label = (min + (i / 4) * range).toFixed(1);
            ctx.fillText(`${label}GB`, padding - 5, y + 3);
        }

        // Draw line
        ctx.strokeStyle = '#4a90d9';
        ctx.lineWidth = 2;
        ctx.beginPath();

        this.memoryHistory.forEach((point, index) => {
            const x = padding + (index / (this.maxHistoryPoints - 1)) * (width - padding - 10);
            const y = height - padding - ((point.value - min) / range) * (height - 2 * padding);

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Draw fill
        ctx.fillStyle = 'rgba(74, 144, 217, 0.1)';
        ctx.lineTo(width - 10, height - padding);
        ctx.lineTo(padding, height - padding);
        ctx.closePath();
        ctx.fill();
    }

    drawResponseChart() {
        const canvas = document.getElementById('response-chart');
        if (!canvas || this.responseTimeHistory.length < 2) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Find min/max for scaling
        const values = this.responseTimeHistory.map(h => h.value);
        const max = Math.max(5, ...values) * 1.1;

        // Draw grid
        ctx.strokeStyle = '#eee';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = height - padding - (i / 4) * (height - 2 * padding);
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - 10, y);
            ctx.stroke();

            // Y-axis labels
            ctx.fillStyle = '#666';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'right';
            const label = ((i / 4) * max).toFixed(1);
            ctx.fillText(`${label}s`, padding - 5, y + 3);
        }

        // Draw line
        ctx.strokeStyle = '#00b894';
        ctx.lineWidth = 2;
        ctx.beginPath();

        this.responseTimeHistory.forEach((point, index) => {
            const x = padding + (index / (this.maxHistoryPoints - 1)) * (width - padding - 10);
            const y = height - padding - (point.value / max) * (height - 2 * padding);

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Draw fill
        ctx.fillStyle = 'rgba(0, 184, 148, 0.1)';
        ctx.lineTo(width - 10, height - padding);
        ctx.lineTo(padding, height - padding);
        ctx.closePath();
        ctx.fill();
    }

    initEmotionLegend() {
        const legend = document.getElementById('emotion-legend');
        if (!legend) return;

        legend.innerHTML = '';
        this.emotions.forEach(emotion => {
            const item = document.createElement('div');
            item.className = 'emotion-item';
            item.innerHTML = `
                <span class="emotion-dot" style="background: ${this.emotionColors[emotion]}"></span>
                <span>${this.capitalizeFirst(emotion)}</span>
                <span class="emotion-value" id="emotion-${emotion}">--</span>
            `;
            legend.appendChild(item);
        });
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    updateEmotions(emotions) {
        if (!emotions) return;

        // Update emotion values
        this.emotions.forEach(name => {
            const el = document.getElementById(`emotion-${name}`);
            if (el && emotions[name] !== undefined) {
                const value = emotions[name];
                el.textContent = (value * 100).toFixed(0) + '%';

                // Color code based on intensity
                el.className = 'emotion-value';
                if (value > 0.8) el.classList.add('high');
                else if (value > 0.6) el.classList.add('medium');
                else el.classList.add('low');
            }
        });

        // Draw emotion radar chart
        this.drawEmotionRadar(emotions);
    }

    drawEmotionRadar(emotions) {
        const canvas = document.getElementById('emotion-radar');
        if (!canvas || !emotions) return;

        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 50;

        const angleStep = (2 * Math.PI) / this.emotions.length;

        // Clear
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw grid circles
        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 1;
        for (let i = 1; i <= 4; i++) {
            ctx.beginPath();
            ctx.arc(centerX, centerY, (radius / 4) * i, 0, 2 * Math.PI);
            ctx.stroke();
        }

        // Draw axis lines and labels
        this.emotions.forEach((emotion, i) => {
            const angle = i * angleStep - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;

            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();

            // Labels
            const labelX = centerX + Math.cos(angle) * (radius + 25);
            const labelY = centerY + Math.sin(angle) * (radius + 25);

            ctx.fillStyle = '#666';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(this.capitalizeFirst(emotion).substring(0, 3), labelX, labelY);
        });

        // Draw emotion polygon
        ctx.fillStyle = 'rgba(74, 144, 217, 0.3)';
        ctx.strokeStyle = '#4a90d9';
        ctx.lineWidth = 2;
        ctx.beginPath();

        this.emotions.forEach((name, i) => {
            const value = emotions[name] || 0.5;
            const angle = i * angleStep - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius * value;
            const y = centerY + Math.sin(angle) * radius * value;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Draw points
        this.emotions.forEach((name, i) => {
            const value = emotions[name] || 0.5;
            const angle = i * angleStep - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius * value;
            const y = centerY + Math.sin(angle) * radius * value;

            ctx.beginPath();
            ctx.arc(x, y, 4, 0, 2 * Math.PI);
            ctx.fillStyle = this.emotionColors[name];
            ctx.fill();
        });
    }

    updatePlatforms(platforms) {
        const container = document.getElementById('platform-grid');
        if (!container || !platforms) return;

        container.innerHTML = '';

        Object.entries(platforms).forEach(([name, info]) => {
            const div = document.createElement('div');
            div.className = `platform-item ${info.status}`;
            div.innerHTML = `
                <span class="platform-name">${this.capitalizeFirst(name)}</span>
                <span class="platform-status">${info.status}</span>
            `;
            container.appendChild(div);
        });

        // If no platforms, show placeholder
        if (Object.keys(platforms).length === 0) {
            container.innerHTML = '<div class="platform-item unknown"><span class="platform-name">No Platforms</span><span class="platform-status">--</span></div>';
        }
    }

    updateAlerts(alerts) {
        const container = document.getElementById('alerts-container');
        const countEl = document.getElementById('alert-count');

        if (countEl) {
            countEl.textContent = alerts && alerts.length > 0 ? `(${alerts.length})` : '';
        }

        if (!container) return;

        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<div class="alert-placeholder">No active alerts</div>';
            return;
        }

        container.innerHTML = '';
        alerts.forEach(alert => {
            const div = document.createElement('div');
            div.className = `alert-item ${alert.level}`;
            div.id = `alert-${alert.id}`;
            div.innerHTML = `
                <div class="alert-content">
                    <div class="alert-header">
                        <span class="alert-severity">${alert.level.toUpperCase()}</span>
                        <span class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-rule">Rule: ${alert.rule_name}</div>
                </div>
                <div class="alert-actions">
                    ${!alert.acknowledged ? `<button class="btn-ack" onclick="dashboard.acknowledgeAlert('${alert.id}')">Ack</button>` : ''}
                    <button class="btn-resolve" onclick="dashboard.resolveAlert('${alert.id}')">Resolve</button>
                </div>
            `;
            container.appendChild(div);
        });
    }

    addAlert(alert) {
        // Refresh alerts list
        this.fetchInitialData();
    }

    async acknowledgeAlert(alertId) {
        try {
            const response = await fetch(`/api/alerts/${alertId}/ack`, {
                method: 'POST'
            });
            if (response.ok) {
                this.fetchInitialData();
            }
        } catch (error) {
            console.error('Failed to acknowledge alert:', error);
        }
    }

    async resolveAlert(alertId) {
        try {
            const response = await fetch(`/api/alerts/${alertId}/resolve`, {
                method: 'POST'
            });
            if (response.ok) {
                this.fetchInitialData();
            }
        } catch (error) {
            console.error('Failed to resolve alert:', error);
        }
    }

    updateTimestamp(timestamp) {
        const el = document.getElementById('last-update');
        if (el && timestamp) {
            const date = new Date(timestamp);
            el.textContent = date.toLocaleTimeString();
        }

        // Update uptime
        const uptimeEl = document.getElementById('uptime');
        if (uptimeEl) {
            uptimeEl.textContent = this.formatUptime(Date.now() - this.startTime);
        }
    }

    formatUptime(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ${hours % 24}h`;
        if (hours > 0) return `${hours}h ${minutes % 60}m`;
        if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
        return `${seconds}s`;
    }

    setupEventListeners() {
        // Handle window resize for canvas
        window.addEventListener('resize', () => {
            this.drawEmotionRadar(this.lastEmotions);
            this.drawMemoryChart();
            this.drawResponseChart();
            this.drawEmotionHistoryChart();
        });

        // Track start time for uptime
        this.startTime = Date.now();
    }

    async fetchLLMMetrics() {
        try {
            const response = await fetch('/api/metrics/llm');
            if (response.ok) {
                const data = await response.json();
                console.debug('LLM metrics fetched:', data);
                this.updateLLMMetrics(data);
            } else {
                console.warn('LLM metrics fetch failed:', response.status);
            }
        } catch (error) {
            console.warn('Failed to fetch LLM metrics:', error);
        }
    }

    updateLLMMetrics(data) {
        if (!data.stats) return;

        const avgResponse = document.getElementById('llm-avg-response');
        const maxResponse = document.getElementById('llm-max-response');
        const totalTokens = document.getElementById('llm-total-tokens');

        if (avgResponse) {
            avgResponse.textContent = `${data.stats.avg_response_time.toFixed(0)} ms`;
        }
        if (maxResponse) {
            maxResponse.textContent = `${data.stats.max_response_time.toFixed(0)} ms`;
        }
        if (totalTokens) {
            totalTokens.textContent = `${data.stats.total_tokens.toLocaleString()}`;
        }

        // Store for chart rendering
        this.llmResponseTimes = data.response_times || [];
    }

    async fetchPlatformMetrics() {
        try {
            const response = await fetch('/api/metrics/platforms');
            if (response.ok) {
                const data = await response.json();
                console.debug('Platform metrics fetched:', data);
                this.updatePlatformMetrics(data);
            } else {
                console.warn('Platform metrics fetch failed:', response.status);
            }
        } catch (error) {
            console.warn('Failed to fetch platform metrics:', error);
        }
    }

    updatePlatformMetrics(data) {
        const container = document.getElementById('platform-metrics-display');
        if (!container) return;

        if (!data.platforms || Object.keys(data.platforms).length === 0) {
            container.innerHTML = '<div style="text-align: center; color: var(--text-muted);">No platform metrics available</div>';
            return;
        }

        let html = '';
        Object.entries(data.platforms).forEach(([platform, stats]) => {
            html += `
                <div style="padding: 12px; background: var(--bg-color); border-radius: 8px; border-left: 4px solid ${stats.error_rate > 5 ? 'var(--warning-color)' : 'var(--success-color)'};">
                    <div style="font-weight: 600; margin-bottom: 8px; text-transform: capitalize;">${platform}</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.9rem;">
                        <div><span style="color: var(--text-muted);">Messages:</span> <span style="color: var(--primary-color); font-weight: 600;">${stats.message_count}</span></div>
                        <div><span style="color: var(--text-muted);">Avg Response:</span> <span style="color: var(--primary-color); font-weight: 600;">${stats.avg_response_time_ms.toFixed(0)}ms</span></div>
                        <div><span style="color: var(--text-muted);">Errors:</span> <span style="color: ${stats.error_count > 0 ? 'var(--warning-color)' : 'var(--success-color)'}; font-weight: 600;">${stats.error_count}</span></div>
                        <div><span style="color: var(--text-muted);">Error Rate:</span> <span style="color: ${stats.error_rate > 5 ? 'var(--warning-color)' : 'var(--success-color)'}; font-weight: 600;">${stats.error_rate.toFixed(2)}%</span></div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    async fetchConversationMetrics() {
        try {
            const response = await fetch('/api/metrics/conversation');
            if (response.ok) {
                const data = await response.json();
                console.debug('Conversation metrics fetched:', data);
                this.updateConversationMetrics(data);
            } else {
                console.warn('Conversation metrics fetch failed:', response.status);
            }
        } catch (error) {
            console.warn('Failed to fetch conversation metrics:', error);
        }
    }

    updateConversationMetrics(data) {
        if (!data.quality) return;

        const userLength = document.getElementById('conv-user-length');
        const responseLength = document.getElementById('conv-response-length');
        const sentiment = document.getElementById('conv-sentiment');
        const maxTurn = document.getElementById('conv-max-turn');

        if (userLength) {
            userLength.textContent = `${Math.round(data.quality.avg_user_message_length)} chars`;
        }
        if (responseLength) {
            responseLength.textContent = `${Math.round(data.quality.avg_response_length)} chars`;
        }
        if (sentiment) {
            sentiment.textContent = (data.quality.avg_sentiment * 100).toFixed(0) + '%';
        }
        if (maxTurn) {
            maxTurn.textContent = `${data.quality.max_conversation_turn}`;
        }
    }

    async fetchEmotionHistory() {
        try {
            const response = await fetch('/api/metrics/emotions/history?hours=1&limit=50');
            if (response.ok) {
                const data = await response.json();
                console.debug('Emotion history fetched, emotions:', Object.keys(data.emotions || {}));
                this.updateEmotionHistory(data);
            } else {
                console.warn('Emotion history fetch failed:', response.status);
            }
        } catch (error) {
            console.warn('Failed to fetch emotion history:', error);
        }
    }

    updateEmotionHistory(data) {
        if (!data.emotions) return;
        this.emotionHistory = data.emotions;
        this.drawEmotionHistoryChart();
    }

    drawEmotionHistoryChart() {
        const canvas = document.getElementById('emotion-history-chart');
        if (!canvas || !this.emotionHistory) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;

        ctx.clearRect(0, 0, width, height);

        // Get all timestamps
        const allTimestamps = new Set();
        Object.values(this.emotionHistory).forEach(emotion => {
            emotion.forEach(point => {
                allTimestamps.add(Math.floor(point.timestamp));
            });
        });
        const timestamps = Array.from(allTimestamps).sort();

        if (timestamps.length < 2) return;

        // Draw grid
        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = height - padding - (i / 4) * (height - 2 * padding);
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - 10, y);
            ctx.stroke();

            // Y-axis labels
            ctx.fillStyle = '#666';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText((i / 4).toFixed(1), padding - 5, y + 3);
        }

        // Draw lines for each emotion
        const emotionColors = this.emotionColors;
        Object.entries(this.emotionHistory).forEach(([emotion, points]) => {
            if (points.length < 2) return;

            ctx.strokeStyle = emotionColors[emotion];
            ctx.lineWidth = 2;
            ctx.beginPath();

            points.forEach((point, index) => {
                const x = padding + (index / (points.length - 1)) * (width - padding - 10);
                const y = height - padding - point.value * (height - 2 * padding);

                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.stroke();
        });
    }

    async fetchDiscordStatus() {
        try {
            const response = await fetch('/api/metrics/discord');
            if (response.ok) {
                const data = await response.json();
                console.debug('Discord status fetched:', data.bot_status);
                this.updateDiscordStatus(data);
            } else {
                console.warn('Discord status fetch failed:', response.status);
            }
        } catch (error) {
            console.warn('Failed to fetch Discord status:', error);
        }
    }

    updateDiscordStatus(data) {
        if (!data.bot_status) return;

        const status = data.bot_status;
        const indicator = document.getElementById('discord-status-indicator');
        const latency = document.getElementById('discord-latency');
        const guilds = document.getElementById('discord-guilds');
        const users = document.getElementById('discord-users');

        // Update status indicator
        if (indicator) {
            indicator.className = `status-indicator ${status.online ? 'online' : 'offline'}`;
            indicator.innerHTML = `
                <span class="status-dot ${status.online ? 'online' : 'offline'}"></span>
                <span>${status.online ? 'Online' : 'Offline'}</span>
            `;
        }

        // Update stats
        if (latency) {
            latency.textContent = status.latency_ms ? status.latency_ms.toFixed(0) : '--';
        }
        if (guilds) {
            guilds.textContent = status.guild_count || '--';
        }
        if (users) {
            users.textContent = status.connected_users || '--';
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DemiDashboard();
});
