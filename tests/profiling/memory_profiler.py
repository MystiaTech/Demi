"""Memory profiler for tracking process and Python-level memory usage.

Uses tracemalloc for detailed Python allocation tracking and psutil for
process-level memory metrics.
"""

import gc
import sys
import tracemalloc
import psutil
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import os


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time.
    
    Attributes:
        timestamp: When the snapshot was taken
        rss_mb: Resident set size in MB (actual physical memory used)
        vms_mb: Virtual memory size in MB
        objects_count: Number of objects tracked by GC
        python_allocated_mb: Python heap allocation from tracemalloc
        top_allocations: Top memory consumers
    """
    timestamp: datetime
    rss_mb: float
    vms_mb: float
    objects_count: int = 0
    python_allocated_mb: float = 0.0
    top_allocations: List[Dict[str, Any]] = field(default_factory=list)
    gc_generations: Tuple[int, int, int] = field(default_factory=lambda: (0, 0, 0))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary format."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "rss_mb": self.rss_mb,
            "vms_mb": self.vms_mb,
            "objects_count": self.objects_count,
            "python_allocated_mb": self.python_allocated_mb,
            "gc_generations": list(self.gc_generations),
        }
    
    def __str__(self) -> str:
        return (f"MemorySnapshot({self.rss_mb:.1f}MB RSS, "
                f"{self.vms_mb:.1f}MB VMS, "
                f"{self.objects_count} objects)")


class MemoryProfiler:
    """Memory profiler for tracking process and Python-level memory usage.
    
    Integrates with tracemalloc for Python-level allocation tracking and
    psutil for process-level metrics. Supports threshold-based alerting
    and historical snapshot storage.
    
    Attributes:
        warning_threshold_mb: Memory threshold for warnings (default 8192 = 8GB)
        critical_threshold_mb: Critical memory threshold (default 10240 = 10GB)
    
    Example:
        profiler = MemoryProfiler()
        profiler.start_profiling()
        
        snapshot = profiler.take_snapshot()
        print(f"Memory: {snapshot.rss_mb}MB")
        
        allocations = profiler.get_top_allocations(10)
        for alloc in allocations:
            print(f"{alloc['file']}: {alloc['size_mb']:.1f}MB")
        
        profiler.stop_profiling()
    """
    
    def __init__(
        self,
        warning_threshold_mb: float = 8192,
        critical_threshold_mb: float = 10240,
    ):
        """Initialize memory profiler.
        
        Args:
            warning_threshold_mb: Alert threshold for warnings (default 8GB)
            critical_threshold_mb: Critical alert threshold (default 10GB)
        """
        self.warning_threshold_mb = warning_threshold_mb
        self.critical_threshold_mb = critical_threshold_mb
        
        self._process = psutil.Process(os.getpid())
        self._snapshots: List[MemorySnapshot] = []
        self._profiling = False
        self._profiling_task: Optional[asyncio.Task] = None
        self._collection_interval = 60
        
    def start_profiling(self, interval_seconds: int = 60) -> None:
        """Begin memory profiling.
        
        Starts tracemalloc tracking for Python-level allocation tracking.
        
        Args:
            interval_seconds: Interval for background snapshot collection
        """
        if self._profiling:
            return
            
        # Start tracemalloc
        tracemalloc.start()
        
        self._profiling = True
        self._collection_interval = interval_seconds
        
    def stop_profiling(self) -> None:
        """Stop memory profiling and cleanup resources."""
        if not self._profiling:
            return
            
        self._profiling = False
        
        # Stop tracemalloc
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        
        # Cancel any background task
        if self._profiling_task and not self._profiling_task.done():
            self._profiling_task.cancel()
    
    def take_snapshot(self) -> MemorySnapshot:
        """Capture current memory state.
        
        Returns:
            MemorySnapshot with current memory metrics
        """
        # Force garbage collection for accurate count
        gc.collect()
        
        # Get process memory
        memory_info = self._process.memory_info()
        rss_mb = memory_info.rss / (1024 * 1024)
        vms_mb = memory_info.vms / (1024 * 1024)
        
        # Get Python object count
        objects_count = len(gc.get_objects())
        
        # Get GC generation counts
        gc_generations = gc.get_count() if hasattr(gc, 'get_count') else (0, 0, 0)
        
        # Get Python allocations from tracemalloc
        python_allocated_mb = 0.0
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            python_allocated_mb = current / (1024 * 1024)
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=rss_mb,
            vms_mb=vms_mb,
            objects_count=objects_count,
            python_allocated_mb=python_allocated_mb,
            gc_generations=gc_generations,
        )
        
        self._snapshots.append(snapshot)
        
        # Keep only last 1000 snapshots
        if len(self._snapshots) > 1000:
            self._snapshots = self._snapshots[-1000:]
            
        return snapshot
    
    def get_top_allocations(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top memory allocations by size.
        
        Args:
            n: Number of top allocations to return
            
        Returns:
            List of allocation dicts with file, size_mb, and count
        """
        if not tracemalloc.is_tracing():
            return []
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:n]
        
        allocations = []
        for stat in top_stats:
            file_info = stat.traceback.format()[-1] if stat.traceback else "unknown"
            allocations.append({
                "file": file_info,
                "size_mb": stat.size / (1024 * 1024),
                "count": stat.count,
            })
        
        return allocations
    
    def compare_snapshots(
        self,
        before: MemorySnapshot,
        after: MemorySnapshot
    ) -> Dict[str, Any]:
        """Compare two memory snapshots and return differences.
        
        Args:
            before: Baseline snapshot
            after: Comparison snapshot
            
        Returns:
            Dictionary with diff statistics
        """
        rss_diff = after.rss_mb - before.rss_mb
        vms_diff = after.vms_mb - before.vms_mb
        objects_diff = after.objects_count - before.objects_count
        python_diff = after.python_allocated_mb - before.python_allocated_mb
        
        hours_elapsed = (after.timestamp - before.timestamp).total_seconds() / 3600
        
        # Calculate growth rates
        rss_growth_rate = (rss_diff / hours_elapsed) if hours_elapsed > 0 else 0
        rss_growth_percent = (rss_diff / before.rss_mb * 100) if before.rss_mb > 0 else 0
        
        return {
            "rss_diff_mb": rss_diff,
            "vms_diff_mb": vms_diff,
            "objects_diff": objects_diff,
            "python_diff_mb": python_diff,
            "hours_elapsed": hours_elapsed,
            "rss_growth_rate_mb_per_hour": rss_growth_rate,
            "rss_growth_percent": rss_growth_percent,
            "timestamp_before": before.timestamp.isoformat(),
            "timestamp_after": after.timestamp.isoformat(),
        }
    
    def check_thresholds(self, snapshot: MemorySnapshot) -> List[str]:
        """Check snapshot against warning/critical thresholds.
        
        Args:
            snapshot: Memory snapshot to check
            
        Returns:
            List of alert messages (empty if no alerts)
        """
        alerts = []
        
        if snapshot.rss_mb >= self.critical_threshold_mb:
            alerts.append(
                f"CRITICAL: Memory usage {snapshot.rss_mb:.0f}MB exceeds "
                f"critical threshold {self.critical_threshold_mb:.0f}MB"
            )
        elif snapshot.rss_mb >= self.warning_threshold_mb:
            alerts.append(
                f"WARNING: Memory usage {snapshot.rss_mb:.0f}MB exceeds "
                f"warning threshold {self.warning_threshold_mb:.0f}MB"
            )
            
        return alerts
    
    def get_object_type_counts(self, limit: int = 50) -> Dict[str, int]:
        """Get counts of objects by type.
        
        Useful for leak detection by tracking growth of specific types.
        
        Args:
            limit: Maximum number of types to return
            
        Returns:
            Dictionary mapping type names to counts
        """
        gc.collect()
        counts = defaultdict(int)
        
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            counts[obj_type] += 1
        
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit])
    
    def generate_report(self, format: str = "text") -> str:
        """Generate memory profiling report.
        
        Args:
            format: Report format ("text" or "html")
            
        Returns:
            Report content as string
        """
        if not self._snapshots:
            return "No snapshots available"
        
        recent = self._snapshots[-10:]
        latest = recent[-1]
        
        if format == "html":
            return self._generate_html_report(recent, latest)
        else:
            return self._generate_text_report(recent, latest)
    
    def _generate_text_report(
        self,
        snapshots: List[MemorySnapshot],
        latest: MemorySnapshot
    ) -> str:
        """Generate text format report."""
        lines = [
            "=" * 60,
            "Memory Profiling Report",
            "=" * 60,
            f"Generated: {datetime.now().isoformat()}",
            f"Snapshots: {len(self._snapshots)}",
            "",
            "Current Memory Usage:",
            f"  RSS: {latest.rss_mb:.1f} MB",
            f"  VMS: {latest.vms_mb:.1f} MB",
            f"  Python Allocated: {latest.python_allocated_mb:.1f} MB",
            f"  Objects: {latest.objects_count:,}",
            "",
        ]
        
        if len(snapshots) > 1:
            first = snapshots[0]
            growth = latest.rss_mb - first.rss_mb
            growth_pct = (growth / first.rss_mb * 100) if first.rss_mb > 0 else 0
            
            lines.extend([
                "Growth (last {} snapshots):".format(len(snapshots)),
                f"  RSS Growth: {growth:+.1f} MB ({growth_pct:+.1f}%)",
                f"  Objects Growth: {latest.objects_count - first.objects_count:+,}",
                "",
            ])
        
        # Top allocations
        top_allocs = self.get_top_allocations(5)
        if top_allocs:
            lines.extend([
                "Top Memory Allocations:",
            ])
            for i, alloc in enumerate(top_allocs, 1):
                lines.append(f"  {i}. {alloc['file']}: {alloc['size_mb']:.2f}MB ({alloc['count']} blocks)")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _generate_html_report(
        self,
        snapshots: List[MemorySnapshot],
        latest: MemorySnapshot
    ) -> str:
        """Generate HTML format report."""
        # Simple HTML report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Memory Profiling Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .metric {{ margin: 10px 0; }}
        .metric-label {{ font-weight: bold; }}
        .alert {{ color: #d9534f; }}
        .warning {{ color: #f0ad4e; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Memory Profiling Report</h1>
    <p>Generated: {datetime.now().isoformat()}</p>
    
    <h2>Current Memory Usage</h2>
    <div class="metric">
        <span class="metric-label">RSS:</span> {latest.rss_mb:.1f} MB
    </div>
    <div class="metric">
        <span class="metric-label">VMS:</span> {latest.vms_mb:.1f} MB
    </div>
    <div class="metric">
        <span class="metric-label">Python Allocated:</span> {latest.python_allocated_mb:.1f} MB
    </div>
    <div class="metric">
        <span class="metric-label">Objects:</span> {latest.objects_count:,}
    </div>
"""
        
        # Add top allocations table
        top_allocs = self.get_top_allocations(10)
        if top_allocs:
            html += """
    <h2>Top Memory Allocations</h2>
    <table>
        <tr>
            <th>File</th>
            <th>Size (MB)</th>
            <th>Count</th>
        </tr>
"""
            for alloc in top_allocs:
                html += f"""        <tr>
            <td>{alloc['file']}</td>
            <td>{alloc['size_mb']:.2f}</td>
            <td>{alloc['count']}</td>
        </tr>
"""
            html += "    </table>"
        
        html += """
</body>
</html>
"""
        return html
    
    async def _profiling_loop(self, interval_seconds: int) -> None:
        """Background loop for periodic snapshot collection."""
        try:
            while self._profiling:
                snapshot = self.take_snapshot()
                
                # Check thresholds
                alerts = self.check_thresholds(snapshot)
                for alert in alerts:
                    print(f"[MEMORY ALERT] {alert}")
                
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            pass
    
    def get_growth_rate(self, hours: float = 24) -> float:
        """Calculate memory growth rate over time.
        
        Uses linear regression on historical data.
        
        Args:
            hours: Time window for growth calculation
            
        Returns:
            Growth rate as percentage per hour
        """
        if len(self._snapshots) < 2:
            return 0.0
        
        # Filter snapshots within time window
        cutoff = datetime.now() - __import__('datetime').timedelta(hours=hours)
        recent = [s for s in self._snapshots if s.timestamp >= cutoff]
        
        if len(recent) < 2:
            return 0.0
        
        # Simple linear regression
        x = list(range(len(recent)))
        y = [s.rss_mb for s in recent]
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Convert to % per hour
        baseline = recent[0].rss_mb if recent[0].rss_mb > 0 else 1
        hours_elapsed = (recent[-1].timestamp - recent[0].timestamp).total_seconds() / 3600
        
        if hours_elapsed <= 0:
            return 0.0
        
        growth_per_hour = slope * (len(recent) / hours_elapsed)
        growth_percent = (growth_per_hour / baseline) * 100
        
        return growth_percent
