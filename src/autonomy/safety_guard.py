"""
SafetyGuard - Critical protections for Demi's self-modification system.

Provides rate limiting, critical file protection, change throttling,
and emergency stop capabilities. This is the safety layer that prevents
runaway self-modification or catastrophic changes.
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.core.logger import get_logger

logger = get_logger()


class SafetyLevel(Enum):
    """Safety restriction levels."""
    PERMISSIVE = "permissive"    # Minimal restrictions
    NORMAL = "normal"            # Standard protections
    RESTRICTIVE = "restrictive"  # Extra caution
    LOCKDOWN = "lockdown"        # No modifications allowed


class SafetyViolation(Enum):
    """Types of safety violations."""
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CRITICAL_FILE_BLOCKED = "critical_file_blocked"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    CHANGE_SIZE_EXCEEDED = "change_size_exceeded"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    EMERGENCY_STOP = "emergency_stop"
    CIRCULAR_MODIFICATION = "circular_modification"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    max_modifications: int
    window_seconds: int
    current_count: int = 0
    window_start: Optional[datetime] = None


@dataclass
class SafetyEvent:
    """Record of a safety-related event."""
    event_id: str
    timestamp: datetime
    violation_type: SafetyViolation
    details: Dict
    action_taken: str
    resolved: bool = False


@dataclass
class ModificationQuota:
    """Daily/hourly modification quotas."""
    hourly_limit: int = 10
    daily_limit: int = 50
    hourly_used: int = 0
    daily_used: int = 0
    last_hour_reset: Optional[datetime] = None
    last_day_reset: Optional[datetime] = None


class SafetyGuard:
    """
    Safety guardian for Demi's self-modification system.
    
    Responsibilities:
    1. Rate limiting (prevent runaway modifications)
    2. Critical file protection (auth, security, core)
    3. Pattern detection (malicious/suspicious code)
    4. Change throttling (cooldown between changes)
    5. Emergency stop (circuit breaker)
    6. Circular modification detection
    
    Usage:
        guard = SafetyGuard()
        
        # Check if modification is allowed
        allowed, reason = guard.check_modification_allowed(
            "src/emotion/decay.py",
            new_content
        )
        
        if not allowed:
            logger.warning(f"Modification blocked: {reason}")
            return
    """
    
    # Dangerous patterns that should block modification
    DANGEROUS_PATTERNS = {
        "exec": r'\bexec\s*\(',
        "eval": r'\beval\s*\(',
        "compile": r'\bcompile\s*\(',
        "os_system": r'os\.system\s*\(',
        "subprocess_shell": r'subprocess\.\w+.*shell\s*=\s*True',
        "pickle_loads": r'pickle\.loads?\s*\(',
        "yaml_unsafe": r'yaml\.load\s*\([^)]*\)(?!.*Loader=yaml\.SafeLoader)',
        "hardcoded_secret": r'(password|secret|key)\s*=\s*["\'][^"\']+["\']',
        "infinite_loop": r'while\s+True\s*:',
        "recursive_import": r'from\s+\.+\s+import',
    }
    
    # Files that are always protected
    CRITICAL_FILES = {
        "src/api/auth.py",
        "src/core/database.py",
        "src/core/config.py",
        "src/autonomy/safety_guard.py",
        "src/autonomy/code_modifier.py",
        ".env",
        ".env.example",
        "requirements.txt",
        "docker-compose.yml",
        "Dockerfile",
        "main.py",
    }
    
    # Modules that shouldn't be modified frequently
    SENSITIVE_MODULES = {
        "src/api/",
        "src/core/",
        "src/conductor/isolation.py",
        "src/llm/inference.py",
    }
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the safety guard.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root or self._detect_project_root())
        
        # Current safety level
        self._safety_level = SafetyLevel.NORMAL
        
        # Rate limiting
        self._rate_limits: Dict[str, RateLimit] = {
            "modifications": RateLimit(max_modifications=10, window_seconds=3600),  # 10/hour
            "critical_attempts": RateLimit(max_modifications=3, window_seconds=3600),  # 3/hour
            "emergency": RateLimit(max_modifications=1, window_seconds=86400),  # 1/day
        }
        
        # Modification quota tracking
        self._quota = ModificationQuota()
        
        # Consecutive failure tracking
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        
        # Recent modification history (for circular detection)
        self._recent_modifications: List[Dict] = []
        self._max_history = 50
        
        # Safety events log
        self._events: List[SafetyEvent] = []
        self._max_events = 100
        
        # Emergency stop flag
        self._emergency_stop = False
        
        # Cooldown tracking
        self._last_modification_time: Optional[datetime] = None
        self._cooldown_seconds = 30  # Minimum seconds between modifications
        
        # Health checkers (for integration with EmergencyHealing)
        self._health_checkers: List[Callable] = []
        
        logger.info(f"SafetyGuard initialized: level={self._safety_level.value}")
    
    def _detect_project_root(self) -> str:
        """Auto-detect project root."""
        current_file = Path(__file__).resolve()
        return str(current_file.parent.parent.parent)
    
    def check_modification_allowed(
        self,
        file_path: str,
        new_content: str,
        context: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive safety check before allowing modification.
        
        Returns:
            (allowed, reason_if_blocked)
        """
        # Check emergency stop
        if self._emergency_stop:
            return False, "Emergency stop is active"
        
        # Check safety level
        if self._safety_level == SafetyLevel.LOCKDOWN:
            return False, "Safety level is LOCKDOWN - no modifications allowed"
        
        abs_path = os.path.abspath(file_path)
        rel_path = os.path.relpath(abs_path, self.project_root)
        
        # 1. Critical file check
        if self._is_critical_file(abs_path):
            self._record_violation(SafetyViolation.CRITICAL_FILE_BLOCKED, {
                "file": rel_path
            })
            return False, f"Critical file blocked: {rel_path}"
        
        # 2. Rate limit check
        if not self._check_rate_limit("modifications"):
            self._record_violation(SafetyViolation.RATE_LIMIT_EXCEEDED, {
                "file": rel_path,
                "limit": "modifications"
            })
            return False, "Rate limit exceeded - too many modifications"
        
        # 3. Quota check
        if not self._check_quota():
            return False, "Daily/hourly modification quota exceeded"
        
        # 4. Cooldown check
        if not self._check_cooldown():
            remaining = self._get_cooldown_remaining()
            return False, f"Cooldown in effect - wait {remaining:.0f} seconds"
        
        # 5. Consecutive failure check
        if self._consecutive_failures >= self._max_consecutive_failures:
            self._record_violation(SafetyViolation.CONSECUTIVE_FAILURES, {
                "failures": self._consecutive_failures
            })
            return False, f"Too many consecutive failures ({self._consecutive_failures})"
        
        # 6. Dangerous pattern check
        violations = self._check_dangerous_patterns(new_content)
        if violations:
            self._record_violation(SafetyViolation.SUSPICIOUS_PATTERN, {
                "file": rel_path,
                "patterns": violations
            })
            return False, f"Dangerous patterns detected: {', '.join(violations)}"
        
        # 7. Circular modification check
        if self._is_circular_modification(abs_path, new_content):
            self._record_violation(SafetyViolation.CIRCULAR_MODIFICATION, {
                "file": rel_path
            })
            return False, "Circular modification detected - already modified recently"
        
        # 8. Change size check
        if len(new_content) > 100000:  # 100KB limit
            self._record_violation(SafetyViolation.CHANGE_SIZE_EXCEEDED, {
                "file": rel_path,
                "size": len(new_content)
            })
            return False, f"Change size ({len(new_content)} bytes) exceeds limit"
        
        # All checks passed
        return True, None
    
    def _is_critical_file(self, file_path: str) -> bool:
        """Check if file is critical/protected."""
        rel_path = os.path.relpath(file_path, self.project_root)
        
        # Direct match
        if rel_path in self.CRITICAL_FILES:
            return True
        
        # Check sensitive modules in restrictive mode
        if self._safety_level == SafetyLevel.RESTRICTIVE:
            for sensitive in self.SENSITIVE_MODULES:
                if rel_path.startswith(sensitive):
                    return True
        
        return False
    
    def _check_rate_limit(self, limit_name: str) -> bool:
        """Check if rate limit allows the operation."""
        limit = self._rate_limits.get(limit_name)
        if not limit:
            return True
        
        now = datetime.now(timezone.utc)
        
        # Reset window if expired
        if limit.window_start is None or \
           (now - limit.window_start).total_seconds() > limit.window_seconds:
            limit.window_start = now
            limit.current_count = 0
        
        # Check if under limit
        if limit.current_count >= limit.max_modifications:
            return False
        
        limit.current_count += 1
        return True
    
    def _check_quota(self) -> bool:
        """Check modification quotas."""
        now = datetime.now(timezone.utc)
        
        # Reset hourly quota if needed
        if self._quota.last_hour_reset is None or \
           (now - self._quota.last_hour_reset).total_seconds() > 3600:
            self._quota.last_hour_reset = now
            self._quota.hourly_used = 0
        
        # Reset daily quota if needed
        if self._quota.last_day_reset is None or \
           (now - self._quota.last_day_reset).total_seconds() > 86400:
            self._quota.last_day_reset = now
            self._quota.daily_used = 0
        
        # Check quotas
        if self._quota.hourly_used >= self._quota.hourly_limit:
            return False
        if self._quota.daily_used >= self._quota.daily_limit:
            return False
        
        self._quota.hourly_used += 1
        self._quota.daily_used += 1
        return True
    
    def _check_cooldown(self) -> bool:
        """Check if cooldown period has passed."""
        if self._last_modification_time is None:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self._last_modification_time).total_seconds()
        return elapsed >= self._cooldown_seconds
    
    def _get_cooldown_remaining(self) -> float:
        """Get remaining cooldown time in seconds."""
        if self._last_modification_time is None:
            return 0
        
        elapsed = (datetime.now(timezone.utc) - self._last_modification_time).total_seconds()
        return max(0, self._cooldown_seconds - elapsed)
    
    def register_health_checker(self, checker: Callable):
        """Register a custom health check callback.
        
        Args:
            checker: Function that returns HealthCheck or None
        """
        self._health_checkers.append(checker)
        logger.debug("Registered health checker")
    
    def run_health_checks(self) -> List:
        """Run all registered health checks."""
        results = []
        for checker in self._health_checkers:
            try:
                result = checker()
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Health checker failed: {e}")
        return results
    
    def _check_dangerous_patterns(self, content: str) -> List[str]:
        """Check for dangerous code patterns."""
        violations = []
        
        for pattern_name, pattern_regex in self.DANGEROUS_PATTERNS.items():
            if re.search(pattern_regex, content, re.IGNORECASE):
                violations.append(pattern_name)
        
        return violations
    
    def _is_circular_modification(self, file_path: str, content: str) -> bool:
        """Detect if we're modifying the same file repeatedly."""
        # Check last N modifications
        recent = self._recent_modifications[-5:]
        
        same_file_count = sum(
            1 for m in recent
            if m.get("file_path") == file_path
        )
        
        # If modified same file 3+ times recently, consider it circular
        if same_file_count >= 3:
            return True
        
        # Check for content similarity (reverting changes)
        for m in recent:
            if m.get("file_path") == file_path:
                # Simple hash comparison
                old_hash = hash(m.get("content", ""))
                new_hash = hash(content)
                if old_hash == new_hash:
                    return True
        
        return False
    
    def record_modification(self, file_path: str, content: str, success: bool):
        """Record a modification attempt for tracking."""
        self._recent_modifications.append({
            "file_path": file_path,
            "content": content[:1000],  # Store partial content for comparison
            "timestamp": datetime.now(timezone.utc),
            "success": success
        })
        
        # Trim history
        if len(self._recent_modifications) > self._max_history:
            self._recent_modifications = self._recent_modifications[-self._max_history:]
        
        # Update tracking
        self._last_modification_time = datetime.now(timezone.utc)
        
        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
    
    def _record_violation(self, violation_type: SafetyViolation, details: Dict):
        """Record a safety violation."""
        event = SafetyEvent(
            event_id=f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{len(self._events)}",
            timestamp=datetime.now(timezone.utc),
            violation_type=violation_type,
            details=details,
            action_taken="blocked"
        )
        
        self._events.append(event)
        
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        
        logger.warning(f"Safety violation: {violation_type.value} - {details}")
    
    # Public control methods
    
    def set_safety_level(self, level: SafetyLevel):
        """Set the current safety level."""
        old_level = self._safety_level
        self._safety_level = level
        logger.info(f"Safety level changed: {old_level.value} -> {level.value}")
    
    def get_safety_level(self) -> SafetyLevel:
        """Get current safety level."""
        return self._safety_level
    
    def emergency_stop(self, reason: str):
        """Activate emergency stop."""
        self._emergency_stop = True
        self._record_violation(SafetyViolation.EMERGENCY_STOP, {"reason": reason})
        logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
    
    def emergency_resume(self):
        """Deactivate emergency stop."""
        self._emergency_stop = False
        logger.info("Emergency stop deactivated")
    
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stop
    
    def reset_failure_count(self):
        """Reset consecutive failure counter."""
        self._consecutive_failures = 0
        logger.info("Failure count reset")
    
    def get_stats(self) -> Dict:
        """Get safety guard statistics."""
        recent_violations = len([
            e for e in self._events
            if (datetime.now(timezone.utc) - e.timestamp).total_seconds() < 86400
        ])
        
        return {
            "safety_level": self._safety_level.value,
            "emergency_stop": self._emergency_stop,
            "consecutive_failures": self._consecutive_failures,
            "hourly_quota_used": self._quota.hourly_used,
            "daily_quota_used": self._quota.daily_used,
            "recent_violations_24h": recent_violations,
            "total_violations": len(self._events),
            "recent_modifications": len(self._recent_modifications),
            "cooldown_active": not self._check_cooldown(),
            "cooldown_remaining": self._get_cooldown_remaining(),
        }
    
    def get_recent_violations(self, limit: int = 10) -> List[SafetyEvent]:
        """Get recent safety violations."""
        return list(reversed(self._events[-limit:]))
