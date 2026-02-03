"""Object tracking using weak references.

Provides lifecycle tracking for objects without preventing garbage collection.
Useful for detecting objects that should have been cleaned up but weren't.
"""

import gc
import weakref
import sys
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class TrackedObject:
    """A tracked object for memory monitoring.
    
    Uses weak references to track object lifecycle without preventing
    garbage collection.
    
    Attributes:
        name: Human-readable identifier for the object
        obj_ref: Weak reference to the tracked object
        initial_size_mb: Estimated size when tracking started
        creation_time: When tracking started
        snapshots: History of size observations
        label: Optional category label
        metadata: Additional tracking metadata
    
    Example:
        obj = {"data": "large payload" * 1000}
        tracked = TrackedObject("my_data", weakref.ref(obj), 0.1, datetime.now())
        
        print(tracked.is_alive)  # True
        del obj
        gc.collect()
        print(tracked.is_alive)  # False
    """
    name: str
    obj_ref: weakref.ref
    initial_size_mb: float
    creation_time: datetime
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_alive(self) -> bool:
        """Check if the tracked object still exists.
        
        Returns:
            True if object hasn't been garbage collected
        """
        return self.obj_ref() is not None
    
    def get_object(self) -> Optional[Any]:
        """Get the actual object if it still exists.
        
        Returns:
            The object or None if GC'd
        """
        return self.obj_ref()
    
    def current_size_estimate(self) -> float:
        """Estimate current size using heuristics if object is alive.
        
        Returns:
            Estimated size in MB
        """
        obj = self.obj_ref()
        if obj is None:
            return 0.0
        
        try:
            return sys.getsizeof(obj) / (1024 * 1024)
        except (TypeError, AttributeError):
            return self.initial_size_mb
    
    def record_snapshot(self) -> Dict[str, Any]:
        """Record a size snapshot.
        
        Returns:
            Snapshot data dictionary
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "is_alive": self.is_alive,
            "size_estimate_mb": self.current_size_estimate(),
        }
        self.snapshots.append(snapshot)
        return snapshot
    
    def get_referrers(self) -> List[Any]:
        """Find objects holding references to the tracked object.
        
        Returns:
            List of referrer objects (empty if object is dead)
        """
        obj = self.obj_ref()
        if obj is None:
            return []
        
        # Get referrers but filter out the get_referrers frame
        referrers = gc.get_referrers(obj)
        
        # Filter out the current frame and the list itself
        filtered = [
            ref for ref in referrers
            if not isinstance(ref, type(sys._getframe())) and ref is not referrers
        ]
        
        return filtered
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary with tracking information
        """
        return {
            "name": self.name,
            "is_alive": self.is_alive,
            "initial_size_mb": self.initial_size_mb,
            "current_size_mb": self.current_size_estimate(),
            "creation_time": self.creation_time.isoformat(),
            "age_seconds": (datetime.now() - self.creation_time).total_seconds(),
            "snapshot_count": len(self.snapshots),
            "label": self.label,
            "metadata": self.metadata,
        }


class ObjectTracker:
    """Track multiple objects and analyze lifecycle patterns.
    
    Manages a collection of TrackedObject instances with grouping
    and analysis capabilities.
    
    Example:
        tracker = ObjectTracker()
        
        # Track some objects
        obj1 = LargeObject()
        obj2 = LargeObject()
        
        tracker.track(obj1, "large_object", label="cache")
        tracker.track(obj2, "large_object_2", label="cache")
        
        # Later check how many are still alive
        print(tracker.get_alive_count("cache"))  # 2
        
        del obj1
        gc.collect()
        
        print(tracker.get_alive_count("cache"))  # 1
        
        # Find orphaned objects
        orphaned = tracker.get_orphaned_objects(min_age_seconds=60)
    """
    
    def __init__(self):
        """Initialize object tracker."""
        self._tracked: Dict[str, TrackedObject] = {}
        self._by_label: Dict[str, Set[str]] = defaultdict(set)
        self._tracking_id_counter = 0
    
    def track(
        self,
        obj: Any,
        name: Optional[str] = None,
        label: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register an object for tracking.
        
        Args:
            obj: Object to track
            name: Human-readable name (auto-generated if None)
            label: Category label for grouping
            metadata: Additional metadata
            
        Returns:
            Tracking ID for later reference
        """
        self._tracking_id_counter += 1
        tracking_id = f"tracked_{self._tracking_id_counter}"
        
        # Estimate initial size
        try:
            initial_size = sys.getsizeof(obj) / (1024 * 1024)
        except (TypeError, AttributeError):
            initial_size = 0.0
        
        # Create weak reference with callback for cleanup notification
        def on_destroyed(ref):
            # Object was garbage collected
            pass
        
        obj_ref = weakref.ref(obj, on_destroyed)
        
        tracked = TrackedObject(
            name=name or tracking_id,
            obj_ref=obj_ref,
            initial_size_mb=initial_size,
            creation_time=datetime.now(),
            label=label,
            metadata=metadata or {},
        )
        
        self._tracked[tracking_id] = tracked
        
        if label:
            self._by_label[label].add(tracking_id)
        
        return tracking_id
    
    def untrack(self, tracking_id: str) -> bool:
        """Remove object from tracking.
        
        Args:
            tracking_id: ID returned from track()
            
        Returns:
            True if object was being tracked
        """
        if tracking_id not in self._tracked:
            return False
        
        tracked = self._tracked[tracking_id]
        
        # Remove from label index
        if tracked.label:
            self._by_label[tracked.label].discard(tracking_id)
        
        del self._tracked[tracking_id]
        return True
    
    def get_tracked(self, tracking_id: str) -> Optional[TrackedObject]:
        """Get a tracked object by ID.
        
        Args:
            tracking_id: Tracking ID
            
        Returns:
            TrackedObject or None
        """
        return self._tracked.get(tracking_id)
    
    def get_alive_count(self, label: Optional[str] = None) -> int:
        """Count live objects.
        
        Args:
            label: Optional label to filter by
            
        Returns:
            Number of alive objects
        """
        if label:
            tracking_ids = self._by_label.get(label, set())
            return sum(
                1 for tid in tracking_ids
                if tid in self._tracked and self._tracked[tid].is_alive
            )
        else:
            return sum(1 for t in self._tracked.values() if t.is_alive)
    
    def get_dead_count(self, label: Optional[str] = None) -> int:
        """Count dead (GC'd) objects.
        
        Args:
            label: Optional label to filter by
            
        Returns:
            Number of dead objects
        """
        if label:
            tracking_ids = self._by_label.get(label, set())
            return sum(
                1 for tid in tracking_ids
                if tid in self._tracked and not self._tracked[tid].is_alive
            )
        else:
            return sum(1 for t in self._tracked.values() if not t.is_alive)
    
    def get_orphaned_objects(
        self,
        label: Optional[str] = None,
        min_age_seconds: float = 300,
    ) -> List[TrackedObject]:
        """Find objects that should be dead but are still alive.
        
        Useful for detecting memory leaks where objects aren't being
        cleaned up as expected.
        
        Args:
            label: Optional label to filter by
            min_age_seconds: Minimum age to consider orphaned
            
        Returns:
            List of potentially orphaned objects
        """
        orphaned = []
        now = datetime.now()
        
        check_ids = (
            self._by_label.get(label, set()) if label
            else set(self._tracked.keys())
        )
        
        for tracking_id in check_ids:
            tracked = self._tracked.get(tracking_id)
            if not tracked:
                continue
            
            age = (now - tracked.creation_time).total_seconds()
            
            # Object is "orphaned" if it's old, still alive, and marked as temporary
            if tracked.is_alive and age > min_age_seconds:
                if tracked.metadata.get("temporary", False):
                    orphaned.append(tracked)
        
        return orphaned
    
    def cleanup_dead(self) -> int:
        """Remove dead objects from tracking.
        
        Returns:
            Number of objects removed
        """
        dead_ids = [
            tid for tid, tracked in self._tracked.items()
            if not tracked.is_alive
        ]
        
        for tid in dead_ids:
            self.untrack(tid)
        
        return len(dead_ids)
    
    def get_lifecycle_report(self, label: Optional[str] = None) -> Dict[str, Any]:
        """Generate lifecycle analysis report.
        
        Args:
            label: Optional label to filter by
            
        Returns:
            Dictionary with lifecycle statistics
        """
        if label:
            tracking_ids = self._by_label.get(label, set())
            tracked_objects = [
                self._tracked[tid] for tid in tracking_ids
                if tid in self._tracked
            ]
        else:
            tracked_objects = list(self._tracked.values())
        
        if not tracked_objects:
            return {
                "total_tracked": 0,
                "alive": 0,
                "dead": 0,
                "alive_percent": 0,
            }
        
        total = len(tracked_objects)
        alive = sum(1 for t in tracked_objects if t.is_alive)
        dead = total - alive
        
        # Calculate average age of alive objects
        now = datetime.now()
        alive_ages = [
            (now - t.creation_time).total_seconds()
            for t in tracked_objects if t.is_alive
        ]
        avg_age = sum(alive_ages) / len(alive_ages) if alive_ages else 0
        max_age = max(alive_ages) if alive_ages else 0
        
        # Calculate total estimated size of alive objects
        total_size_mb = sum(
            t.current_size_estimate()
            for t in tracked_objects if t.is_alive
        )
        
        return {
            "total_tracked": total,
            "alive": alive,
            "dead": dead,
            "alive_percent": (alive / total * 100) if total > 0 else 0,
            "avg_age_seconds": avg_age,
            "max_age_seconds": max_age,
            "total_size_mb": total_size_mb,
            "label_filter": label,
        }
    
    def get_all_by_label(self, label: str) -> List[TrackedObject]:
        """Get all tracked objects with a specific label.
        
        Args:
            label: Label to filter by
            
        Returns:
            List of TrackedObject instances
        """
        tracking_ids = self._by_label.get(label, set())
        return [
            self._tracked[tid] for tid in tracking_ids
            if tid in self._tracked
        ]
    
    def clear(self) -> None:
        """Clear all tracked objects."""
        self._tracked.clear()
        self._by_label.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tracker state to dictionary.
        
        Returns:
            Dictionary with all tracking information
        """
        return {
            "total_tracked": len(self._tracked),
            "alive_count": self.get_alive_count(),
            "dead_count": self.get_dead_count(),
            "labels": list(self._by_label.keys()),
            "objects": [
                tracked.to_dict()
                for tracked in self._tracked.values()
            ],
        }
