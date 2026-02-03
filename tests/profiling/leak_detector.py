"""Memory leak detection using statistical analysis.

Detects leaks by analyzing memory growth patterns over time, filtering out
normal fluctuations to reduce false positives.
"""

import gc
import statistics
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

from tests.profiling.memory_profiler import MemorySnapshot


@dataclass
class LeakFinding:
    """A detected potential memory leak.
    
    Attributes:
        detected_at: When the leak was detected
        growth_mb: Absolute growth in MB
        growth_percent: Percentage growth
        growth_rate_mb_per_hour: Calculated growth rate
        confidence: Confidence score (0-1)
        pattern: Description of the leak pattern
    """
    detected_at: datetime
    growth_mb: float
    growth_percent: float
    growth_rate_mb_per_hour: float
    confidence: float
    pattern: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "detected_at": self.detected_at.isoformat(),
            "growth_mb": self.growth_mb,
            "growth_percent": self.growth_percent,
            "growth_rate_mb_per_hour": self.growth_rate_mb_per_hour,
            "confidence": self.confidence,
            "pattern": self.pattern,
        }


class GrowthAnalyzer:
    """Analyzes memory growth patterns with statistical methods.
    
    Uses linear regression and statistical variance to distinguish
    between normal fluctuations and actual leak patterns.
    """
    
    def __init__(
        self,
        min_observations: int = 6,
        variance_threshold: float = 0.3,
    ):
        """Initialize growth analyzer.
        
        Args:
            min_observations: Minimum observations for trend analysis
            variance_threshold: Max coefficient of variation for stable memory
        """
        self.min_observations = min_observations
        self.variance_threshold = variance_threshold
    
    def calculate_slope(self, values: List[float]) -> float:
        """Calculate slope using simple linear regression.
        
        Args:
            values: List of memory values over time
            
        Returns:
            Slope (positive = growth, negative = decline)
        """
        n = len(values)
        if n < 2:
            return 0.0
        
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(xi * yi for xi, yi in zip(x, values))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope
    
    def calculate_coefficient_of_variation(self, values: List[float]) -> float:
        """Calculate coefficient of variation (CV).
        
        CV = std_dev / mean, used to measure relative variability.
        Low CV indicates stable values, high CV indicates fluctuation.
        
        Args:
            values: List of values
            
        Returns:
            Coefficient of variation (0-1 typically)
        """
        if len(values) < 2:
            return 0.0
        
        mean = statistics.mean(values)
        if mean == 0:
            return 0.0
        
        try:
            std_dev = statistics.stdev(values)
            return std_dev / mean
        except statistics.StatisticsError:
            return 0.0
    
    def is_consistent_growth(
        self,
        values: List[float],
        threshold_percent: float = 5.0
    ) -> bool:
        """Check if values show consistent growth pattern.
        
        Args:
            values: Memory values over time
            threshold_percent: Minimum growth percent to consider
            
        Returns:
            True if consistent growth detected
        """
        if len(values) < self.min_observations:
            return False
        
        slope = self.calculate_slope(values)
        if slope <= 0:
            return False
        
        # Calculate growth percent
        growth = values[-1] - values[0]
        growth_percent = (growth / values[0] * 100) if values[0] > 0 else 0
        
        if growth_percent < threshold_percent:
            return False
        
        # Check for consistent upward trend
        # Count how many consecutive periods show growth
        growth_periods = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
        consistency = growth_periods / (len(values) - 1)
        
        # Require at least 60% of periods to show growth
        return consistency >= 0.6


class LeakDetector:
    """Automated memory leak detection using statistical analysis.
    
    Detects leaks by:
    1. Trend analysis (consistent growth over time)
    2. Object accumulation (growing counts of specific types)
    3. Statistical confidence scoring to reduce false positives
    
    Example:
        detector = LeakDetector()
        detector.start_monitoring()
        
        # Record snapshots periodically
        detector.record_snapshot("baseline")
        # ... do work ...
        detector.record_snapshot("after_work")
        
        if detector.check_for_leaks():
            findings = detector.generate_leak_report()
            print(f"Leak detected: {findings}")
    """
    
    def __init__(
        self,
        min_growth_threshold_mb: float = 50.0,
        min_growth_percent: float = 5.0,
        observation_periods: int = 6,
        period_minutes: float = 60.0,
        false_positive_filter: bool = True,
    ):
        """Initialize leak detector.
        
        Args:
            min_growth_threshold_mb: Minimum absolute growth to flag as leak
            min_growth_percent: Minimum percentage growth to flag as leak
            observation_periods: Number of periods for trend analysis
            period_minutes: Duration of each observation period
            false_positive_filter: Enable statistical filtering to reduce false positives
        """
        self.min_growth_threshold_mb = min_growth_threshold_mb
        self.min_growth_percent = min_growth_percent
        self.observation_periods = observation_periods
        self.period_minutes = period_minutes
        self.false_positive_filter = false_positive_filter
        
        self._observations: deque = deque(maxlen=observation_periods + 2)
        self._tagged_snapshots: Dict[str, MemorySnapshot] = {}
        self._suspected_leaks: List[LeakFinding] = []
        self._analyzer = GrowthAnalyzer(min_observations=observation_periods)
        self._monitoring = False
        self._baseline_established = False
        self._baseline_memory = 0.0
    
    def start_monitoring(self) -> None:
        """Begin leak monitoring."""
        self._monitoring = True
        self._observations.clear()
        self._suspected_leaks.clear()
    
    def stop_monitoring(self) -> None:
        """Stop leak monitoring."""
        self._monitoring = False
    
    def record_snapshot(self, label: str, snapshot: Optional[MemorySnapshot] = None) -> None:
        """Record a tagged snapshot.
        
        Args:
            label: Tag for this snapshot (e.g., "baseline", "after_task")
            snapshot: Optional snapshot, will take new one if not provided
        """
        from tests.profiling.memory_profiler import MemoryProfiler
        
        if snapshot is None:
            profiler = MemoryProfiler()
            snapshot = profiler.take_snapshot()
        
        self._tagged_snapshots[label] = snapshot
    
    def add_observation(self, snapshot: MemorySnapshot) -> None:
        """Add a memory observation for analysis.
        
        Args:
            snapshot: Memory snapshot to add
        """
        self._observations.append(snapshot)
        
        # Establish baseline on first observation
        if not self._baseline_established:
            self._baseline_memory = snapshot.rss_mb
            self._baseline_established = True
        
        # Check for leaks if we have enough data
        if len(self._observations) >= self.observation_periods:
            self._analyze_for_leaks()
    
    def _analyze_for_leaks(self) -> None:
        """Analyze observations for leak patterns."""
        if len(self._observations) < self.observation_periods:
            return
        
        # Get recent observations
        recent = list(self._observations)[-self.observation_periods:]
        
        memory_values = [obs.rss_mb for obs in recent]
        
        # Use growth analyzer for statistical detection
        if not self._analyzer.is_consistent_growth(
            memory_values,
            threshold_percent=self.min_growth_percent
        ):
            return
        
        # Calculate statistics
        slope = self._analyzer.calculate_slope(memory_values)
        total_growth_mb = memory_values[-1] - memory_values[0]
        growth_percent = (total_growth_mb / memory_values[0] * 100) if memory_values[0] > 0 else 0
        
        # Calculate growth rate per hour
        hours_elapsed = (recent[-1].timestamp - recent[0].timestamp).total_seconds() / 3600
        growth_rate = total_growth_mb / hours_elapsed if hours_elapsed > 0 else 0
        
        # Apply false positive filtering
        if self.false_positive_filter:
            cv = self._analyzer.calculate_coefficient_of_variation(memory_values)
            
            # High variance with low growth is likely normal fluctuation
            if cv > 0.5 and growth_percent < 10:
                return
            
            # Require minimum absolute growth
            if total_growth_mb < self.min_growth_threshold_mb:
                return
        
        # Check for leak conditions
        is_leak = (
            slope > 0 and  # Consistent growth
            total_growth_mb > self.min_growth_threshold_mb and
            growth_percent > self.min_growth_percent
        )
        
        if is_leak:
            # Calculate confidence based on consistency
            growth_periods = sum(1 for i in range(1, len(memory_values)) 
                               if memory_values[i] > memory_values[i-1])
            consistency = growth_periods / (len(memory_values) - 1)
            confidence = min(0.95, consistency * 0.8 + 0.2)
            
            leak_finding = LeakFinding(
                detected_at=datetime.now(),
                growth_mb=total_growth_mb,
                growth_percent=growth_percent,
                growth_rate_mb_per_hour=growth_rate,
                confidence=confidence,
                pattern="consistent_growth",
            )
            
            # Avoid duplicate reports
            if not self._suspected_leaks or \
               abs(self._suspected_leaks[-1].growth_mb - total_growth_mb) > 1:
                self._suspected_leaks.append(leak_finding)
    
    def check_for_leaks(self) -> bool:
        """Check if any leak has been detected.
        
        Returns:
            True if a leak has been detected
        """
        return len(self._suspected_leaks) > 0
    
    def get_suspected_leaks(self) -> List[LeakFinding]:
        """Get list of suspected memory leaks.
        
        Returns:
            List of LeakFinding objects
        """
        return self._suspected_leaks.copy()
    
    def clear_suspected_leaks(self) -> None:
        """Clear suspected leaks list."""
        self._suspected_leaks.clear()
    
    def analyze_growth(
        self,
        baseline_counts: Dict[str, int],
        current_counts: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """Analyze growth in object counts by type.
        
        Args:
            baseline_counts: Baseline object counts
            current_counts: Current object counts
            
        Returns:
            List of growing object types
        """
        growth_items = []
        
        for obj_type, current_count in current_counts.items():
            baseline_count = baseline_counts.get(obj_type, 0)
            growth = current_count - baseline_count
            
            if baseline_count > 0:
                growth_percent = (growth / baseline_count) * 100
            else:
                growth_percent = float('inf') if growth > 0 else 0
            
            # Flag significant growth
            if growth > 100 or (growth_percent > 50 and growth > 10):
                growth_items.append({
                    "type": obj_type,
                    "baseline": baseline_count,
                    "current": current_count,
                    "growth": growth,
                    "growth_percent": growth_percent if growth_percent != float('inf') else None,
                })
        
        # Sort by absolute growth
        growth_items.sort(key=lambda x: x["growth"], reverse=True)
        return growth_items[:20]  # Top 20 growing types
    
    def detect_reference_cycles(self) -> List[Dict[str, Any]]:
        """Detect objects involved in reference cycles.
        
        Returns:
            List of cycle information dicts
        """
        gc.collect()  # Clean up first
        
        # Get objects that can't be collected
        unreachable = gc.collect(2)  # Full collection
        
        # Get garbage (objects with cycles)
        cycles = []
        garbage = getattr(gc, 'garbage', [])
        for item in garbage:
            cycles.append({
                "type": type(item).__name__,
                "repr": repr(item)[:100],  # Truncated
            })
        
        return cycles
    
    def calculate_growth_rate(self, hours: Optional[float] = None) -> Dict[str, float]:
        """Calculate memory growth rate.
        
        Args:
            hours: Time window in hours (None = all observations)
            
        Returns:
            Dictionary with growth statistics
        """
        if len(self._observations) < 2:
            return {
                "growth_rate_mb_per_hour": 0.0,
                "growth_percent_per_hour": 0.0,
                "projected_7day_growth_mb": 0.0,
                "projected_7day_growth_percent": 0.0,
            }
        
        observations = list(self._observations)
        
        # Filter by time window if specified
        if hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            observations = [obs for obs in observations if obs.timestamp >= cutoff]
        
        if len(observations) < 2:
            return {
                "growth_rate_mb_per_hour": 0.0,
                "growth_percent_per_hour": 0.0,
                "projected_7day_growth_mb": 0.0,
                "projected_7day_growth_percent": 0.0,
            }
        
        first = observations[0]
        last = observations[-1]
        
        hours_elapsed = (last.timestamp - first.timestamp).total_seconds() / 3600
        if hours_elapsed <= 0:
            hours_elapsed = 0.001  # Avoid division by zero
        
        growth_mb = last.rss_mb - first.rss_mb
        growth_rate_mb_per_hour = growth_mb / hours_elapsed
        
        baseline = first.rss_mb if first.rss_mb > 0 else 1
        growth_percent = (growth_mb / baseline) * 100
        growth_percent_per_hour = growth_percent / hours_elapsed
        
        # Project to 7 days
        hours_in_7days = 24 * 7
        projected_7day_growth_mb = growth_rate_mb_per_hour * hours_in_7days
        projected_7day_growth_percent = growth_percent_per_hour * hours_in_7days
        
        return {
            "growth_rate_mb_per_hour": growth_rate_mb_per_hour,
            "growth_percent_per_hour": growth_percent_per_hour,
            "projected_7day_growth_mb": projected_7day_growth_mb,
            "projected_7day_growth_percent": projected_7day_growth_percent,
            "baseline_mb": baseline,
            "current_mb": last.rss_mb,
            "hours_elapsed": hours_elapsed,
        }
    
    def generate_leak_report(self) -> Dict[str, Any]:
        """Generate comprehensive leak analysis report.
        
        Returns:
            Dictionary with detailed leak findings
        """
        if not self._observations:
            return {
                "status": "insufficient_data",
                "message": "No observations yet",
            }
        
        recent = list(self._observations)[-10:] if len(self._observations) >= 10 else list(self._observations)
        
        # Calculate statistics
        memory_values = [obs.rss_mb for obs in recent]
        avg_memory = sum(memory_values) / len(memory_values)
        max_memory = max(memory_values)
        min_memory = min(memory_values)
        
        # Get growth rate
        growth_stats = self.calculate_growth_rate()
        
        # Determine status
        status = "no_leak"
        if self.check_for_leaks():
            status = "leak_detected"
        elif growth_stats["projected_7day_growth_percent"] > 5:
            status = "warning_high_growth"
        elif growth_stats["projected_7day_growth_percent"] > 2:
            status = "elevated_growth"
        
        return {
            "status": status,
            "observation_count": len(self._observations),
            "suspected_leaks_count": len(self._suspected_leaks),
            "recent_memory_stats": {
                "average_mb": avg_memory,
                "min_mb": min_memory,
                "max_mb": max_memory,
                "range_mb": max_memory - min_memory,
            },
            "growth_projection": growth_stats,
            "suspected_leaks": [leak.to_dict() for leak in self._suspected_leaks[-5:]],
            "monitoring_active": self._monitoring,
            "baseline_established": self._baseline_established,
        }
