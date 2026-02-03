"""
Emotional State Monitor for Stability Testing.

Tracks emotional state consistency over extended periods, detecting
anomalies and verifying that emotions behave correctly over time.

Requirements:
    - HEALTH-03: Emotional state preserved across restarts
    - Validates emotional consistency (no sudden jumps without cause)
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean, stdev

from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.emotion.decay import DecaySystem


# Consistency rules for emotional state validation
CONSISTENCY_RULES = {
    # Maximum allowed change between consecutive readings
    "max_single_change": 0.3,
    
    # Maximum allowed drift over 24 hours without interaction
    "max_daily_drift": 0.4,
    
    # Minimum floor enforcement (must be respected)
    "floor_violation_tolerance": 0.01,
    
    # Momentum decay check (should decay over time)
    "momentum_decay_expected": True,
    
    # Maximum emotion value (hard limit)
    "max_emotion_value": 1.0,
    
    # Minimum emotion value (hard limit)
    "min_emotion_value": 0.0,
}


@dataclass
class EmotionSnapshot:
    """
    Snapshot of emotional state at a point in time.
    
    Attributes:
        timestamp: When the snapshot was taken
        state: The emotional state at that time
        trigger: What caused this state (interaction, decay, etc.)
    """
    timestamp: datetime
    state: EmotionalState
    trigger: str  # What caused this state (interaction, decay, etc.)
    
    def to_dict(self) -> Dict:
        """Convert snapshot to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "state": self.state.to_dict(),
            "trigger": self.trigger,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EmotionSnapshot":
        """Create snapshot from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            state=EmotionalState.from_dict(data["state"]),
            trigger=data["trigger"],
        )


@dataclass
class EmotionDriftReport:
    """
    Report on emotional state drift over time.
    
    Attributes:
        emotion_name: Name of the emotion analyzed
        start_value: Value at start of period
        end_value: Value at end of period
        min_value: Minimum value observed
        max_value: Maximum value observed
        drift_amount: Total drift (end - start)
        is_consistent: Whether drift is within expected bounds
        violations: List of any violations detected
    """
    emotion_name: str
    start_value: float
    end_value: float
    min_value: float
    max_value: float
    drift_amount: float
    is_consistent: bool
    violations: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "emotion_name": self.emotion_name,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "drift_amount": self.drift_amount,
            "is_consistent": self.is_consistent,
            "violations": self.violations,
        }


class EmotionStabilityMonitor:
    """
    Monitors emotional state stability over time.
    
    Tracks emotional state snapshots, validates consistency,
    detects anomalies, and generates decay reports.
    
    Example:
        >>> monitor = EmotionStabilityMonitor(persistence)
        >>> await monitor.record_state(state, trigger="user_message")
        >>> report = monitor.check_consistency()
        >>> anomalies = monitor.detect_anomalies()
    """
    
    def __init__(
        self,
        persistence: EmotionPersistence,
        check_interval_minutes: int = 30,
        max_history_hours: float = 168  # 7 days
    ):
        """
        Initialize emotion stability monitor.
        
        Args:
            persistence: Emotion persistence layer
            check_interval_minutes: How often to check consistency
            max_history_hours: Maximum history to retain
        """
        self.persistence = persistence
        self.check_interval = check_interval_minutes
        self.max_history_hours = max_history_hours
        
        # Snapshot history
        self.snapshots: List[EmotionSnapshot] = []
        
        # Check results
        self.check_results: List[Dict] = []
    
    async def record_state(
        self,
        state: EmotionalState,
        trigger: str = "scheduled",
        timestamp: Optional[datetime] = None
    ) -> EmotionSnapshot:
        """
        Record current emotional state.
        
        Args:
            state: Current emotional state
            trigger: What caused this state
            timestamp: Optional timestamp (default: now)
            
        Returns:
            Created snapshot
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        snapshot = EmotionSnapshot(
            timestamp=timestamp,
            state=state,
            trigger=trigger
        )
        
        self.snapshots.append(snapshot)
        
        # Maintain rolling window
        self._prune_old_snapshots()
        
        return snapshot
    
    async def record_snapshot(self, trigger: str = "scheduled") -> Optional[EmotionSnapshot]:
        """
        Record snapshot from persistence layer.
        
        Args:
            trigger: What caused this snapshot
            
        Returns:
            Created snapshot or None if no state available
        """
        state = self.persistence.load_latest_state()
        if state is None:
            return None
        
        return await self.record_state(state, trigger)
    
    def _prune_old_snapshots(self):
        """Remove snapshots older than max_history_hours."""
        if not self.snapshots:
            return
        
        cutoff = datetime.now() - timedelta(hours=self.max_history_hours)
        self.snapshots = [s for s in self.snapshots if s.timestamp > cutoff]
    
    def check_consistency(self) -> Dict[str, EmotionDriftReport]:
        """
        Check emotional state consistency across all snapshots.
        
        Returns:
            Dict mapping emotion names to drift reports
        """
        if len(self.snapshots) < 2:
            return {}
        
        reports = {}
        
        for emotion_name in self.snapshots[0].state.get_all_emotions().keys():
            report = self._analyze_emotion_drift(emotion_name)
            reports[emotion_name] = report
        
        return reports
    
    def _analyze_emotion_drift(self, emotion_name: str) -> EmotionDriftReport:
        """
        Analyze drift for a single emotion.
        
        Args:
            emotion_name: Name of emotion to analyze
            
        Returns:
            Drift report for the emotion
        """
        if len(self.snapshots) < 2:
            return EmotionDriftReport(
                emotion_name=emotion_name,
                start_value=0.0,
                end_value=0.0,
                min_value=0.0,
                max_value=0.0,
                drift_amount=0.0,
                is_consistent=True,
                violations=[{"error": "Insufficient snapshots"}],
            )
        
        # Collect values
        values = []
        for snapshot in self.snapshots:
            value = getattr(snapshot.state, emotion_name)
            values.append((snapshot.timestamp, value))
        
        start_value = values[0][1]
        end_value = values[-1][1]
        min_value = min(v for _, v in values)
        max_value = max(v for _, v in values)
        drift_amount = end_value - start_value
        
        # Check for violations
        violations = []
        
        # Check for excessive single changes
        for i in range(1, len(values)):
            prev_time, prev_val = values[i-1]
            curr_time, curr_val = values[i]
            change = abs(curr_val - prev_val)
            
            if change > CONSISTENCY_RULES["max_single_change"]:
                violations.append({
                    "type": "excessive_single_change",
                    "timestamp": curr_time.isoformat(),
                    "emotion": emotion_name,
                    "change": change,
                    "from_value": prev_val,
                    "to_value": curr_val,
                })
        
        # Check bounds
        for timestamp, value in values:
            if not (CONSISTENCY_RULES["min_emotion_value"] <= value <= CONSISTENCY_RULES["max_emotion_value"]):
                violations.append({
                    "type": "bounds_violation",
                    "timestamp": timestamp.isoformat(),
                    "emotion": emotion_name,
                    "value": value,
                })
            
            if value != value:  # NaN check
                violations.append({
                    "type": "nan_value",
                    "timestamp": timestamp.isoformat(),
                    "emotion": emotion_name,
                })
        
        # Check floor violations
        floors = self.snapshots[0].state._EMOTION_FLOORS
        floor = floors.get(emotion_name, 0.1)
        tolerance = CONSISTENCY_RULES["floor_violation_tolerance"]
        
        for timestamp, value in values:
            if value < floor - tolerance:
                violations.append({
                    "type": "floor_violation",
                    "timestamp": timestamp.isoformat(),
                    "emotion": emotion_name,
                    "value": value,
                    "floor": floor,
                })
        
        is_consistent = len(violations) == 0
        
        return EmotionDriftReport(
            emotion_name=emotion_name,
            start_value=start_value,
            end_value=end_value,
            min_value=min_value,
            max_value=max_value,
            drift_amount=drift_amount,
            is_consistent=is_consistent,
            violations=violations,
        )
    
    def detect_anomalies(self) -> List[Dict]:
        """
        Detect unusual patterns in emotional state history.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        if len(self.snapshots) < 3:
            return anomalies
        
        # Get all emotion names
        emotion_names = list(self.snapshots[0].state.get_all_emotions().keys())
        
        for emotion_name in emotion_names:
            values = [getattr(s.state, emotion_name) for s in self.snapshots]
            
            # Statistical anomaly detection
            if len(values) >= 3:
                avg = mean(values)
                try:
                    std = stdev(values)
                    
                    # Check for outliers (>3 sigma)
                    for i, value in enumerate(values):
                        if std > 0 and abs(value - avg) > 3 * std:
                            anomalies.append({
                                "type": "statistical_outlier",
                                "timestamp": self.snapshots[i].timestamp.isoformat(),
                                "emotion": emotion_name,
                                "value": value,
                                "mean": avg,
                                "std": std,
                                "z_score": (value - avg) / std,
                            })
                except:
                    pass  # stdev can fail with insufficient data
            
            # Check for sudden spikes/drops
            for i in range(1, len(values)):
                change = abs(values[i] - values[i-1])
                if change > CONSISTENCY_RULES["max_single_change"]:
                    anomalies.append({
                        "type": "sudden_change",
                        "timestamp": self.snapshots[i].timestamp.isoformat(),
                        "emotion": emotion_name,
                        "change": change,
                        "from_value": values[i-1],
                        "to_value": values[i],
                    })
        
        return anomalies
    
    def generate_decay_report(self) -> Dict[str, Any]:
        """
        Analyze decay rates for each emotion.
        
        Returns:
            Dict with decay analysis
        """
        if len(self.snapshots) < 2:
            return {"error": "Insufficient snapshots"}
        
        decay_analysis = {}
        
        for emotion_name in self.snapshots[0].state.get_all_emotions().keys():
            values = []
            for snapshot in self.snapshots:
                if snapshot.trigger == "decay":
                    values.append((snapshot.timestamp, getattr(snapshot.state, emotion_name)))
            
            if len(values) >= 2:
                # Calculate average decay rate
                time_span = (values[-1][0] - values[0][0]).total_seconds() / 3600  # hours
                value_change = values[-1][1] - values[0][1]
                
                if time_span > 0:
                    decay_rate = value_change / time_span
                    
                    decay_analysis[emotion_name] = {
                        "hours_observed": time_span,
                        "total_change": value_change,
                        "decay_rate_per_hour": decay_rate,
                        "start_value": values[0][1],
                        "end_value": values[-1][1],
                    }
        
        return decay_analysis
    
    def get_emotion_history(self, emotion_name: str) -> List[Tuple[datetime, float]]:
        """
        Get history for a specific emotion.
        
        Args:
            emotion_name: Name of emotion
            
        Returns:
            List of (timestamp, value) tuples
        """
        return [
            (s.timestamp, getattr(s.state, emotion_name))
            for s in self.snapshots
        ]
    
    def clear_history(self):
        """Clear all snapshot history."""
        self.snapshots.clear()
        self.check_results.clear()


async def verify_emotion_consistency(
    persistence: EmotionPersistence,
    hours_of_history: float = 24
) -> Dict[str, Any]:
    """
    Verify emotional state has remained consistent over time.
    
    Args:
        persistence: EmotionPersistence instance
        hours_of_history: How far back to check
        
    Returns:
        Dict with consistency report
    """
    # Load recent states from database
    history = persistence.get_interaction_history(limit=1000)
    
    if len(history) < 2:
        return {"status": "insufficient_data", "message": "Need more history"}
    
    # Analyze state progression
    violations = []
    
    for i in range(1, len(history)):
        prev = EmotionalState.from_dict(history[i-1]["state_after"])
        curr = EmotionalState.from_dict(history[i]["state_after"])
        
        # Check each emotion
        for emotion_name in prev.get_all_emotions().keys():
            prev_val = getattr(prev, emotion_name)
            curr_val = getattr(curr, emotion_name)
            change = abs(curr_val - prev_val)
            
            if change > CONSISTENCY_RULES["max_single_change"]:
                violations.append({
                    "timestamp": history[i]["timestamp"],
                    "emotion": emotion_name,
                    "change": change,
                    "from_value": prev_val,
                    "to_value": curr_val,
                    "violation": "excessive_single_change",
                })
    
    return {
        "status": "consistent" if not violations else "violations_found",
        "violations": violations,
        "total_checks": len(history) - 1,
        "violation_count": len(violations),
    }


def verify_emotion_persistence_integrity(
    persistence: EmotionPersistence
) -> Dict[str, Any]:
    """
    Verify database integrity for emotion storage.
    
    Args:
        persistence: EmotionPersistence instance
        
    Returns:
        Dict with integrity report
    """
    try:
        # Try to load latest state
        state = persistence.load_latest_state()
        
        if state is None:
            return {"status": "no_state", "valid": False}
        
        # Verify all emotions in valid range
        issues = []
        for name, value in state.get_all_emotions().items():
            if not (0 <= value <= 1):
                issues.append(f"{name}={value} out of range [0,1]")
            if value != value:  # NaN check
                issues.append(f"{name} is NaN")
        
        return {
            "status": "valid" if not issues else "invalid",
            "valid": not issues,
            "issues": issues,
            "state_timestamp": state.last_updated.isoformat(),
        }
    except Exception as e:
        return {"status": "error", "valid": False, "error": str(e)}


async def verify_decay_behavior(
    initial_state: EmotionalState,
    current_state: EmotionalState,
    hours_elapsed: float
) -> Dict[str, Any]:
    """
    Verify that emotion decay behaves correctly over time.
    
    Args:
        initial_state: Initial emotional state
        current_state: Current emotional state
        hours_elapsed: Hours since initial state
        
    Returns:
        Dict with decay verification results
    """
    decay = DecaySystem()
    expected_state = decay.simulate_offline_decay(
        initial_state,
        int(hours_elapsed * 3600)
    )
    
    discrepancies = []
    for emotion_name in initial_state.get_all_emotions().keys():
        expected = getattr(expected_state, emotion_name)
        actual = getattr(current_state, emotion_name)
        diff = abs(expected - actual)
        
        if diff > 0.05:  # 5% tolerance
            discrepancies.append({
                "emotion": emotion_name,
                "expected": expected,
                "actual": actual,
                "difference": diff,
            })
    
    return {
        "status": "correct" if not discrepancies else "discrepancy",
        "hours_elapsed": hours_elapsed,
        "discrepancies": discrepancies,
        "discrepancy_count": len(discrepancies),
    }


async def main():
    """Demo emotion monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo emotion monitor")
    parser.add_argument("--duration", type=float, default=0.1, help="Duration in hours")
    
    args = parser.parse_args()
    
    print("Emotion Stability Monitor Demo")
    print("-" * 50)
    
    # Create mock persistence
    persistence = EmotionPersistence()
    monitor = EmotionStabilityMonitor(persistence)
    
    # Simulate some state changes
    print("Recording state snapshots...")
    
    base_time = datetime.now()
    
    for i in range(10):
        state = EmotionalState(
            loneliness=0.5 + (i * 0.02),
            excitement=0.6 - (i * 0.01),
            affection=0.4 + (i * 0.03),
        )
        timestamp = base_time + timedelta(minutes=i * 5)
        await monitor.record_state(state, trigger="scheduled", timestamp=timestamp)
        print(f"  Snapshot {i+1}: loneliness={state.loneliness:.2f}, "
              f"excitement={state.excitement:.2f}")
    
    print("-" * 50)
    
    # Check consistency
    print("\nConsistency Check:")
    reports = monitor.check_consistency()
    for emotion_name, report in reports.items():
        status = "✓" if report.is_consistent else "✗"
        print(f"  {status} {emotion_name}: drift={report.drift_amount:.3f}, "
              f"violations={len(report.violations)}")
    
    # Detect anomalies
    print("\nAnomaly Detection:")
    anomalies = monitor.detect_anomalies()
    if anomalies:
        for anomaly in anomalies[:5]:
            print(f"  ! {anomaly['type']}: {anomaly.get('emotion', 'N/A')} "
                  f"at {anomaly['timestamp']}")
    else:
        print("  No anomalies detected")
    
    print("\nDemo complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
