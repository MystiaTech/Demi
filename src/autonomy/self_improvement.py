"""
SelfImprovementSystem - Complete self-modification system for Demi.

Integrates all self-modification capabilities:
- SafeCodeModifier: Safe file modifications with backups
- GitManager: Version control for changes
- ModificationValidator: Testing and validation
- SafetyGuard: Rate limiting and protections
- EmergencyHealing: Self-repair when broken
- AutonomyConfig: Configuration management

This is the unified interface for Demi's full autonomy.
"""

import asyncio
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from src.core.logger import get_logger

# Import self-modification components
from src.autonomy.code_modifier import (
    SafeCodeModifier,
    ModificationResult,
    ModificationContext,
    ModificationAttempt
)
from src.autonomy.git_manager import GitManager, ModificationBranch
from src.autonomy.modification_validator import (
    ModificationValidator,
    ValidationReport,
    ValidationResult
)
from src.autonomy.safety_guard import SafetyGuard, SafetyLevel, SafetyViolation
from src.autonomy.emergency_healing import EmergencyHealing, HealingEvent
from src.autonomy.autonomy_config import get_autonomy_config, SelfModificationConfig
from src.llm.codebase_reader import CodebaseReader

logger = get_logger()


class ImprovementStatus(Enum):
    """Status of an improvement suggestion."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    VALIDATING = "validating"
    APPLYING = "applying"
    COMMITTED = "committed"
    MERGED = "merged"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ImprovementSuggestion:
    """An improvement suggestion with full tracking."""
    suggestion_id: str
    file_path: str
    description: str
    suggested_content: str
    priority: str  # low, medium, high, critical
    confidence: float
    created_at: datetime
    status: ImprovementStatus = ImprovementStatus.PENDING
    current_code: str = ""
    
    # Tracking
    validation_report: Optional[ValidationReport] = None
    modification_attempt: Optional[ModificationAttempt] = None
    git_branch: Optional[str] = None
    
    # Results
    applied_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "suggestion_id": self.suggestion_id,
            "file_path": self.file_path,
            "description": self.description,
            "priority": self.priority,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "error_message": self.error_message,
        }


class SelfImprovementSystem:
    """
    Complete self-improvement system with full autonomy capabilities.
    
    Features:
    - Code review and suggestion generation
    - Safe file modification with backups
    - Git version control integration
    - Comprehensive testing and validation
    - Safety guards and rate limiting
    - Emergency self-healing
    
    Usage:
        # Initialize
        improvement = SelfImprovementSystem(conductor)
        
        # Review code and generate suggestions
        suggestions = await improvement.run_code_review()
        
        # Apply a suggestion (with full safety pipeline)
        result = await improvement.apply_suggestion(suggestions[0])
        
        # Check system health
        health = await improvement.check_health()
        
        # Emergency healing if needed
        if not health.healthy:
            await improvement.emergency_heal()
    """
    
    def __init__(self, conductor=None, project_root: Optional[str] = None):
        """
        Initialize the complete self-improvement system.
        
        Args:
            conductor: Conductor instance for LLM access
            project_root: Project root directory
        """
        self.conductor = conductor
        self.project_root = self._determine_project_root(project_root)
        self.config: SelfModificationConfig = get_autonomy_config()
        
        # Initialize all subsystems
        self.code_modifier = SafeCodeModifier(project_root=str(self.project_root))
        self.git_manager = GitManager(project_root=str(self.project_root))
        self.validator = ModificationValidator(project_root=str(self.project_root))
        self.safety_guard = SafetyGuard(project_root=str(self.project_root))
        self.emergency_healing = EmergencyHealing(
            code_modifier=self.code_modifier,
            git_manager=self.git_manager,
            project_root=str(self.project_root)
        )
        
        # Codebase reader for analysis
        self.codebase_reader: Optional[CodebaseReader] = None
        if conductor and hasattr(conductor, 'codebase_reader'):
            self.codebase_reader = conductor.codebase_reader
        else:
            try:
                self.codebase_reader = CodebaseReader(logger=logger)
            except Exception as e:
                logger.warning(f"Could not initialize codebase reader: {e}")
        
        # Suggestion tracking
        self.suggestions: Dict[str, ImprovementSuggestion] = {}
        self._pending_approvals: List[str] = []
        
        # Callbacks for notifications
        self._on_suggestion_created: Optional[Callable] = None
        self._on_suggestion_applied: Optional[Callable] = None
        self._on_suggestion_failed: Optional[Callable] = None
        
        # Code review tracking
        self.last_review_time: Optional[datetime] = None
        
        # Register emergency healing with safety guard
        self.safety_guard.register_health_checker(self._health_check_callback)
        
        logger.info(
            f"SelfImprovementSystem initialized: "
            f"enabled={self.config.enabled}, "
            f"safety_level={self.config.safety_level}"
        )
    
    def _detect_project_root(self) -> str:
        """Auto-detect project root."""
        current_file = Path(__file__).resolve()
        return str(current_file.parent.parent.parent)

    def _determine_project_root(self, project_root: Optional[str]) -> Path:
        """
        Determine usable project root with fallback strategy.
        Priority:
        1) Explicit constructor argument
        2) DEMI_PROJECT_ROOT env var
        3) Source-tree detection from module location
        4) Current working directory (if writable)
        """
        candidates: List[Path] = []

        if project_root:
            candidates.append(Path(project_root))

        env_root = os.getenv("DEMI_PROJECT_ROOT")
        if env_root:
            candidates.append(Path(env_root))

        candidates.append(Path(self._detect_project_root()))
        candidates.append(Path.cwd())

        for candidate in candidates:
            try:
                resolved = candidate.expanduser().resolve()
            except Exception:
                continue

            # Prefer roots that look like source workspaces.
            has_source_layout = (resolved / "src").exists()
            has_project_markers = any(
                (resolved / marker).exists()
                for marker in (".git", "pyproject.toml", "setup.py")
            )
            if not (has_source_layout or has_project_markers):
                continue

            if os.access(resolved, os.W_OK):
                logger.info(f"Using self-improvement project root: {resolved}")
                return resolved

        fallback = Path.cwd().resolve()
        logger.warning(
            f"No writable project root candidate found; falling back to cwd: {fallback}. "
            "Set DEMI_PROJECT_ROOT explicitly for reliable self-improvement."
        )
        return fallback

    @property
    def enabled(self) -> bool:
        """Backwards-compatible access to config.enabled."""
        return self.config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.config.enabled = bool(value)
    
    # ==================== Core Improvement Workflow ====================
    
    async def run_code_review(self) -> List[ImprovementSuggestion]:
        """
        Review codebase and generate improvement suggestions.
        
        Returns:
            List of ImprovementSuggestion objects
        """
        if not self.config.enabled:
            logger.info("Self-modification is disabled")
            return []
        
        if not self.conductor or not self.codebase_reader:
            logger.warning("Cannot run code review: missing dependencies")
            return []
        
        try:
            logger.info("Starting autonomous code review...")
            
            # Get recent conversation patterns
            recent_interactions = self._get_recent_interactions()
            
            # Get codebase sample
            sample_code = self._get_codebase_sample()
            
            # Build prompt for code review
            review_prompt = self._build_review_prompt(recent_interactions, sample_code)
            
            # Run review through LLM
            messages = [{"role": "user", "content": review_prompt}]
            response = await self.conductor.request_inference(messages)
            
            # Parse suggestions
            suggestions = self._parse_review_response(response)
            
            # Store suggestions
            for suggestion in suggestions:
                self.suggestions[suggestion.suggestion_id] = suggestion
                if self.config.require_human_approval:
                    self._pending_approvals.append(suggestion.suggestion_id)
                
                if self._on_suggestion_created:
                    await self._notify(self._on_suggestion_created, suggestion)
            
            logger.info(f"Code review complete: {len(suggestions)} suggestions")
            self.last_review_time = datetime.now(timezone.utc)
            
            # Auto-apply suggestions if enabled and no approval required
            if not self.config.require_human_approval:
                for suggestion in suggestions:
                    should_auto_apply = (
                        self.config.auto_apply_low_risk and 
                        suggestion.priority in ['low', 'medium']
                    ) or suggestion.priority == 'high' or suggestion.confidence > 0.9
                    
                    if should_auto_apply:
                        logger.info(f"Auto-applying suggestion {suggestion.suggestion_id} "
                                  f"(priority={suggestion.priority}, confidence={suggestion.confidence})")
                        await self.apply_suggestion(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return []
    
    async def apply_suggestion(
        self,
        suggestion: ImprovementSuggestion,
        force: bool = False
    ) -> bool:
        """
        Apply an improvement suggestion with full safety pipeline.
        
        Pipeline:
        1. Safety check (rate limits, critical files)
        2. Validation (syntax, tests)
        3. Git branch creation
        4. File modification
        5. Git commit
        6. (Optional) Merge to main
        
        Args:
            suggestion: The suggestion to apply
            force: Bypass some safety checks (dangerous)
            
        Returns:
            True if successfully applied
        """
        if not self.config.enabled:
            logger.warning("Cannot apply: self-modification disabled")
            return False
        
        suggestion_id = suggestion.suggestion_id
        resolved_path, path_error = self._resolve_file_path(suggestion.file_path)
        if path_error:
            logger.error(f"Invalid target path: {path_error}")
            suggestion.status = ImprovementStatus.FAILED
            suggestion.error_message = f"Path: {path_error}"
            return False

        file_path = str(resolved_path)
        relative_file_path = os.path.relpath(resolved_path, self.project_root)
        new_content, prep_error = self._prepare_suggested_content(suggestion)
        if prep_error:
            logger.error(f"Suggestion preparation failed: {prep_error}")
            suggestion.status = ImprovementStatus.FAILED
            suggestion.error_message = f"Preparation: {prep_error}"
            return False

        logger.info(f"Applying suggestion {suggestion_id}: {relative_file_path}")
        suggestion.status = ImprovementStatus.VALIDATING
        
        # Step 1: Safety Check
        if not force:
            allowed, reason = self.safety_guard.check_modification_allowed(
                file_path, new_content
            )
            if not allowed:
                logger.error(f"Safety check failed: {reason}")
                suggestion.status = ImprovementStatus.FAILED
                suggestion.error_message = f"Safety: {reason}"
                return False
        
        # Step 2: Validation
        if self.config.enable_validation:
            validation_report = await self.validator.validate_modification(
                file_path, new_content
            )
            suggestion.validation_report = validation_report
            
            if not self.validator.can_apply_safely(validation_report):
                logger.error(f"Validation failed: {validation_report.summary}")
                # Emit per-check details for troubleshooting
                for check in validation_report.checks:
                    logger.error(
                        f"Validation check {check.name}: {check.result.value} - {check.message}"
                    )
                suggestion.status = ImprovementStatus.FAILED
                suggestion.error_message = f"Validation: {validation_report.summary}"
                return False
        
        # Step 3: Create Git branch
        branch = None
        if self.config.enable_git_integration and self.git_manager.is_available():
            branch = self.git_manager.create_modification_branch(
                suggestion_id,
                suggestion.description
            )
            if branch:
                suggestion.git_branch = branch.branch_name
        
        # Step 4: Modify file
        suggestion.status = ImprovementStatus.APPLYING
        
        context = ModificationContext(
            suggestion_id=suggestion_id,
            reason=suggestion.description,
            priority=suggestion.priority,
            auto_rollback_on_failure=True
        )
        
        modification = await self.code_modifier.modify_file(
            file_path,
            new_content,
            context
        )
        
        suggestion.modification_attempt = modification
        
        if modification.result != ModificationResult.SUCCESS:
            logger.error(f"Modification failed: {modification.result.value}")
            suggestion.status = ImprovementStatus.FAILED
            suggestion.error_message = f"Modify: {modification.result.value}"
            
            # Record failure with safety guard
            self.safety_guard.record_modification(file_path, new_content, False)
            
            return False
        
        # Step 5: Git commit
        if self.config.auto_commit and branch:
            commit_success, commit_hash = self.git_manager.commit_changes(
                message=suggestion.description,
                files=[relative_file_path],
                description=f"Self-improvement: {suggestion_id}"
            )
            
            if not commit_success:
                logger.warning(f"Git commit failed, but file was modified")
        
        # Success!
        suggestion.status = ImprovementStatus.COMMITTED
        suggestion.applied_at = datetime.now(timezone.utc)
        
        # Record success with safety guard
        self.safety_guard.record_modification(file_path, new_content, True)
        
        # Notify
        if self._on_suggestion_applied:
            await self._notify(self._on_suggestion_applied, suggestion)
        
        logger.info(f"Successfully applied suggestion {suggestion_id}")
        return True
    
    async def approve_and_apply(self, suggestion_id: str) -> bool:
        """
        Approve a pending suggestion and apply it.
        
        Args:
            suggestion_id: ID of suggestion to approve
            
        Returns:
            True if applied successfully
        """
        if suggestion_id not in self.suggestions:
            logger.error(f"Suggestion not found: {suggestion_id}")
            return False
        
        suggestion = self.suggestions[suggestion_id]
        suggestion.status = ImprovementStatus.APPROVED
        
        # Remove from pending
        if suggestion_id in self._pending_approvals:
            self._pending_approvals.remove(suggestion_id)
        
        return await self.apply_suggestion(suggestion)
    
    async def reject_suggestion(self, suggestion_id: str, reason: str = ""):
        """Reject a suggestion."""
        if suggestion_id in self.suggestions:
            suggestion = self.suggestions[suggestion_id]
            suggestion.status = ImprovementStatus.REJECTED
            suggestion.error_message = reason
            
            if suggestion_id in self._pending_approvals:
                self._pending_approvals.remove(suggestion_id)
            
            logger.info(f"Suggestion {suggestion_id} rejected: {reason}")
    
    # ==================== Health & Healing ====================
    
    async def check_health(self) -> Dict:
        """
        Check system health related to self-modification.
        
        Returns:
            Health status dictionary
        """
        checks = await self.emergency_healing.check_system_health()
        
        healthy = self.emergency_healing.is_system_healthy(checks)
        
        return {
            "healthy": healthy,
            "checks": [
                {"name": c.name, "healthy": c.healthy, "message": c.message}
                for c in checks
            ],
            "safety_stats": self.safety_guard.get_stats(),
            "pending_suggestions": len(self._pending_approvals),
        }
    
    async def emergency_heal(self) -> HealingEvent:
        """
        Trigger emergency healing.
        
        Returns:
            HealingEvent with results
        """
        logger.warning("Emergency healing triggered")
        return await self.emergency_healing.heal_system()
    
    def _health_check_callback(self):
        """Custom health check for safety guard."""
        # Check if we have too many failed suggestions
        recent_failures = [
            s for s in self.suggestions.values()
            if s.status == ImprovementStatus.FAILED
            and (datetime.now(timezone.utc) - s.created_at).total_seconds() < 3600
        ]
        
        if len(recent_failures) > 5:
            from src.autonomy.emergency_healing import HealthCheck
            return HealthCheck(
                name="self_improvement_failures",
                healthy=False,
                severity="warning",
                message=f"{len(recent_failures)} recent failures in self-improvement"
            )
        
        return None
    
    # ==================== Status & Monitoring ====================
    
    def get_status(self) -> Dict:
        """Get comprehensive status of self-improvement system."""
        by_status = {}
        for s in self.suggestions.values():
            status = s.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "enabled": self.config.enabled,
            "safety_level": self.safety_guard.get_safety_level().value,
            "total_suggestions": len(self.suggestions),
            "by_status": by_status,
            "pending_approval": len(self._pending_approvals),
            "git_available": self.git_manager.is_available(),
            "modification_stats": self.code_modifier.get_modification_stats(),
            "safety_stats": self.safety_guard.get_stats(),
            "healing_stats": self.emergency_healing.get_stats(),
        }
    
    def get_pending_suggestions(self) -> List[ImprovementSuggestion]:
        """Get suggestions pending approval."""
        return [
            self.suggestions[sid]
            for sid in self._pending_approvals
            if sid in self.suggestions
        ]
    
    def get_suggestion_history(
        self,
        status_filter: Optional[ImprovementStatus] = None,
        limit: int = 20
    ) -> List[ImprovementSuggestion]:
        """Get suggestion history with optional filtering."""
        suggestions = list(self.suggestions.values())
        
        if status_filter:
            suggestions = [s for s in suggestions if s.status == status_filter]
        
        # Sort by created_at descending
        suggestions.sort(key=lambda s: s.created_at, reverse=True)
        
        return suggestions[:limit]
    
    # ==================== Configuration ====================
    
    def set_safety_level(self, level: SafetyLevel):
        """Set safety level."""
        self.safety_guard.set_safety_level(level)
        logger.info(f"Safety level set to: {level.value}")
    
    def emergency_stop(self, reason: str):
        """Emergency stop all modifications."""
        self.safety_guard.emergency_stop(reason)
        logger.critical(f"Emergency stop: {reason}")
    
    def emergency_resume(self):
        """Resume from emergency stop."""
        self.safety_guard.emergency_resume()
        logger.info("Emergency stop cleared")
    
    # ==================== Callbacks ====================
    
    def on_suggestion_created(self, callback: Callable):
        """Register callback for new suggestions."""
        self._on_suggestion_created = callback
    
    def on_suggestion_applied(self, callback: Callable):
        """Register callback for applied suggestions."""
        self._on_suggestion_applied = callback
    
    def on_suggestion_failed(self, callback: Callable):
        """Register callback for failed suggestions."""
        self._on_suggestion_failed = callback
    
    async def _notify(self, callback: Callable, suggestion: ImprovementSuggestion):
        """Safely invoke a callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(suggestion)
            else:
                callback(suggestion)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    # ==================== Helper Methods ====================
    
    def _get_recent_interactions(self) -> List[Dict]:
        """Get recent conversation patterns."""
        # This would integrate with conversation history
        return []
    
    def _get_codebase_sample(self) -> str:
        """Get a sample of codebase for review."""
        if not self.codebase_reader:
            return "# Codebase reader not available"
        
        # Get a few interesting files
        files_to_review = [
            "src/llm/prompt_builder.py",
            "src/integrations/discord_bot.py",
            "src/mobile/api.py",
            "src/emotion/models.py",
        ]
        
        sample = []
        for file_path in files_to_review:
            try:
                full_path = self.project_root / file_path
                if full_path.exists():
                    with open(full_path, 'r') as f:
                        content = f.read()
                        lines = content.split('\n')[:100]
                        sample.append(f"\n# {file_path}\n" + '\n'.join(lines))
            except Exception as e:
                logger.debug(f"Could not read {file_path}: {e}")
        
        return '\n'.join(sample) if sample else "# No sample available"
    
    def _build_review_prompt(
        self,
        recent_interactions: List[Dict],
        sample_code: str
    ) -> str:
        """Build prompt for code review."""
        return f"""You are reviewing your own code (Demi's codebase) to identify improvement opportunities.

Recent conversation patterns:
{self._format_interactions(recent_interactions)}

Sample of current code:
{sample_code}

Based on this, identify specific improvements:
1. Code optimizations and simplifications
2. Missing error handling
3. Better modularity opportunities
4. Performance improvements
5. Bug fixes

For each improvement, provide:
FILE: <relative filepath>
PRIORITY: <low/medium/high>
DESCRIPTION: <brief description>
CURRENT_CODE: <the code to replace (10-30 lines)>
IMPROVED_CODE: <the replacement code>
CONFIDENCE: <0.0-1.0>

Be specific and concrete. Focus on changes you can actually implement."""
    
    def _format_interactions(self, interactions: List[Dict]) -> str:
        """Format interactions for prompt."""
        if not interactions:
            return "No recent interactions available"
        return "\n".join([f"- {i.get('content', '')[:100]}" for i in interactions[-10:]])
    
    def _parse_review_response(self, response: str) -> List[ImprovementSuggestion]:
        """Parse LLM review response into suggestions."""
        response_text = self._extract_response_text(response)
        suggestions = []
        current = {}

        collecting_field: Optional[str] = None

        for raw_line in response_text.split('\n'):
            stripped = raw_line.strip()

            # Check for new suggestion header
            if stripped.startswith('FILE:'):
                # Save previous suggestion if complete
                if current and 'file' in current and 'improved_code' in current:
                    suggestions.append(self._create_suggestion(current))
                current = {'file': stripped.replace('FILE:', '', 1).strip()}
                collecting_field = None
                continue

            # Check for other field headers - also ends code collection
            if stripped.startswith('PRIORITY:'):
                current['priority'] = stripped.replace('PRIORITY:', '', 1).strip().lower()
                collecting_field = None
                continue

            if stripped.startswith('DESCRIPTION:'):
                current['description'] = stripped.replace('DESCRIPTION:', '', 1).strip()
                collecting_field = None
                continue

            if stripped.startswith('CURRENT_CODE:'):
                current['current_code'] = stripped.replace('CURRENT_CODE:', '', 1).strip()
                collecting_field = 'current_code'
                continue

            if stripped.startswith('IMPROVED_CODE:'):
                current['improved_code'] = stripped.replace('IMPROVED_CODE:', '', 1).strip()
                collecting_field = 'improved_code'
                continue

            if stripped.startswith('CONFIDENCE:'):
                try:
                    current['confidence'] = float(stripped.replace('CONFIDENCE:', '', 1).strip())
                except ValueError:
                    current['confidence'] = 0.5
                collecting_field = None
                continue
            
            # Check for other headers that might end code collection
            # This catches cases where the LLM uses different header formats
            if stripped.endswith(':') and not collecting_field:
                collecting_field = None
                continue

            if collecting_field in ('current_code', 'improved_code'):
                existing = current.get(collecting_field, '')
                current[collecting_field] = (
                    f"{existing}\n{raw_line}" if existing else raw_line
                )
        
        # Save last suggestion if complete
        if current and 'file' in current and 'improved_code' in current:
            suggestions.append(self._create_suggestion(current))
        
        # Post-process: clean up any suggestions that might have issues
        for suggestion in suggestions:
            # Strip code fences from parsed content
            if suggestion.current_code:
                suggestion.current_code = self._strip_code_fences(suggestion.current_code)
            if suggestion.suggested_content:
                suggestion.suggested_content = self._strip_code_fences(suggestion.suggested_content)
        
        return suggestions
    
    def _create_suggestion(self, data: Dict) -> ImprovementSuggestion:
        """Create ImprovementSuggestion from parsed data."""
        suggestion_id = f"sugg_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{len(self.suggestions)}"
        
        return ImprovementSuggestion(
            suggestion_id=suggestion_id,
            file_path=data.get('file', 'unknown'),
            description=data.get('description', 'No description'),
            suggested_content=data.get('improved_code', ''),
            current_code=data.get('current_code', ''),
            priority=data.get('priority', 'medium'),
            confidence=data.get('confidence', 0.5),
            created_at=datetime.now(timezone.utc)
        )

    def _extract_response_text(self, response: Any) -> str:
        """Extract string body from inference response payloads."""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str):
                return content
            return str(content or "")
        return str(response or "")

    def _prepare_suggested_content(
        self, suggestion: ImprovementSuggestion
    ) -> tuple[str, Optional[str]]:
        """
        Sanitize and optionally expand suggestion content to full file content.
        Returns (content, error). Error is None when preparation succeeded.
        """
        sanitized = self._strip_code_fences(suggestion.suggested_content)
        if not sanitized.strip():
            return "", "Empty suggested content"

        # Reject obvious parser leaks early.
        if sanitized.lstrip().startswith(("FILE:", "PRIORITY:", "DESCRIPTION:")):
            return "", "Suggestion content still contains metadata headers"

        file_path = suggestion.file_path
        if file_path.endswith(".py"):
            merged = self._merge_snippet_with_existing_file(
                file_path=file_path,
                current_code=suggestion.current_code,
                improved_code=sanitized,
            )
            if merged is not None:
                sanitized = merged

        # Persist sanitized content for traceability.
        suggestion.suggested_content = sanitized
        return sanitized, None

    def _strip_code_fences(self, content: str) -> str:
        """Strip wrapping markdown code fences from generated content."""
        if not content:
            return ""

        normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
        
        # Try to match code blocks with optional language specifier
        # Handle both ```python\ncode\n``` and ```\ncode\n```
        fence_pattern = re.compile(r"^```[a-zA-Z0-9_-]*\n?([\s\S]*?)\n?```$", re.MULTILINE)
        match = fence_pattern.match(normalized)
        if match:
            return match.group(1).strip()

        # If fences exist but not wrapped perfectly, remove fence lines only.
        lines = []
        for line in normalized.split("\n"):
            stripped = line.strip()
            if stripped.startswith("```"):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def _merge_snippet_with_existing_file(
        self,
        file_path: str,
        current_code: str,
        improved_code: str,
    ) -> Optional[str]:
        """
        If CURRENT_CODE is provided and matches file content, apply replacement.
        Returns full file content on success, otherwise None.
        """
        current_code = self._strip_code_fences(current_code)
        if not current_code.strip():
            return None

        resolved_path, error = self._resolve_file_path(file_path)
        if error or not resolved_path.exists():
            return None

        try:
            original = resolved_path.read_text(encoding="utf-8")
        except Exception:
            return None

        if current_code not in original:
            return None

        updated = original.replace(current_code, improved_code, 1)
        logger.info(f"Expanded snippet to full-file update using CURRENT_CODE: {file_path}")
        return updated

    def _resolve_file_path(self, file_path: str) -> tuple[Optional[Path], Optional[str]]:
        """Resolve file path relative to project root and ensure it stays inside root."""
        if not file_path or not isinstance(file_path, str):
            return None, "Missing file path"

        candidate = Path(file_path)
        resolved = candidate.resolve() if candidate.is_absolute() else (self.project_root / candidate).resolve()
        root = self.project_root.resolve()

        try:
            resolved.relative_to(root)
        except ValueError:
            return None, f"Path escapes project root: {file_path}"

        return resolved, None
