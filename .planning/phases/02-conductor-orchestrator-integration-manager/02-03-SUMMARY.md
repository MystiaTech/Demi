---
phase: 02-conductor-orchestrator-integration-manager
plan: 03
subsystem: conductor
tags: [resource-monitoring, auto-scaling, machine-learning, predictive, graceful-degradation, psutil, sklearn]

requires:
  - phase: 02-01
    provides: Plugin architecture and discovery system needed by scaler to enable/disable integrations
  - phase: 02-02
    provides: Health monitoring foundation, Prometheus metrics integration

provides:
  - Resource monitoring with 30-minute sliding window analysis
  - ML-based predictive auto-scaling engine
  - Graceful integration degradation (voice > android > discord > stubs)
  - Hysteresis-based threshold control (80% disable / 65% enable)
  - Exponential moving average smoothing to prevent oscillation

affects:
  - Phase 03+: Emotional system depends on stable resource allocation
  - Phase 05+: Platform integrations depend on scaler for lifecycle management
  - Phase 09: Integration testing validates scaler stability under load

tech-stack:
  added:
    - psutil 7.2.1 (system resource monitoring)
    - scikit-learn (optional, LinearRegression for ML predictions)
  patterns:
    - Sliding window for historical data management (deque with maxlen)
    - ML model training on historical data with fallback mode
    - Hysteresis pattern for threshold-based decisions
    - Graceful degradation with priority ordering
    - Exponential moving average for smoothing

key-files:
  created:
    - src/conductor/resource_monitor.py (314 lines)
    - src/conductor/scaler.py (486 lines)
  modified: []

key-decisions:
  - "Used deque for sliding window (memory-efficient, FIFO semantics)"
  - "Made sklearn optional with fallback linear trend prediction"
  - "Hysteresis gap set to 15% (80→65) to prevent rapid oscillation"
  - "Graceful degradation order prioritizes stubs > discord > android > voice"
  - "Exponential moving average smoothing factor: 0.7 (responsive but stable)"

patterns-established:
  - Resource history stored as ResourceMetrics dataclass snapshots
  - Scaling decisions logged with full audit trail
  - Prediction confidence reflects model availability (0.8 with sklearn, 0.5 fallback)
  - Integration disable/enable via PluginManager (decoupled from scaler)

duration: 8 min
completed: 2026-02-02
---

# Phase 2 Plan 3: Resource Monitoring & Predictive Auto-Scaling Summary

**ML-based predictive auto-scaling with 30-minute sliding window analysis, Linear Regression forecasts, hysteresis thresholds, and graceful integration degradation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-02T01:52:00Z
- **Completed:** 2026-02-02T02:00:36Z
- **Tasks:** 2 completed
- **Files created:** 2 (800 lines total)

## Accomplishments

- **Resource Monitor**: Tracks CPU, RAM, disk every collection cycle with 30-minute sliding window (60 data points)
- **Trend Analysis**: Calculates average/min/max and rate-of-change for resource trends
- **Anomaly Detection**: Statistical spike detection using standard deviation thresholds
- **Predictive Scaler**: ML model trains on historical data to forecast resource needs 5 minutes ahead
- **Auto-Scaling**: Makes intelligent decisions on enable/disable with hysteresis (80%→65%) to prevent oscillation
- **Graceful Degradation**: Disables integrations in priority order (voice → android → discord → stubs)
- **Smoothing**: Exponential moving average (factor 0.7) for stable scaling decisions
- **Integration**: Seamless PluginManager integration for enable/disable operations
- **Audit Trail**: Comprehensive logging of all scaling decisions with confidence metrics

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement resource monitoring system** - `5838f1a` (feat)
   - ResourceMonitor class with 60-point sliding window
   - psutil integration for CPU/RAM/disk tracking
   - Trend calculation and anomaly detection
   - Prometheus metrics recording with graceful fallback

2. **Task 2: Build predictive auto-scaling engine** - `40619e3` (feat)
   - PredictiveScaler with LinearRegression ML model
   - 5-minute lookahead predictions
   - Hysteresis-based threshold control
   - Graceful degradation with priority ordering
   - Emergency shutdown at 95% RAM

**Plan metadata:** docs commit will follow after STATE/ROADMAP update

## Files Created/Modified

- `src/conductor/resource_monitor.py` - System resource monitoring with historical analysis (333 lines)
- `src/conductor/scaler.py` - Predictive auto-scaling engine with ML models (486 lines)

## Decisions Made

| Decision | Rationale | Implementation |
|----------|-----------|-----------------|
| Sliding window (deque) for history | Memory-efficient, maintains FIFO ordering, bounded storage | deque(maxlen=60) with periodic collection |
| Optional sklearn with fallback | Robust to missing dependencies, fallback uses linear trend | Linear Regression if available, else simple forecast |
| Hysteresis gap (80%→65%) | Prevents oscillation from rapid enable/disable cycles | 15% gap configured, smoothing factor 0.7 |
| Graceful degradation order | Voice/Android less critical than Discord for v1 | voice > android > discord > stubs |
| Exponential moving average | Smooths predictions while remaining responsive | Factor 0.7 (70% new, 30% previous) |
| PluginManager integration | Decouples scaling decisions from plugin lifecycle | Scaler calls pm.disable_plugin/load_plugin |
| 5-minute prediction window | Balance: too short=noisy, too long=miss spikes | Calculation: (5*60)/30 = 10 points |

## Deviations from Plan

None - plan executed exactly as written.

All must-have truths verified:
- ✓ Resource monitor tracks RAM/CPU/disk with 30-second intervals
- ✓ Predictive scaler uses Linear Regression to forecast needs
- ✓ Auto-scaling disables at 80% RAM, re-enables at 65%
- ✓ Scaling decisions use ML predictions with smoothing

All artifacts present with required structure:
- ✓ ResourceMonitor class in resource_monitor.py (50+ lines)
- ✓ PredictiveScaler class in scaler.py (70+ lines)
- ✓ Key links established (scaler→resource_monitor→metrics)

## Issues Encountered

None - implementation smooth, all tests passing.

## Next Phase Readiness

**Resource scaling foundation complete.** Ready for:
- Phase 03: Emotional System (depends on stable resource allocation)
- Phase 05+: Platform integrations can rely on scaler for graceful degradation

**Stability notes:**
- Model training requires minimum 10 data points (safe for production)
- Fallback mode activates gracefully if sklearn unavailable
- Hysteresis prevents feedback loops at threshold boundaries
- Decision audit log (100 entries) enables troubleshooting

---

*Phase: 02-conductor-orchestrator-integration-manager*
*Completed: 2026-02-02*
