"""
Change Tracking & Auto-Documentation System

Automatically commits and documents Demi's changes:
1. Auto-commit to git with descriptive messages
2. Generate CHANGELOG entries
3. Track improvement metrics over time
4. Document rationale for changes

Integration with self-evolution systems for full traceability.
"""

import os
import re
import json
import subprocess
import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.core.logger import get_logger
from src.autonomy.git_manager import GitManager

logger = get_logger()


@dataclass
class ChangeRecord:
    """Record of a change made by Demi."""
    
    change_id: str
    timestamp: str
    category: str  # 'error_fix', 'quality_improvement', 'optimization', etc.
    files_modified: List[str]
    description: str
    rationale: str
    before_metrics: Optional[Dict[str, float]] = None
    after_metrics: Optional[Dict[str, float]] = None
    git_commit_hash: Optional[str] = None
    git_branch: Optional[str] = None
    approved: bool = False
    approved_by: Optional[str] = None  # 'demi_auto', 'human', 'system'
    reverted: bool = False


class ChangeTracker:
    """
    Tracks and documents all changes made by Demi.
    
    Features:
    - Auto-commit changes with descriptive messages
    - Generate CHANGELOG entries
    - Track improvement metrics
    - Maintain audit trail
    """
    
    def __init__(self, project_root: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize change tracker.
        
        Args:
            project_root: Root of git repository
            db_path: Path to SQLite database
        """
        self.project_root = Path(project_root or self._detect_project_root())
        self.db_path = db_path or self._get_default_db_path()
        self.git = GitManager(str(self.project_root))
        
        self._init_database()
        self._init_changelog()
        
        logger.info(f"ChangeTracker initialized: {self.project_root}")
    
    def _detect_project_root(self) -> str:
        """Auto-detect project root from git."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return str(Path(__file__).parent.parent.parent.parent)
    
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        data_dir = Path.home() / ".demi"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "changes.db")
    
    def _init_database(self):
        """Initialize change tracking database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS changes (
                    change_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    files_modified TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rationale TEXT,
                    before_metrics TEXT,
                    after_metrics TEXT,
                    git_commit_hash TEXT,
                    git_branch TEXT,
                    approved BOOLEAN DEFAULT 0,
                    approved_by TEXT,
                    reverted BOOLEAN DEFAULT 0
                )
            """)
            conn.commit()
    
    def _init_changelog(self):
        """Initialize CHANGELOG.md if it doesn't exist."""
        changelog_path = self.project_root / "CHANGELOG.md"
        if not changelog_path.exists():
            changelog_path.write_text("""# Changelog

All notable changes to Demi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Self-evolution capabilities (Phase 2)

""")
    
    def record_change(
        self,
        category: str,
        files_modified: List[str],
        description: str,
        rationale: str,
        before_metrics: Optional[Dict[str, float]] = None,
        after_metrics: Optional[Dict[str, float]] = None,
        auto_commit: bool = True,
        auto_approve: bool = False
    ) -> ChangeRecord:
        """
        Record a change made by Demi.
        
        Args:
            category: Type of change (error_fix, improvement, etc.)
            files_modified: List of files changed
            description: What was changed
            rationale: Why it was changed
            before_metrics: Metrics before change
            after_metrics: Metrics after change
            auto_commit: Whether to auto-commit to git
            auto_approve: Whether to auto-approve (for safe changes)
            
        Returns:
            ChangeRecord with details
        """
        import uuid
        
        change = ChangeRecord(
            change_id=f"chg_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            category=category,
            files_modified=files_modified,
            description=description,
            rationale=rationale,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            approved=auto_approve,
            approved_by="demi_auto" if auto_approve else None,
            git_branch=self.git.get_current_branch() if self.git.is_available() else None,
        )
        
        # Auto-commit if requested and git is available
        if auto_commit and self.git.is_available():
            commit_hash = self._auto_commit(change)
            change.git_commit_hash = commit_hash
        
        # Store in database
        self._store_change(change)
        
        # Update CHANGELOG
        self._update_changelog(change)
        
        logger.info(
            f"Change recorded: {change.change_id}",
            category=category,
            files=len(files_modified),
            committed=bool(change.git_commit_hash)
        )
        
        return change
    
    def _auto_commit(self, change: ChangeRecord) -> Optional[str]:
        """
        Auto-commit changes to git.
        
        Args:
            change: Change to commit
            
        Returns:
            Commit hash if successful
        """
        try:
            # Check if there are changes to commit
            if self.git.is_clean_working_directory():
                logger.warning("No changes to commit")
                return None
            
            # Stage files
            for file_path in change.files_modified:
                full_path = self.project_root / file_path
                if full_path.exists():
                    subprocess.run(
                        ["git", "add", str(file_path)],
                        cwd=self.project_root,
                        check=True,
                        capture_output=True
                    )
            
            # Create commit message
            commit_msg = self._generate_commit_message(change)
            
            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = hash_result.stdout.strip()
            
            logger.info(f"Auto-committed: {commit_hash[:8]}")
            return commit_hash
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Auto-commit failed: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Auto-commit error: {e}")
            return None
    
    def _generate_commit_message(self, change: ChangeRecord) -> str:
        """Generate descriptive commit message."""
        # Category emoji mapping
        emojis = {
            "error_fix": "🐛",
            "quality_improvement": "✨",
            "optimization": "⚡",
            "refactor": "♻️",
            "docs": "📝",
            "safety": "🔒",
            "emotion": "💕",
            "voice": "🎙️",
            "metrics": "📊",
        }
        
        emoji = emojis.get(change.category, "🔧")
        
        # Build commit message
        lines = [
            f"{emoji} [{change.category}] {change.description}",
            "",
            f"Change-Id: {change.change_id}",
            f"Rationale: {change.rationale}",
        ]
        
        # Add metrics if available
        if change.before_metrics and change.after_metrics:
            lines.append("")
            lines.append("Metrics:")
            for key in change.before_metrics:
                before = change.before_metrics[key]
                after = change.after_metrics.get(key, before)
                delta = after - before
                sign = "+" if delta > 0 else ""
                lines.append(f"  {key}: {before:.2f} → {after:.2f} ({sign}{delta:.2f})")
        
        return "\n".join(lines)
    
    def _store_change(self, change: ChangeRecord):
        """Store change in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO changes 
                (change_id, timestamp, category, files_modified, description,
                 rationale, before_metrics, after_metrics, git_commit_hash,
                 git_branch, approved, approved_by, reverted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change.change_id,
                    change.timestamp,
                    change.category,
                    json.dumps(change.files_modified),
                    change.description,
                    change.rationale,
                    json.dumps(change.before_metrics) if change.before_metrics else None,
                    json.dumps(change.after_metrics) if change.after_metrics else None,
                    change.git_commit_hash,
                    change.git_branch,
                    change.approved,
                    change.approved_by,
                    change.reverted,
                )
            )
            conn.commit()
    
    def _update_changelog(self, change: ChangeRecord):
        """Update CHANGELOG.md with the change."""
        try:
            changelog_path = self.project_root / "CHANGELOG.md"
            if not changelog_path.exists():
                return
            
            content = changelog_path.read_text()
            
            # Find "## [Unreleased]" section
            unreleased_pattern = r"(## \[Unreleased\].*?\n)(## \[|$)"
            match = re.search(unreleased_pattern, content, re.DOTALL)
            
            if match:
                # Determine subsection based on category
                if change.category in ["error_fix", "bugfix", "fix"]:
                    subsection = "### Fixed"
                elif change.category in ["optimization", "performance"]:
                    subsection = "### Changed"
                elif change.category in ["docs", "documentation"]:
                    subsection = "### Docs"
                else:
                    subsection = "### Added"
                
                # Build entry
                entry = f"- {change.description} ({change.change_id})"
                if change.rationale:
                    entry += f"\n  - *Rationale:* {change.rationale}"
                
                # Insert into appropriate subsection
                subsection_pattern = rf"({subsection}\n)"
                if re.search(subsection_pattern, content):
                    # Add to existing subsection
                    content = re.sub(
                        subsection_pattern,
                        rf"\1- {change.description} ({change.change_id})\n",
                        content
                    )
                else:
                    # Create new subsection
                    insert_point = match.end(1)
                    new_section = f"{subsection}\n- {change.description} ({change.change_id})\n\n"
                    content = content[:insert_point] + new_section + content[insert_point:]
                
                changelog_path.write_text(content)
                
        except Exception as e:
            logger.error(f"Failed to update CHANGELOG: {e}")
    
    def get_change_history(
        self,
        category: Optional[str] = None,
        approved_only: bool = False,
        limit: int = 50
    ) -> List[ChangeRecord]:
        """
        Get change history.
        
        Args:
            category: Filter by category
            approved_only: Only approved changes
            limit: Max results
            
        Returns:
            List of change records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM changes WHERE 1=1"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if approved_only:
                query += " AND approved = 1"
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            records = []
            for row in rows:
                records.append(ChangeRecord(
                    change_id=row['change_id'],
                    timestamp=row['timestamp'],
                    category=row['category'],
                    files_modified=json.loads(row['files_modified']),
                    description=row['description'],
                    rationale=row['rationale'],
                    before_metrics=json.loads(row['before_metrics']) if row['before_metrics'] else None,
                    after_metrics=json.loads(row['after_metrics']) if row['after_metrics'] else None,
                    git_commit_hash=row['git_commit_hash'],
                    git_branch=row['git_branch'],
                    approved=bool(row['approved']),
                    approved_by=row['approved_by'],
                    reverted=bool(row['reverted']),
                ))
            
            return records
    
    def get_change_stats(self) -> Dict[str, Any]:
        """Get change statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total changes
            total = conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
            
            # By category
            categories = {}
            rows = conn.execute(
                "SELECT category, COUNT(*) FROM changes GROUP BY category"
            ).fetchall()
            for row in rows:
                categories[row[0]] = row[1]
            
            # Approved vs pending
            approved = conn.execute(
                "SELECT COUNT(*) FROM changes WHERE approved = 1"
            ).fetchone()[0]
            
            # With git commits
            committed = conn.execute(
                "SELECT COUNT(*) FROM changes WHERE git_commit_hash IS NOT NULL"
            ).fetchone()[0]
            
            return {
                "total_changes": total,
                "by_category": categories,
                "approved": approved,
                "pending_approval": total - approved,
                "committed": committed,
            }
    
    def approve_change(self, change_id: str, approved_by: str = "human"):
        """Approve a pending change."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE changes 
                SET approved = 1, approved_by = ?
                WHERE change_id = ?
                """,
                (approved_by, change_id)
            )
            conn.commit()
    
    def revert_change(self, change_id: str) -> bool:
        """
        Revert a change by commit hash.
        
        Args:
            change_id: Change to revert
            
        Returns:
            True if reverted successfully
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT git_commit_hash FROM changes WHERE change_id = ?",
                (change_id,)
            ).fetchone()
            
            if not row or not row[0]:
                logger.error(f"No commit hash found for change {change_id}")
                return False
            
            commit_hash = row[0]
            
            try:
                # Revert the commit
                subprocess.run(
                    ["git", "revert", "--no-edit", commit_hash],
                    cwd=self.project_root,
                    check=True,
                    capture_output=True
                )
                
                # Mark as reverted
                conn.execute(
                    "UPDATE changes SET reverted = 1 WHERE change_id = ?",
                    (change_id,)
                )
                conn.commit()
                
                logger.info(f"Reverted change {change_id} (commit {commit_hash[:8]})")
                return True
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Revert failed: {e.stderr}")
                return False
    
    def generate_report(self, days: int = 7) -> str:
        """
        Generate a report of recent changes.
        
        Args:
            days: Number of days to include
            
        Returns:
            Markdown-formatted report
        """
        from datetime import timedelta
        
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM changes WHERE timestamp > ? ORDER BY timestamp DESC",
                (cutoff,)
            ).fetchall()
        
        lines = [
            f"# Demi Change Report (Last {days} days)",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Total Changes:** {len(rows)}",
            "",
            "## Summary",
            "",
        ]
        
        # Category breakdown
        categories = {}
        for row in rows:
            cat = row['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in sorted(categories.items()):
            lines.append(f"- **{cat}:** {count}")
        
        lines.extend(["", "## Changes", ""])
        
        for row in rows:
            lines.append(f"### {row['description']}")
            lines.append(f"- **ID:** `{row['change_id']}`")
            lines.append(f"- **Category:** {row['category']}")
            lines.append(f"- **Time:** {row['timestamp']}")
            lines.append(f"- **Rationale:** {row['rationale']}")
            
            if row['git_commit_hash']:
                lines.append(f"- **Commit:** `{row['git_commit_hash'][:8]}`")
            
            if row['approved']:
                lines.append(f"- **Approved by:** {row['approved_by']}")
            else:
                lines.append("- **Status:** ⏳ Pending approval")
            
            if row['reverted']:
                lines.append("- **Status:** ↩️ Reverted")
            
            lines.append("")
        
        return "\n".join(lines)
