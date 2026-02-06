"""
GitManager - Version control integration for Demi's self-modification.

Manages Git operations for autonomous code changes including branching,
committing, and history management. Provides safe Git operations with
conflict detection and rollback capabilities.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from src.core.logger import get_logger

logger = get_logger()


class GitResult(Enum):
    """Result status for Git operations."""
    SUCCESS = "success"
    NOT_A_REPO = "not_a_repo"
    ALREADY_EXISTS = "already_exists"
    BRANCH_FAILED = "branch_failed"
    CHECKOUT_FAILED = "checkout_failed"
    COMMIT_FAILED = "commit_failed"
    MERGE_FAILED = "merge_failed"
    CONFLICT = "conflict"
    PUSH_FAILED = "push_failed"
    PULL_FAILED = "pull_failed"
    CLEAN_FAILED = "clean_failed"
    GIT_NOT_INSTALLED = "git_not_installed"
    ERROR = "error"


@dataclass
class GitCommit:
    """Represents a Git commit."""
    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime
    files_changed: List[str] = field(default_factory=list)


@dataclass
class GitOperation:
    """Record of a Git operation."""
    operation_id: str
    operation_type: str
    timestamp: datetime
    result: GitResult
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict = field(default_factory=dict)


@dataclass
class ModificationBranch:
    """Represents a branch created for self-modification."""
    branch_name: str
    suggestion_id: str
    created_at: datetime
    base_branch: str
    files_modified: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)
    merged: bool = False
    merged_at: Optional[datetime] = None


class GitManager:
    """
    Manage Git operations for Demi's self-modification workflow.
    
    Workflow:
    1. Create branch from main for each suggestion
    2. Apply modifications on that branch
    3. Commit with descriptive message
    4. Optionally merge back to main
    5. Keep history for audit
    
    Safety:
    - Never commits directly to protected branches (main, master)
    - Validates clean working directory before operations
    - Creates descriptive commit messages
    - Tracks all operations for audit
    
    Usage:
        git_mgr = GitManager()
        
        # Start modification
        branch = git_mgr.create_modification_branch("sugg_123", "Optimize emotion decay")
        
        # After file modifications
        git_mgr.commit_changes(
            "Optimize emotion decay calculation",
            ["src/emotion/decay.py"],
            "Improved performance by 20%"
        )
        
        # Merge if tests pass
        git_mgr.merge_to_main(branch.branch_name)
    """
    
    # Branches that should never be directly committed to
    PROTECTED_BRANCHES = {"main", "master", "production", "release"}
    
    # Branch name prefix for self-modifications
    BRANCH_PREFIX = "demi/autonomy"
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Git manager.
        
        Args:
            project_root: Project root directory (default: auto-detect)
        """
        self.project_root = Path(project_root or self._detect_project_root())
        self._git_available = self._check_git_available()
        self._is_repo = self._check_is_repo() if self._git_available else False
        
        # Track operations
        self._operations: List[GitOperation] = []
        self._active_branches: Dict[str, ModificationBranch] = {}
        
        # Track current branch
        self._current_branch: Optional[str] = None
        if self._is_repo:
            self._current_branch = self._get_current_branch()
        
        logger.info(
            f"GitManager initialized: available={self._git_available}, "
            f"is_repo={self._is_repo}, branch={self._current_branch}"
        )
    
    def _detect_project_root(self) -> str:
        """Auto-detect project root."""
        current_file = Path(__file__).resolve()
        return str(current_file.parent.parent.parent)
    
    def _check_git_available(self) -> bool:
        """Check if Git is installed and available."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_is_repo(self) -> bool:
        """Check if project root is a Git repository."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_root), "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
    
    def _run_git(self, args: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Run a Git command.
        
        Returns:
            (success, stdout, stderr)
        """
        if not self._git_available:
            return False, "", "Git not installed"
        
        cmd = ["git", "-C", str(self.project_root)] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            success = result.returncode == 0
            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)
    
    def _get_current_branch(self) -> Optional[str]:
        """Get the current Git branch name."""
        success, stdout, stderr = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        if success:
            return stdout.strip()
        return None
    
    def is_available(self) -> bool:
        """Check if Git operations are available."""
        return self._git_available and self._is_repo
    
    def is_clean_working_directory(self) -> bool:
        """Check if working directory is clean (no uncommitted changes)."""
        if not self.is_available():
            return False
        
        success, stdout, _ = self._run_git(["status", "--porcelain"])
        if success:
            return len(stdout.strip()) == 0
        return False
    
    def get_status(self) -> Dict:
        """Get current Git status."""
        if not self.is_available():
            return {"available": False}
        
        # Get branch
        branch = self._get_current_branch()
        
        # Get status
        _, status_out, _ = self._run_git(["status", "--short"])
        
        # Get last commit
        _, log_out, _ = self._run_git([
            "log", "-1", "--format=%H|%s|%an|%ai"
        ])
        
        last_commit = None
        if log_out:
            parts = log_out.strip().split("|", 3)
            if len(parts) >= 4:
                last_commit = {
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3]
                }
        
        # Count uncommitted changes
        uncommitted = len([l for l in status_out.split('\n') if l.strip()]) if status_out else 0
        
        return {
            "available": True,
            "branch": branch,
            "is_clean": uncommitted == 0,
            "uncommitted_changes": uncommitted,
            "last_commit": last_commit,
            "protected_branch": branch in self.PROTECTED_BRANCHES if branch else False,
        }
    
    def create_modification_branch(
        self,
        suggestion_id: str,
        description: str
    ) -> Optional[ModificationBranch]:
        """
        Create a new branch for a self-modification.
        
        Args:
            suggestion_id: Unique ID for the suggestion
            description: Short description for branch name
            
        Returns:
            ModificationBranch if successful, None otherwise
        """
        if not self.is_available():
            logger.error("Git not available for branch creation")
            return None
        
        # Ensure clean working directory
        if not self.is_clean_working_directory():
            logger.warning("Working directory not clean, stashing changes")
            self._run_git(["stash", "push", "-m", "Auto-stash before Demi modification"])
        
        # Sanitize description for branch name
        sanitized = re.sub(r'[^\w\-]', '-', description.lower())[:50]
        branch_name = f"{self.BRANCH_PREFIX}/{sanitized}-{suggestion_id[:8]}"
        
        # Get current branch as base
        base_branch = self._get_current_branch() or "main"
        
        # Create branch
        success, stdout, stderr = self._run_git(["checkout", "-b", branch_name])
        
        if not success:
            # Branch might already exist, try to checkout
            success, _, _ = self._run_git(["checkout", branch_name])
            if not success:
                logger.error(f"Failed to create branch {branch_name}: {stderr}")
                return None
        
        self._current_branch = branch_name
        
        # Track the branch
        branch_info = ModificationBranch(
            branch_name=branch_name,
            suggestion_id=suggestion_id,
            created_at=datetime.now(timezone.utc),
            base_branch=base_branch
        )
        self._active_branches[suggestion_id] = branch_info
        
        logger.info(f"Created modification branch: {branch_name}")
        return branch_info
    
    def checkout_branch(self, branch_name: str) -> bool:
        """Checkout an existing branch."""
        if not self.is_available():
            return False
        
        success, _, stderr = self._run_git(["checkout", branch_name])
        if success:
            self._current_branch = branch_name
            return True
        else:
            logger.error(f"Failed to checkout {branch_name}: {stderr}")
            return False
    
    def commit_changes(
        self,
        message: str,
        files: List[str],
        description: Optional[str] = None,
        author_name: str = "Demi",
        author_email: str = "self@demi.ai"
    ) -> Tuple[bool, Optional[str]]:
        """
        Commit file changes with proper attribution.
        
        Args:
            message: Commit message summary
            files: List of files to commit
            description: Extended description
            author_name: Commit author name
            author_email: Commit author email
            
        Returns:
            (success, commit_hash_or_error)
        """
        if not self.is_available():
            return False, "Git not available"
        
        # Check for protected branch
        current = self._get_current_branch()
        if current in self.PROTECTED_BRANCHES:
            error_msg = f"Cannot commit directly to protected branch: {current}"
            logger.error(error_msg)
            return False, error_msg
        
        # Stage files
        for file_path in files:
            # Convert to relative path
            rel_path = os.path.relpath(file_path, self.project_root)
            success, _, stderr = self._run_git(["add", rel_path])
            if not success:
                logger.warning(f"Failed to stage {rel_path}: {stderr}")
        
        # Build commit message
        full_message = f"[Demi Autonomy] {message}\n\n"
        full_message += f"Self-modification by Demi AI companion.\n"
        if description:
            full_message += f"\n{description}\n"
        full_message += f"\nTimestamp: {datetime.now(timezone.utc).isoformat()}"
        
        # Commit
        success, stdout, stderr = self._run_git([
            "-c", f"user.name={author_name}",
            "-c", f"user.email={author_email}",
            "commit",
            "-m", full_message
        ])
        
        if success:
            # Get commit hash
            _, hash_out, _ = self._run_git(["rev-parse", "HEAD"])
            commit_hash = hash_out.strip()
            
            # Update active branch tracking
            for branch_info in self._active_branches.values():
                if branch_info.branch_name == current:
                    branch_info.commits.append(commit_hash)
                    branch_info.files_modified.extend(files)
            
            logger.info(f"Committed changes: {commit_hash[:8]} - {message}")
            return True, commit_hash
        else:
            logger.error(f"Commit failed: {stderr}")
            return False, stderr
    
    def merge_to_main(
        self,
        branch_name: str,
        merge_message: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Merge a modification branch to main/master.
        
        Args:
            branch_name: Branch to merge
            merge_message: Custom merge message
            
        Returns:
            (success, message)
        """
        if not self.is_available():
            return False, "Git not available"
        
        # Find main branch
        main_branch = "main"
        success, _, _ = self._run_git(["show-ref", "--verify", "--quiet", "refs/heads/main"])
        if not success:
            main_branch = "master"
        
        # Save current branch
        original_branch = self._get_current_branch()
        
        # Checkout main
        if not self.checkout_branch(main_branch):
            return False, f"Failed to checkout {main_branch}"
        
        # Pull latest (optional, might fail if no remote)
        self._run_git(["pull", "origin", main_branch])
        
        # Merge
        msg = merge_message or f"Merge self-modification: {branch_name}"
        success, stdout, stderr = self._run_git([
            "merge",
            "--no-ff",  # Create merge commit
            "-m", msg,
            branch_name
        ])
        
        if success:
            logger.info(f"Merged {branch_name} to {main_branch}")
            
            # Update branch tracking
            for branch_info in self._active_branches.values():
                if branch_info.branch_name == branch_name:
                    branch_info.merged = True
                    branch_info.merged_at = datetime.now(timezone.utc)
            
            # Optionally delete the branch
            self._run_git(["branch", "-d", branch_name])
            
            return True, f"Successfully merged to {main_branch}"
        else:
            # Check for conflicts
            if "CONFLICT" in stderr:
                logger.error(f"Merge conflict: {stderr}")
                # Abort merge
                self._run_git(["merge", "--abort"])
                # Return to original branch
                if original_branch:
                    self.checkout_branch(original_branch)
                return False, f"Merge conflict: {stderr}"
            
            logger.error(f"Merge failed: {stderr}")
            if original_branch:
                self.checkout_branch(original_branch)
            return False, f"Merge failed: {stderr}"
    
    def get_commit_history(
        self,
        branch: Optional[str] = None,
        max_count: int = 20,
        author_filter: Optional[str] = "Demi"
    ) -> List[GitCommit]:
        """
        Get commit history with optional filtering.
        
        Args:
            branch: Branch to query (default: current)
            max_count: Maximum commits to return
            author_filter: Filter by author (None for all)
            
        Returns:
            List of GitCommit objects
        """
        if not self.is_available():
            return []
        
        branch_ref = branch or self._get_current_branch() or "HEAD"
        
        # Format: hash|short_hash|message|author|date
        format_str = "%H|%h|%s|%an|%ai"
        
        cmd = ["log", branch_ref, f"--max-count={max_count}", f"--format={format_str}"]
        
        if author_filter:
            cmd.extend(["--author", author_filter])
        
        success, stdout, _ = self._run_git(cmd)
        
        commits = []
        if success:
            for line in stdout.strip().split('\n'):
                if '|' not in line:
                    continue
                
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    commits.append(GitCommit(
                        hash=parts[0],
                        short_hash=parts[1],
                        message=parts[2],
                        author=parts[3],
                        date=datetime.fromisoformat(parts[4])
                    ))
        
        return commits
    
    def get_diff(self, commit_hash: Optional[str] = None) -> str:
        """
        Get diff for a commit or uncommitted changes.
        
        Args:
            commit_hash: Specific commit (None for uncommitted changes)
            
        Returns:
            Diff content
        """
        if not self.is_available():
            return ""
        
        if commit_hash:
            success, stdout, _ = self._run_git(["show", commit_hash, "--format="])
        else:
            success, stdout, _ = self._run_git(["diff"])
        
        return stdout if success else ""
    
    def stash_changes(self, message: Optional[str] = None) -> bool:
        """Stash current changes."""
        if not self.is_available():
            return False
        
        msg = message or f"Demi auto-stash {datetime.now(timezone.utc).isoformat()}"
        success, _, _ = self._run_git(["stash", "push", "-m", msg])
        return success
    
    def pop_stash(self) -> bool:
        """Pop the latest stash."""
        if not self.is_available():
            return False
        
        success, _, _ = self._run_git(["stash", "pop"])
        return success
    
    def discard_changes(self, file_path: Optional[str] = None) -> bool:
        """
        Discard uncommitted changes.
        
        Args:
            file_path: Specific file (None for all changes)
        """
        if not self.is_available():
            return False
        
        if file_path:
            rel_path = os.path.relpath(file_path, self.project_root)
            success, _, _ = self._run_git(["checkout", "--", rel_path])
        else:
            success, _, _ = self._run_git(["reset", "--hard", "HEAD"])
        
        return success
    
    def get_modified_files(self) -> List[str]:
        """Get list of modified files (uncommitted)."""
        if not self.is_available():
            return []
        
        success, stdout, _ = self._run_git(["diff", "--name-only"])
        if success:
            return [f.strip() for f in stdout.split('\n') if f.strip()]
        return []
    
    def get_stats(self) -> Dict:
        """Get Git statistics."""
        if not self.is_available():
            return {"available": False}
        
        # Total commits by Demi
        commits = self.get_commit_history(max_count=1000)
        
        # Branches
        success, stdout, _ = self._run_git(["branch", "-a"])
        branches = [b.strip().strip('* ') for b in stdout.split('\n') if b.strip()]
        
        # Modification branches
        mod_branches = [b for b in branches if self.BRANCH_PREFIX in b]
        
        return {
            "available": True,
            "total_commits_by_demi": len(commits),
            "total_branches": len(branches),
            "modification_branches": len(mod_branches),
            "active_modifications": len(self._active_branches),
            "current_branch": self._current_branch,
            "is_clean": self.is_clean_working_directory(),
        }
