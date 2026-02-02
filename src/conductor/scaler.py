"""Predictive auto-scaling engine using ML models to manage resource constraints.

This module provides intelligent scaling decisions based on historical resource trends
and ML predictions, with graceful degradation of integrations to stay within the 12GB RAM limit.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from collections import deque

from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.conductor.metrics import get_metrics
from src.conductor.resource_monitor import ResourceMonitor, ResourceMetrics

logger = get_logger()

try:
    from sklearn.linear_model import LinearRegression
    import numpy as np

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn not installed, predictions will use fallback method")


@dataclass
class ScalingDecision:
    """Result of a scaling decision analysis."""

    timestamp: float
    decision: str  # "none", "scale_down", "scale_up", "emergency_shutdown"
    reason: str
    predicted_load: float
    confidence: float
    disabled_integrations: List[str] = field(default_factory=list)
    enabled_integrations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {
            "timestamp": self.timestamp,
            "decision": self.decision,
            "reason": self.reason,
            "predicted_load": self.predicted_load,
            "confidence": self.confidence,
            "disabled": self.disabled_integrations,
            "enabled": self.enabled_integrations,
        }


class PredictiveScaler:
    """ML-based predictive scaling engine for managing integrations.

    Uses Linear Regression to forecast resource needs 5 minutes ahead,
    with hysteresis thresholds (80% disable / 65% enable) to prevent oscillation.
    Gracefully degrades integrations in priority order: Voice > Android > Discord > stubs.
    """

    # Graceful degradation order (from least critical to most critical to disable)
    DEGRADATION_ORDER = ["voice", "android", "discord", "stubs"]

    def __init__(self, resource_monitor: Optional[ResourceMonitor] = None):
        """Initialize predictive scaler.

        Args:
            resource_monitor: Optional ResourceMonitor instance to use
        """
        self.resource_monitor = resource_monitor
        self.config = DemiConfig.load()

        # Scaling thresholds
        self.disable_threshold = self.config.system.get("ram_threshold", 80)
        self.enable_threshold = self.disable_threshold - 15  # Hysteresis gap

        # ML model for predictions
        self._model: Optional[LinearRegression] = None if HAS_SKLEARN else None
        self._model_trained_at: float = 0
        self._min_data_points = 10  # Minimum points needed for training

        # Smoothing for stability (exponential moving average)
        self.smoothing_factor = 0.7  # Higher = more responsive, lower = more stable
        self._ema_load: Optional[float] = None

        # Prediction parameters
        self.lookahead_minutes = 5  # Predict 5 minutes ahead
        self.prediction_points = int(
            (self.lookahead_minutes * 60) / 30
        )  # ~10 points at 30s intervals

        # Integration state tracking
        self.disabled_integrations: Set[str] = set()
        self.enabled_integrations: Set[str] = set(self.DEGRADATION_ORDER)

        # Audit log for scaling decisions
        self.decision_log: deque = deque(maxlen=100)

        # Metrics registry
        self.metrics = get_metrics()

        logger.info(
            "PredictiveScaler initialized",
            disable_threshold=self.disable_threshold,
            enable_threshold=self.enable_threshold,
            has_sklearn=HAS_SKLEARN,
        )

    def update_model(self, historical_data: List[ResourceMetrics]) -> bool:
        """Train ML model on historical resource data.

        Args:
            historical_data: List of ResourceMetrics from sliding window

        Returns:
            True if training successful, False otherwise
        """
        if not HAS_SKLEARN:
            logger.debug("Skipping model training (sklearn not available)")
            return False

        if len(historical_data) < self._min_data_points:
            logger.debug(
                "Insufficient data for model training",
                data_points=len(historical_data),
                minimum=self._min_data_points,
            )
            return False

        try:
            # Extract memory usage from historical data (focus on RAM as critical constraint)
            values = [m.memory for m in historical_data]

            # Create feature matrix (X = time indices)
            X = np.arange(len(values)).reshape(-1, 1)
            y = np.array(values)

            # Train model
            self._model = LinearRegression()
            self._model.fit(X, y)
            self._model_trained_at = time.time()

            logger.debug(
                "Model trained successfully",
                data_points=len(values),
                slope=float(self._model.coef_[0])
                if self._model.coef_ is not None
                else 0,
            )
            return True

        except Exception as e:
            logger.error("Model training failed", error=str(e))
            return False

    def predict_load(
        self, current_metrics: Dict[str, float], lookahead_points: Optional[int] = None
    ) -> float:
        """Predict resource load N points into the future.

        Args:
            current_metrics: Current metrics dictionary
            lookahead_points: Optional override for number of points to predict ahead

        Returns:
            Predicted memory load percentage (0-100)
        """
        if lookahead_points is None:
            lookahead_points = self.prediction_points

        current_memory = current_metrics.get("memory", 50)

        if not HAS_SKLEARN or not self._model:
            # Fallback: assume linear trend continues
            return min(100, current_memory + 5)

        try:
            # Predict value at future point
            future_point = np.array([[lookahead_points]])
            predicted_value = float(self._model.predict(future_point)[0])

            # Clamp to valid range
            predicted_value = max(0, min(100, predicted_value))

            return predicted_value

        except Exception as e:
            logger.warning("Prediction failed, using fallback", error=str(e))
            return min(100, current_memory + 5)

    def _apply_smoothing(self, predicted_load: float) -> float:
        """Apply exponential moving average smoothing to prevent oscillation.

        Args:
            predicted_load: Raw predicted load

        Returns:
            Smoothed predicted load
        """
        if self._ema_load is None:
            self._ema_load = predicted_load
            return predicted_load

        # EMA formula: new_ema = (current * factor) + (previous * (1 - factor))
        self._ema_load = (predicted_load * self.smoothing_factor) + (
            self._ema_load * (1 - self.smoothing_factor)
        )
        return self._ema_load

    async def evaluate_and_adjust(
        self, resource_monitor: ResourceMonitor
    ) -> ScalingDecision:
        """Evaluate current resource state and make scaling decisions.

        This is the main entry point. It:
        1. Gets current metrics and historical data
        2. Updates the ML model
        3. Predicts future load
        4. Decides whether to scale
        5. Disables/enables integrations as needed

        Args:
            resource_monitor: ResourceMonitor instance with current data

        Returns:
            ScalingDecision with action taken
        """
        now = time.time()
        current = resource_monitor.get_current_metrics()

        if not current:
            return ScalingDecision(
                timestamp=now,
                decision="none",
                reason="No metrics available yet",
                predicted_load=0,
                confidence=0,
            )

        # Get historical data for model training
        history = resource_monitor.get_history()
        if len(history) >= self._min_data_points:
            self.update_model(history)

        # Make prediction
        current_dict = current.to_dict()
        predicted_load = self.predict_load(current_dict)
        smoothed_load = self._apply_smoothing(predicted_load)

        # Determine confidence based on model state
        confidence = 0.8 if (self._model and HAS_SKLEARN) else 0.5

        # Decide on action
        decision_str = "none"
        reason = "Load within thresholds"
        disabled = []
        enabled = []

        if smoothed_load >= self.disable_threshold:
            # Scale down: disable integrations starting with lowest priority
            decision_str = "scale_down"
            reason = f"Predicted load {smoothed_load:.1f}% exceeds disable threshold {self.disable_threshold}%"
            disabled = await self._scale_down(resource_monitor)

        elif smoothed_load <= self.enable_threshold and self.disabled_integrations:
            # Scale up: enable previously disabled integrations
            decision_str = "scale_up"
            reason = f"Predicted load {smoothed_load:.1f}% below enable threshold {self.enable_threshold}%, recovering integrations"
            enabled = await self._scale_up(resource_monitor)

        elif current.memory >= 95:
            # Emergency: critical resource level
            decision_str = "emergency_shutdown"
            reason = "CRITICAL: Memory at 95%+, entering emergency mode"
            disabled = await self._emergency_shutdown(resource_monitor)

        # Log decision
        decision = ScalingDecision(
            timestamp=now,
            decision=decision_str,
            reason=reason,
            predicted_load=smoothed_load,
            confidence=confidence,
            disabled_integrations=disabled,
            enabled_integrations=enabled,
        )

        self.decision_log.append(decision)
        logger.info(
            "scaling_decision",
            decision=decision_str,
            predicted_load=f"{smoothed_load:.1f}%",
            current_memory=f"{current.memory:.1f}%",
            disabled=len(disabled),
            enabled=len(enabled),
        )

        return decision

    async def _scale_down(self, resource_monitor: ResourceMonitor) -> List[str]:
        """Disable integrations to reduce resource usage.

        Args:
            resource_monitor: ResourceMonitor instance

        Returns:
            List of integrations that were disabled
        """
        disabled = []

        # Try disabling from lowest priority upward
        for integration in self.DEGRADATION_ORDER:
            if integration in self.enabled_integrations:
                if await self._disable_integration(integration, resource_monitor):
                    self.enabled_integrations.remove(integration)
                    self.disabled_integrations.add(integration)
                    disabled.append(integration)
                    logger.warning(
                        f"Disabled integration: {integration}",
                        remaining=self.enabled_integrations,
                    )

                    # Re-check metrics after each disable
                    await asyncio.sleep(0.5)
                    if resource_monitor.get_current_metrics():
                        current_memory = resource_monitor.get_current_metrics().memory
                        if current_memory < self.disable_threshold - 5:
                            # Recovered enough, stop disabling
                            logger.info(
                                "Scaling stabilized",
                                memory=f"{current_memory:.1f}%",
                                disabled_count=len(disabled),
                            )
                            break

        return disabled

    async def _scale_up(self, resource_monitor: ResourceMonitor) -> List[str]:
        """Enable previously disabled integrations to restore functionality.

        Args:
            resource_monitor: ResourceMonitor instance

        Returns:
            List of integrations that were enabled
        """
        enabled = []

        # Enable in reverse priority order (restore highest priority first)
        for integration in reversed(self.DEGRADATION_ORDER):
            if integration in self.disabled_integrations:
                if await self._enable_integration(integration, resource_monitor):
                    self.disabled_integrations.remove(integration)
                    self.enabled_integrations.add(integration)
                    enabled.append(integration)
                    logger.info(
                        f"Enabled integration: {integration}",
                        active=self.enabled_integrations,
                    )

                    # Check if re-enabling causes memory spike
                    await asyncio.sleep(0.5)
                    if resource_monitor.get_current_metrics():
                        current_memory = resource_monitor.get_current_metrics().memory
                        if current_memory > self.disable_threshold:
                            # Can't sustain this many enabled, stop enabling
                            logger.warning(
                                "Memory spike detected during scale-up, stopping",
                                memory=f"{current_memory:.1f}%",
                            )
                            break

        return enabled

    async def _emergency_shutdown(self, resource_monitor: ResourceMonitor) -> List[str]:
        """Emergency shutdown: disable all non-critical integrations immediately.

        Args:
            resource_monitor: ResourceMonitor instance

        Returns:
            List of integrations that were disabled
        """
        logger.critical("EMERGENCY SHUTDOWN INITIATED - Memory critical")

        disabled = []
        for integration in self.DEGRADATION_ORDER[:-1]:  # Keep only stubs
            if integration in self.enabled_integrations:
                if await self._disable_integration(integration, resource_monitor):
                    self.enabled_integrations.remove(integration)
                    self.disabled_integrations.add(integration)
                    disabled.append(integration)
                    logger.critical(f"EMERGENCY: Disabled {integration}")

        return disabled

    async def _disable_integration(
        self, integration: str, resource_monitor: ResourceMonitor
    ) -> bool:
        """Disable a specific integration via plugin manager.

        Args:
            integration: Integration name to disable
            resource_monitor: ResourceMonitor instance

        Returns:
            True if successful, False otherwise
        """
        try:
            # Import here to avoid circular dependencies
            from src.plugins.manager import PluginManager

            pm = PluginManager()
            await pm.discover_and_register()

            # Find plugin matching integration name
            for plugin_name in pm.registry:
                if integration.lower() in plugin_name.lower():
                    logger.info(f"Attempting to disable plugin: {plugin_name}")
                    await pm.unload_plugin(plugin_name)
                    return True

            logger.warning(f"Plugin not found for integration: {integration}")
            return False

        except Exception as e:
            logger.error(f"Failed to disable {integration}: {e}")
            return False

    async def _enable_integration(
        self, integration: str, resource_monitor: ResourceMonitor
    ) -> bool:
        """Enable a specific integration via plugin manager.

        Args:
            integration: Integration name to enable
            resource_monitor: ResourceMonitor instance

        Returns:
            True if successful, False otherwise
        """
        try:
            # Import here to avoid circular dependencies
            from src.plugins.manager import PluginManager

            pm = PluginManager()
            await pm.discover_and_register()

            # Find plugin matching integration name
            for plugin_name in pm.registry:
                if integration.lower() in plugin_name.lower():
                    logger.info(f"Attempting to enable plugin: {plugin_name}")
                    await pm.load_plugin(plugin_name)
                    return True

            logger.warning(f"Plugin not found for integration: {integration}")
            return False

        except Exception as e:
            logger.error(f"Failed to enable {integration}: {e}")
            return False

    def get_scaling_status(self) -> Dict:
        """Get current scaling status and audit log.

        Returns:
            Dictionary with enabled/disabled integrations and recent decisions
        """
        recent_decisions = [d.to_dict() for d in list(self.decision_log)[-10:]]

        return {
            "enabled_integrations": list(self.enabled_integrations),
            "disabled_integrations": list(self.disabled_integrations),
            "disable_threshold": self.disable_threshold,
            "enable_threshold": self.enable_threshold,
            "recent_decisions": recent_decisions,
            "model_trained": self._model_trained_at > 0,
            "last_training": (
                datetime.fromtimestamp(self._model_trained_at).isoformat()
                if self._model_trained_at > 0
                else None
            ),
        }
