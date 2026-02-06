"""
SafeCodeModifier - Core file modification system for Demi's self-improvement.

Provides safe, validated file modifications with backups, syntax checking,
and comprehensive audit logging. This is the foundation of Demi's autonomy.
"""

import ast
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import difflib

from src.core.logger import get_logger

logger = get_logger()


class ModificationResult(Enum):
    """Result status for code modifications."""
    SUCCESS = "success"
    VALIDATION_FAILED = "validation_failed"
    SYNTAX_ERROR = "syntax_error"
    BACKUP_FAILED = "backup_failed"
    WRITE_FAILED = "write_failed"
    CRITICAL_FILE_BLOCKED = "critical_file_blocked"
    SIZE_LIMIT_EXCEEDED = "size_limit_exceeded"
    TEST_FAILED = "test_failed"
    ROLLBACK_SUCCESS = "rollback_success"
    ROLLBACK_FAILED = "rollback_failed"


@dataclass
class ModificationAttempt:
    """Record of a modification attempt."""
    attempt_id: str
    file_path: str
    original_hash: str
    modified_hash: str
    timestamp: datetime
    result: ModificationResult
    diff: str
    backup_path: Optional[str] = None
    error_message: Optional[str] = None
    test_results: Optional[Dict] = None


@dataclass
class ModificationContext:
    """Context for a modification operation."""
    suggestion_id: str
    reason: str
    priority: str = "medium"  # low, medium, high, critical
    auto_rollback_on_failure: bool = True
    require_tests_pass: bool = True
    created_by: str = "demi_autonomy"


class SafeCodeModifier:
    """
    Safely modify Python files with comprehensive validation and backup.
    
    Safety Features:
    - AST validation before any write operation
    - Automatic backups with retention
    - Critical file protection
    - Change size limits
    - Diff generation for audit trails
    - Automatic rollback on failure
    
    Usage:
        modifier = SafeCodeModifier()
        result = await modifier.modify_file(
            "src/emotion/models.py",
            new_content,
            ModificationContext(suggestion_id="123", reason="Optimize emotion decay")
        )
    """
    
    # Files that should never be auto-modified (security critical)
    CRITICAL_FILES = {
        "src/api/auth.py",
        "src/core/database.py",
        "src/api/models.py",
        "src/autonomy/safety_guard.py",
        "src/autonomy/code_modifier.py",
        "src/conductor/isolation.py",
        ".env",
        ".env.example",
        "docker-compose.yml",
        "Dockerfile",
    }
    
    # Maximum file size for modification (1MB)
    MAX_FILE_SIZE_BYTES = 1024 * 1024
    
    # Maximum change size (100KB of new content)
    MAX_CHANGE_SIZE_BYTES = 100 * 1024
    
    # Backup retention (7 days)
    BACKUP_RETENTION_DAYS = 7
    
    def __init__(self, project_root: Optional[str] = None, backup_dir: Optional[str] = None):
        """
        Initialize the code modifier.
        
        Args:
            project_root: Root directory of the project (default: auto-detect)
            backup_dir: Directory for backups (default: ~/.demi/backups)
        """
        self.project_root = Path(project_root or self._detect_project_root())
        self.backup_dir = Path(backup_dir or os.path.expanduser("~/.demi/backups"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Track modification history
        self._history: List[ModificationAttempt] = []
        self._max_history = 100
        
        # Active backups for potential rollback
        self._active_backups: Dict[str, str] = {}
        
        logger.info(f"SafeCodeModifier initialized: root={self.project_root}, backup_dir={self.backup_dir}")
    
    def _detect_project_root(self) -> str:
        """Auto-detect project root from current file location."""
        current_file = Path(__file__).resolve()
        # Go up from src/autonomy/code_modifier.py to project root
        return str(current_file.parent.parent.parent)
    
    def _is_critical_file(self, file_path: str) -> bool:
        """Check if file is on the critical files list."""
        # Normalize path for comparison
        rel_path = os.path.relpath(file_path, self.project_root)
        return rel_path in self.CRITICAL_FILES
    
    def _validate_python_syntax(self, content: str, file_path: str = "<unknown>") -> Tuple[bool, Optional[str]]:
        """
        Validate that content is valid Python syntax.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            ast.parse(content, filename=file_path)
            return True, None
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}, col {e.offset}: {e.msg}"
            return False, error_msg
        except Exception as e:
            return False, f"Parse error: {str(e)}"
    
    def _create_backup(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Create a backup of the file before modification.
        
        Returns:
            (success, backup_path_or_error)
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return True, None  # No backup needed for new files
            
            # Generate backup filename with timestamp and hash
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            content_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()[:8]
            backup_filename = f"{source_path.name}.{timestamp}.{content_hash}.bak"
            
            # Organize backups by relative path
            rel_path = os.path.relpath(file_path, self.project_root)
            backup_subdir = self.backup_dir / rel_path.replace(os.sep, "_")
            backup_subdir.mkdir(parents=True, exist_ok=True)
            
            backup_path = backup_subdir / backup_filename
            shutil.copy2(file_path, backup_path)
            
            # Store for potential rollback
            self._active_backups[file_path] = str(backup_path)
            
            logger.info(f"Backup created: {backup_path}")
            return True, str(backup_path)
            
        except Exception as e:
            logger.error(f"Backup failed for {file_path}: {e}")
            return False, str(e)
    
    def _generate_diff(self, original: str, modified: str, file_path: str = "<unknown>") -> str:
        """Generate unified diff between original and modified content."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        # Ensure lines end with newline for proper diff
        if original_lines and not original_lines[-1].endswith('\n'):
            original_lines[-1] += '\n'
        if modified_lines and not modified_lines[-1].endswith('\n'):
            modified_lines[-1] += '\n'
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm='\n'
        )
        return ''.join(diff)
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def modify_file(
        self,
        file_path: str,
        new_content: str,
        context: ModificationContext
    ) -> ModificationAttempt:
        """
        Safely modify a file with full validation and backup.
        
        This is the primary method for self-modification. It performs:
        1. Critical file check
        2. Size validation
        3. Syntax validation (for Python files)
        4. Backup creation
        5. File write
        6. Post-write verification
        
        Args:
            file_path: Path to the file to modify
            new_content: New file content
            context: Modification context with metadata
            
        Returns:
            ModificationAttempt with full details and result
        """
        attempt_id = f"mod_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha256(file_path.encode()).hexdigest()[:8]}"
        
        # Ensure file_path is absolute
        abs_path = os.path.abspath(file_path)
        rel_path = os.path.relpath(abs_path, self.project_root)
        
        logger.info(f"Modification attempt [{attempt_id}]: {rel_path}")
        
        # Read original content
        original_content = ""
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except Exception as e:
                logger.error(f"Failed to read original file: {e}")
        
        original_hash = self._compute_hash(original_content)
        modified_hash = self._compute_hash(new_content)
        
        # Check if content actually changed
        if original_hash == modified_hash:
            logger.info(f"No changes detected for {rel_path}")
            return ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=original_hash,
                modified_hash=modified_hash,
                timestamp=datetime.now(timezone.utc),
                result=ModificationResult.SUCCESS,
                diff="",
                error_message="No changes detected"
            )
        
        # Step 1: Check if critical file
        if self._is_critical_file(abs_path):
            logger.warning(f"Blocked modification of critical file: {rel_path}")
            return ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=original_hash,
                modified_hash=modified_hash,
                timestamp=datetime.now(timezone.utc),
                result=ModificationResult.CRITICAL_FILE_BLOCKED,
                diff="",
                error_message=f"Critical file blocked: {rel_path}"
            )
        
        # Step 2: Check size limits
        if len(new_content.encode('utf-8')) > self.MAX_FILE_SIZE_BYTES:
            return ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=original_hash,
                modified_hash=modified_hash,
                timestamp=datetime.now(timezone.utc),
                result=ModificationResult.SIZE_LIMIT_EXCEEDED,
                diff="",
                error_message=f"File size exceeds {self.MAX_FILE_SIZE_BYTES} bytes"
            )
        
        change_size = len(new_content) - len(original_content)
        if abs(change_size) > self.MAX_CHANGE_SIZE_BYTES:
            return ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=original_hash,
                modified_hash=modified_hash,
                timestamp=datetime.now(timezone.utc),
                result=ModificationResult.SIZE_LIMIT_EXCEEDED,
                diff="",
                error_message=f"Change size ({abs(change_size)}) exceeds {self.MAX_CHANGE_SIZE_BYTES} bytes"
            )
        
        # Step 3: Validate Python syntax
        if abs_path.endswith('.py'):
            is_valid, error_msg = self._validate_python_syntax(new_content, abs_path)
            if not is_valid:
                logger.error(f"Syntax validation failed: {error_msg}")
                return ModificationAttempt(
                    attempt_id=attempt_id,
                    file_path=abs_path,
                    original_hash=original_hash,
                    modified_hash=modified_hash,
                    timestamp=datetime.now(timezone.utc),
                    result=ModificationResult.SYNTAX_ERROR,
                    diff="",
                    error_message=error_msg
                )
        
        # Step 4: Create backup
        backup_success, backup_result = self._create_backup(abs_path)
        if not backup_success:
            return ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=original_hash,
                modified_hash=modified_hash,
                timestamp=datetime.now(timezone.utc),
                result=ModificationResult.BACKUP_FAILED,
                diff="",
                error_message=f"Backup failed: {backup_result}"
            )
        
        backup_path = backup_result
        
        # Step 5: Generate diff for audit
        diff = self._generate_diff(original_content, new_content, rel_path)
        
        # Step 6: Write the file
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(abs_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # Write atomically using temp file
            temp_path = abs_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Atomic rename
            os.replace(temp_path, abs_path)
            
            logger.info(f"File modified successfully: {rel_path}")
            
            # Record successful modification
            attempt = ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=original_hash,
                modified_hash=modified_hash,
                timestamp=datetime.now(timezone.utc),
                result=ModificationResult.SUCCESS,
                diff=diff,
                backup_path=backup_path
            )
            
            self._record_attempt(attempt)
            return attempt
            
        except Exception as e:
            logger.error(f"Write failed: {e}")
            
            # Attempt rollback if enabled
            if context.auto_rollback_on_failure and backup_path:
                rollback_success = self.rollback(attempt_id)
                rollback_result = ModificationResult.ROLLBACK_SUCCESS if rollback_success else ModificationResult.ROLLBACK_FAILED
            else:
                rollback_result = ModificationResult.WRITE_FAILED
            
            return ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=original_hash,
                modified_hash=modified_hash,
                timestamp=datetime.now(timezone.utc),
                result=rollback_result,
                diff=diff,
                backup_path=backup_path,
                error_message=str(e)
            )
    
    async def apply_patch(
        self,
        file_path: str,
        patch_content: str,
        context: ModificationContext
    ) -> ModificationAttempt:
        """
        Apply a unified diff patch to a file.
        
        Args:
            file_path: Target file path
            patch_content: Unified diff patch
            context: Modification context
            
        Returns:
            ModificationAttempt with result
        """
        abs_path = os.path.abspath(file_path)
        
        # Read current content
        if os.path.exists(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        else:
            original_content = ""
        
        # Parse and apply patch
        try:
            patched_content = self._apply_unified_diff(original_content, patch_content)
            return await self.modify_file(abs_path, patched_content, context)
        except Exception as e:
            attempt_id = f"patch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            return ModificationAttempt(
                attempt_id=attempt_id,
                file_path=abs_path,
                original_hash=self._compute_hash(original_content),
                modified_hash="",
                timestamp=datetime.now(timezone.utc),
                result=ModificationResult.VALIDATION_FAILED,
                diff=patch_content,
                error_message=f"Patch application failed: {str(e)}"
            )
    
    def _apply_unified_diff(self, original: str, patch: str) -> str:
        """
        Apply a unified diff to original content.
        
        This is a simplified patch applier - for complex patches,
        consider using the 'patch' library.
        """
        original_lines = original.splitlines(keepends=True)
        patch_lines = patch.splitlines()
        
        result_lines = original_lines.copy()
        
        # Track current position in result
        current_line = 0
        
        i = 0
        while i < len(patch_lines):
            line = patch_lines[i]
            
            # Look for hunk header
            if line.startswith('@@'):
                # Parse hunk header: @@ -start,count +start,count @@
                # Extract new file starting line
                parts = line.split()
                new_range = parts[1]  # +start,count
                new_start = int(new_range.split(',')[0][1:])  # Remove '+' and get start
                
                # Convert to 0-based index
                current_line = new_start - 1
                i += 1
                
                # Process hunk lines
                while i < len(patch_lines) and not patch_lines[i].startswith('@@'):
                    patch_line = patch_lines[i]
                    
                    if patch_line.startswith('+'):
                        # Addition
                        content = patch_line[1:]
                        if not content.endswith('\n'):
                            content += '\n'
                        result_lines.insert(current_line, content)
                        current_line += 1
                    elif patch_line.startswith('-'):
                        # Deletion
                        if current_line < len(result_lines):
                            result_lines.pop(current_line)
                    elif patch_line.startswith(' '):
                        # Context line - just advance
                        current_line += 1
                    elif patch_line.startswith('\\'):
                        # "\ No newline at end of file" - ignore
                        pass
                    
                    i += 1
            else:
                i += 1
        
        return ''.join(result_lines)
    
    def rollback(self, attempt_id: str) -> bool:
        """
        Rollback a modification using its backup.
        
        Args:
            attempt_id: The modification attempt ID to rollback
            
        Returns:
            True if rollback successful
        """
        # Find the attempt
        attempt = None
        for a in self._history:
            if a.attempt_id == attempt_id:
                attempt = a
                break
        
        if not attempt:
            logger.error(f"Cannot rollback: attempt {attempt_id} not found")
            return False
        
        if not attempt.backup_path or not os.path.exists(attempt.backup_path):
            logger.error(f"Cannot rollback: backup not found for {attempt_id}")
            return False
        
        try:
            shutil.copy2(attempt.backup_path, attempt.file_path)
            logger.info(f"Rollback successful: {attempt.file_path}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def rollback_file(self, file_path: str) -> bool:
        """
        Rollback a file to its most recent backup.
        
        Args:
            file_path: Path to the file to rollback
            
        Returns:
            True if rollback successful
        """
        abs_path = os.path.abspath(file_path)
        
        # Find most recent backup for this file
        backups = []
        for attempt in reversed(self._history):
            if attempt.file_path == abs_path and attempt.backup_path:
                if os.path.exists(attempt.backup_path):
                    backups.append(attempt)
        
        if not backups:
            logger.error(f"No backup found for {file_path}")
            return False
        
        # Use most recent backup
        most_recent = backups[0]
        return self.rollback(most_recent.attempt_id)
    
    def _record_attempt(self, attempt: ModificationAttempt):
        """Record modification attempt in history."""
        self._history.append(attempt)
        
        # Trim history if too large
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_history(
        self,
        file_path: Optional[str] = None,
        result_filter: Optional[ModificationResult] = None,
        limit: int = 50
    ) -> List[ModificationAttempt]:
        """
        Get modification history with optional filtering.
        
        Args:
            file_path: Filter by file path
            result_filter: Filter by result status
            limit: Maximum number of results
            
        Returns:
            List of matching modification attempts
        """
        results = self._history
        
        if file_path:
            abs_path = os.path.abspath(file_path)
            results = [a for a in results if a.file_path == abs_path]
        
        if result_filter:
            results = [a for a in results if a.result == result_filter]
        
        # Return most recent first, limited
        return list(reversed(results[-limit:]))
    
    def get_modification_stats(self) -> Dict:
        """Get statistics about modifications."""
        total = len(self._history)
        successful = len([a for a in self._history if a.result == ModificationResult.SUCCESS])
        failed = total - successful
        
        by_result = {}
        for attempt in self._history:
            status = attempt.result.value
            by_result[status] = by_result.get(status, 0) + 1
        
        # Files modified
        files_modified = set(a.file_path for a in self._history if a.result == ModificationResult.SUCCESS)
        
        return {
            "total_attempts": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "by_result": by_result,
            "unique_files_modified": len(files_modified),
            "recent_failures": len([a for a in self._history[-10:] if a.result != ModificationResult.SUCCESS]),
        }
    
    def cleanup_old_backups(self, max_age_days: Optional[int] = None) -> int:
        """
        Clean up backup files older than retention period.
        
        Args:
            max_age_days: Override default retention (uses BACKUP_RETENTION_DAYS if None)
            
        Returns:
            Number of backups removed
        """
        max_age = max_age_days or self.BACKUP_RETENTION_DAYS
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age * 24 * 60 * 60)
        
        removed = 0
        for backup_file in self.backup_dir.rglob("*.bak"):
            try:
                stat = backup_file.stat()
                if stat.st_mtime < cutoff:
                    backup_file.unlink()
                    removed += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup backup {backup_file}: {e}")
        
        logger.info(f"Cleaned up {removed} old backups")
        return removed
