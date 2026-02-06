"""
EmergencyHealing - Self-repair system for Demi.

Provides emergency self-healing capabilities when the system detects
it's in a broken state. Can restore from backups, reset to known-good
state, and perform critical fixes autonomously.
"""

import os
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from src.core.logger import get_logger

logger = get_logger()


class HealingAction(Enum):
    """Types of healing actions."""
    ROLLBACK_FILE = "rollback_file"
    RESET_TO_MAIN = "reset_to_main"
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    REINSTALL_DEPS = "reinstall_deps"
    FACTORY_RESET = "factory_reset"
    EMERGENCY_PATCH = "emergency_patch"


class HealingResult(Enum):
    """Result of healing attempt."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_NEEDED = "not_needed"
    SKIPPED = "skipped"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    healthy: bool
    severity: str  # critical, warning, info
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class HealingEvent:
    """Record of a healing event."""
    event_id: str
    timestamp: datetime
    trigger: str
    actions_taken: List[Tuple[HealingAction, HealingResult]]
    final_state: str
    details: str


class EmergencyHealing:
    """
    Emergency self-healing system for Demi.
    
    Capabilities:
    1. Health monitoring (detect broken state)
    2. Automatic rollback (restore last known good)
    3. Git reset (return to main branch)
    4. Cache clearing (fix stale state)
    5. Emergency patches (critical fixes)
    
    Usage:
        healer = EmergencyHealing(code_modifier, git_manager)
        
        # Check health
        health = healer.check_system_health()
        
        if not health.healthy:
            # Attempt healing
            result = await healer.heal_system(health)
    """
    
    def __init__(
        self,
        code_modifier=None,
        git_manager=None,
        project_root: Optional[str] = None
    ):
        """
        Initialize emergency healing.
        
        Args:
            code_modifier: SafeCodeModifier instance for rollbacks
            git_manager: GitManager instance for git operations
            project_root: Project root directory
        """
        self.project_root = Path(project_root or self._detect_project_root())
        self.code_modifier = code_modifier
        self.git_manager = git_manager
        
        # Healing configuration
        self.config = {
            "auto_heal": True,
            "max_healing_attempts": 3,
            "healing_cooldown_minutes": 30,
            "rollback_on_critical": True,
            "reset_on_unrecoverable": False,  # Dangerous - disabled by default
        }
        
        # State tracking
        self._healing_events: List[HealingEvent] = []
        self._last_healing_time: Optional[datetime] = None
        self._healing_attempts_today = 0
        self._last_healing_day: Optional[datetime] = None
        
        # Custom health checks
        self._health_checkers: List[Callable] = []
        
        logger.info("EmergencyHealing initialized")
    
    def _detect_project_root(self) -> str:
        """Auto-detect project root."""
        current_file = Path(__file__).resolve()
        return str(current_file.parent.parent.parent)
    
    def register_health_checker(self, checker: Callable):
        """Register a custom health check function."""
        self._health_checkers.append(checker)
    
    async def check_system_health(self) -> List[HealthCheck]:
        """
        Run comprehensive health checks on the system.
        
        Returns:
            List of health check results
        """
        checks = []
        
        # Check 1: Can we import core modules?
        checks.append(self._check_core_imports())
        
        # Check 2: Git repository status
        checks.append(self._check_git_status())
        
        # Check 3: File integrity (no corrupted files)
        checks.append(await self._check_file_integrity())
        
        # Check 4: Recent modification failures
        checks.append(self._check_recent_failures())
        
        # Check 5: Run custom health checkers
        for checker in self._health_checkers:
            try:
                result = checker()
                if result:
                    checks.append(result)
            except Exception as e:
                logger.error(f"Custom health check failed: {e}")
        
        return checks
    
    def _check_core_imports(self) -> HealthCheck:
        """Check that core modules can be imported."""
        core_modules = [
            "src.core.config",
            "src.core.database",
            "src.emotion.models",
            "src.llm.inference",
        ]
        
        failed = []
        for module in core_modules:
            try:
                # Try to import
                parts = module.split('.')
                current = __import__(parts[0])
                for part in parts[1:]:
                    current = getattr(current, part)
            except Exception as e:
                failed.append(f"{module}: {e}")
        
        if failed:
            return HealthCheck(
                name="core_imports",
                healthy=False,
                severity="critical",
                message=f"Failed to import {len(failed)} core modules",
                details={"failed": failed}
            )
        
        return HealthCheck(
            name="core_imports",
            healthy=True,
            severity="info",
            message="All core modules import successfully"
        )
    
    def _check_git_status(self) -> HealthCheck:
        """Check Git repository health."""
        if not self.git_manager or not self.git_manager.is_available():
            return HealthCheck(
                name="git_status",
                healthy=True,  # Not critical if no git
                severity="warning",
                message="Git not available"
            )
        
        status = self.git_manager.get_status()
        
        if not status.get("is_clean", False):
            return HealthCheck(
                name="git_status",
                healthy=False,
                severity="warning",
                message=f"Uncommitted changes: {status.get('uncommitted_changes', 0)} files",
                details={"branch": status.get("branch")}
            )
        
        return HealthCheck(
            name="git_status",
            healthy=True,
            severity="info",
            message=f"Git clean on branch {status.get('branch')}"
        )
    
    async def _check_file_integrity(self) -> HealthCheck:
        """Check that key files are not corrupted."""
        key_files = [
            "main.py",
            "src/core/config.py",
            "src/core/database.py",
        ]
        
        corrupted = []
        for file_path in key_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Try to parse if Python
                        if file_path.endswith('.py'):
                            import ast
                            ast.parse(content)
                except SyntaxError as e:
                    corrupted.append(f"{file_path}: Syntax error at line {e.lineno}")
                except Exception as e:
                    corrupted.append(f"{file_path}: {e}")
        
        if corrupted:
            return HealthCheck(
                name="file_integrity",
                healthy=False,
                severity="critical",
                message=f"{len(corrupted)} files corrupted",
                details={"corrupted": corrupted}
            )
        
        return HealthCheck(
            name="file_integrity",
            healthy=True,
            severity="info",
            message="All key files intact"
        )
    
    def _check_recent_failures(self) -> HealthCheck:
        """Check for recent modification failures."""
        # This would integrate with code_modifier history
        if not self.code_modifier:
            return HealthCheck(
                name="recent_failures",
                healthy=True,
                severity="info",
                message="No failure tracking available"
            )
        
        recent_failures = self.code_modifier.get_history(
            result_filter=self.code_modifier.ModificationResult.WRITE_FAILED,
            limit=5
        )
        
        if len(recent_failures) >= 3:
            return HealthCheck(
                name="recent_failures",
                healthy=False,
                severity="warning",
                message=f"{len(recent_failures)} recent modification failures",
                details={"failures": [f.attempt_id for f in recent_failures]}
            )
        
        return HealthCheck(
            name="recent_failures",
            healthy=True,
            severity="info",
            message="No recent failures detected"
        )
    
    def is_system_healthy(self, checks: Optional[List[HealthCheck]] = None) -> bool:
        """Check if system is overall healthy."""
        if checks is None:
            # Can't run async check here, assume caller provides
            return True
        
        critical_issues = [
            c for c in checks
            if not c.healthy and c.severity == "critical"
        ]
        
        return len(critical_issues) == 0
    
    async def heal_system(
        self,
        health_checks: Optional[List[HealthCheck]] = None,
        force: bool = False
    ) -> HealingEvent:
        """
        Attempt to heal the system from a broken state.
        
        Args:
            health_checks: Pre-computed health checks (optional)
            force: Force healing even if auto_heal is disabled
            
        Returns:
            HealingEvent with results
        """
        event_id = f"heal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        # Check cooldown
        if not force and not self._can_heal():
            return HealingEvent(
                event_id=event_id,
                timestamp=datetime.now(timezone.utc),
                trigger="cooldown",
                actions_taken=[],
                final_state="skipped",
                details="Healing on cooldown"
            )
        
        # Get health checks if not provided
        if health_checks is None:
            health_checks = await self.check_system_health()
        
        # Check if healing needed
        if self.is_system_healthy(health_checks) and not force:
            return HealingEvent(
                event_id=event_id,
                timestamp=datetime.now(timezone.utc),
                trigger="health_check",
                actions_taken=[],
                final_state="healthy",
                details="System is healthy, no healing needed"
            )
        
        logger.warning(f"Starting emergency healing: {event_id}")
        
        actions_taken = []
        
        # Identify critical issues
        critical = [c for c in health_checks if c.severity == "critical" and not c.healthy]
        
        # Action 1: Handle file corruption
        corruption = next((c for c in critical if c.name == "file_integrity"), None)
        if corruption:
            result = await self._heal_file_corruption(corruption)
            actions_taken.append((HealingAction.ROLLBACK_FILE, result))
        
        # Action 2: Handle Git issues
        git_issues = next((c for c in health_checks if c.name == "git_status"), None)
        if git_issues and not git_issues.healthy:
            result = await self._heal_git_issues()
            actions_taken.append((HealingAction.RESET_TO_MAIN, result))
        
        # Action 3: Handle import failures
        import_issues = next((c for c in critical if c.name == "core_imports"), None)
        if import_issues:
            # Try clearing cache
            result = await self._heal_clear_cache()
            actions_taken.append((HealingAction.CLEAR_CACHE, result))
        
        # Re-check health
        new_checks = await self.check_system_health()
        final_healthy = self.is_system_healthy(new_checks)
        
        final_state = "healed" if final_healthy else "still_broken"
        
        # Update tracking
        self._last_healing_time = datetime.now(timezone.utc)
        self._update_healing_count()
        
        event = HealingEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc),
            trigger="health_check" if not force else "forced",
            actions_taken=actions_taken,
            final_state=final_state,
            details=f"Actions: {len(actions_taken)}, Final health: {final_healthy}"
        )
        
        self._healing_events.append(event)
        logger.info(f"Healing complete: {final_state}")
        
        return event
    
    def _can_heal(self) -> bool:
        """Check if healing is allowed (cooldown, limits)."""
        if not self.config["auto_heal"]:
            return False
        
        # Check daily limit
        self._update_healing_count()
        if self._healing_attempts_today >= self.config["max_healing_attempts"]:
            return False
        
        # Check cooldown
        if self._last_healing_time:
            elapsed = (datetime.now(timezone.utc) - self._last_healing_time).total_seconds()
            cooldown = self.config["healing_cooldown_minutes"] * 60
            if elapsed < cooldown:
                return False
        
        return True
    
    def _update_healing_count(self):
        """Update daily healing count."""
        today = datetime.now(timezone.utc).date()
        
        if self._last_healing_day != today:
            self._healing_attempts_today = 0
            self._last_healing_day = today
    
    async def _heal_file_corruption(self, check: HealthCheck) -> HealingResult:
        """Heal corrupted files using backups or Git."""
        corrupted = check.details.get("corrupted", [])
        
        healed = 0
        failed = 0
        
        for item in corrupted:
            file_path = item.split(":")[0]
            
            # Try rollback first
            if self.code_modifier:
                success = self.code_modifier.rollback_file(file_path)
                if success:
                    healed += 1
                    continue
            
            # Try Git restore
            if self.git_manager and self.git_manager.is_available():
                success = self.git_manager.discard_changes(file_path)
                if success:
                    healed += 1
                    continue
            
            failed += 1
        
        if failed == 0:
            return HealingResult.SUCCESS
        elif healed > 0:
            return HealingResult.PARTIAL
        else:
            return HealingResult.FAILED
    
    async def _heal_git_issues(self) -> HealingResult:
        """Heal Git-related issues."""
        if not self.git_manager:
            return HealingResult.SKIPPED
        
        # Stash any changes
        stashed = self.git_manager.stash_changes("Emergency healing stash")
        
        # Try to checkout main
        main_branch = "main"
        if not self.git_manager.checkout_branch(main_branch):
            main_branch = "master"
            if not self.git_manager.checkout_branch(main_branch):
                return HealingResult.FAILED
        
        # Pull latest
        success, _, _ = self.git_manager._run_git(["pull", "origin", main_branch])
        
        if stashed:
            # Keep stashed, don't auto-pop (might cause issues)
            pass
        
        return HealingResult.SUCCESS if success else HealingResult.PARTIAL
    
    async def _heal_clear_cache(self) -> HealingResult:
        """Clear Python cache files."""
        try:
            # Find and remove __pycache__ directories
            removed = 0
            for pycache in self.project_root.rglob("__pycache__"):
                if pycache.is_dir():
                    import shutil
                    shutil.rmtree(pycache)
                    removed += 1
            
            # Remove .pyc files
            for pyc in self.project_root.rglob("*.pyc"):
                pyc.unlink()
            
            logger.info(f"Cleared {removed} cache directories")
            return HealingResult.SUCCESS
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
            return HealingResult.FAILED
    
    def get_healing_history(self, limit: int = 10) -> List[HealingEvent]:
        """Get recent healing events."""
        return list(reversed(self._healing_events[-limit:]))
    
    def get_stats(self) -> Dict:
        """Get healing system statistics."""
        today_events = [
            e for e in self._healing_events
            if e.timestamp.date() == datetime.now(timezone.utc).date()
        ]
        
        successful = len([e for e in today_events if e.final_state == "healed"])
        
        return {
            "total_healings": len(self._healing_events),
            "today_healings": len(today_events),
            "today_successful": successful,
            "healing_attempts_remaining": self.config["max_healing_attempts"] - self._healing_attempts_today,
            "auto_heal_enabled": self.config["auto_heal"],
            "last_healing": self._last_healing_time.isoformat() if self._last_healing_time else None,
        }
