# Phase 02: Conductor Orchestrator & Integration Manager - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

---

## Phase Boundary

Phase 02 delivers the central nervous system for Demi. It orchestrates startup, monitors health of all integrations, manages resource scaling autonomously, routes requests between platforms, and ensures one failure cannot cascade through the system. This builds directly on the foundation from Phase 01 and enables the emotional system (Phase 3) to function properly.

---

## Implementation Decisions

### Health Monitoring Strategy

**Health Check Frequency**: 5 seconds with lightweight checks
- Chosen based on user preference for real-time monitoring
- Each check validates platform connectivity, response time (<200ms), and error counts
- Comprehensive health metrics available via REST endpoints

**Failure Detection**: Consecutive failure threshold of 3 before platform marked as failed
- Uses exponential backoff with tenacity for retry logic
- Circuit breaker pattern with HALF_OPEN state for testing recovery

### Auto-scaling Approach

**Predictive Scaling**: Usage pattern analysis with 30-minute sliding window
- scikit-learn Linear Regression model for resource prediction
- RAM thresholds: Disable integrations at 80%, re-enable at 65%
- Graceful degradation order: Voice > Android > Discord > stubs

**Scaling Triggers**:
- Gradual load increase (requests per second > threshold)
- Sudden spike detection (2x normal rate within 30 seconds)
- Proactive scaling based on time-of-day patterns

### Plugin System Architecture

**Plugin Discovery**: Directory scanning + registration hooks using importlib.metadata
- Plugins are Python modules with standardized interface
- Hot-swapping support with dependency resolution
- Lazy loading by default, eager loading option available

**Plugin Interface**:
```python
class PlatformPlugin:
    def initialize(self, config: Dict[str, Any]) -> bool
    def health_check(self) -> PluginHealth
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]
    def shutdown(self) -> None
```

### Platform Integration Patterns

**Isolation Mechanisms**: Async subprocess with resource limits and timeouts
- Each platform integration runs in isolated async context
- Process pools limit concurrent operations per platform
- 5-second timeout for individual requests

**Routing Strategy**: Request pattern matching with fallback capabilities
- Content-based routing for Discord commands vs Android API
- Load balancing for multiple instances of same platform
- Dead letter queue for failed requests

### Technical Stack Decisions

**Core Libraries**:
- `asyncio` for event loop and task management
- `aiobreaker` for circuit breaker patterns
- `tenacity` for retry logic with exponential backoff
- `psutil` for resource monitoring (RAM, CPU, disk)
- `scikit-learn` for predictive scaling models
- `importlib.metadata` for plugin discovery
- `aiohttp` for HTTP APIs (Android integration)

**Database Schema**:
```python
class IntegrationMetrics(Base):
    __tablename__ = 'integration_metrics'
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    platform_name = Column(String)
    response_time_ms = Column(Integer)
    error_count = Column(Integer)
    request_count = Column(Integer)
    resource_usage_mb = Column(Float)
```

### Architecture Patterns

**Orchestrator Loop**:
```python
class Conductor:
    async def health_check_loop(self):
        """Run every 5 seconds"""
        for plugin in self.platforms.values():
            health = await plugin.health_check()
            self.circuit_breakers[plugin.name].record_result(health)
    
    async def resource_monitor(self):
        """Monitor RAM usage and trigger scaling"""
        ram_usage = psutil.virtual_memory().percent
        await self.predictive_scaler.evaluate_and_adjust(ram_usage)
```

**Startup Sequence**:
1. Load configuration and initialize plugins
2. Initialize database connection and health metrics
3. Start background health monitoring loop
4. Register platform integrations with circuit breakers
5. Enable request routing and load balancing

### Performance Requirements

From research, critical performance targets for Phase 02:
- Health loop tick time: <200ms (target: 5s interval with 40ms processing budget)
- Circuit breaker response: <50ms
- Plugin discovery: <1s for full scan
- Resource monitoring overhead: <50MB total
- Request routing: <10ms overhead

### Testing Strategy

**Unit Tests**: Each component tested independently
**Integration Tests**: Full conductor with mock plugins
**Load Testing**: 10x normal request volume
**Chaos Testing**: Random failures to verify isolation and recovery

---

## Claude's Discretion Areas

The following areas are explicitly delegated to Claude during implementation:

### Plugin Security Model
- Plugin sandboxing and permission system design
- Code validation and security scanning for third-party plugins
- Process isolation and resource limits

### ML Model Refinement
- Model retraining strategy based on production data
- A/B testing framework for scaling algorithm improvements
- Feature engineering for better resource usage prediction

### Advanced Circuit Breaker Patterns
- Multi-level circuit breakers for different failure modes
- Distributed circuit breaker state management (if ever needed)
- Custom recovery strategies per platform type

---

*Phase 02 context captured. Ready for planning with clear implementation decisions.*