"""Memory profiling and leak detection module for Demi.

Provides tools for memory profiling, leak detection, and object tracking
to ensure Demi stays below 10GB sustained memory usage.

Example:
    from tests.profiling import MemoryProfiler, LeakDetector, ObjectTracker
    
    profiler = MemoryProfiler()
    profiler.start_profiling()
    
    snapshot = profiler.take_snapshot()
    print(f"Memory: {snapshot.rss_mb}MB")
"""

from tests.profiling.memory_profiler import (
    MemoryProfiler,
    MemorySnapshot,
)
from tests.profiling.leak_detector import (
    LeakDetector,
    GrowthAnalyzer,
)
from tests.profiling.tracked_object import (
    TrackedObject,
    ObjectTracker,
)

__all__ = [
    # Memory profiling
    "MemoryProfiler",
    "MemorySnapshot",
    # Leak detection
    "LeakDetector",
    "GrowthAnalyzer",
    # Object tracking
    "TrackedObject",
    "ObjectTracker",
]

__version__ = "1.0.0"
