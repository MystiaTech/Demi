"""
Pattern Learning Database

Tracks which improvements work best and learns from revision history.
Builds a knowledge base of "what to fix when" patterns.

Used to:
1. Predict which strategies will work for specific issues
2. Build "mistake notebook" for common errors
3. Improve strategy selection over time
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

from src.core.logger import get_logger

logger = get_logger()


@dataclass
class LearnedPattern:
    """A learned pattern of error → fix."""
    pattern_id: str
    timestamp: str
    
    # What to look for
    trigger_issue: str  # e.g., "Missing goddess persona markers"
    trigger_keywords: List[str]  # Keywords that indicate this issue
    
    # What to do
    effective_strategy: str  # Strategy that fixes it
    before_example: str  # Example of bad response
    after_example: str  # Example of fixed response
    
    # Effectiveness tracking
    times_applied: int = 0
    times_successful: int = 0
    avg_improvement: float = 0.0
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.times_applied == 0:
            return 0.0
        return self.times_successful / self.times_applied


@dataclass
class MistakeEntry:
    """Entry in the mistake notebook."""
    entry_id: str
    timestamp: str
    
    # The mistake
    mistake_type: str
    mistake_description: str
    example_response: str
    
    # The correction
    correction_strategy: str
    corrected_response: str
    
    # Learning
    root_cause: str
    prevention_tip: str
    
    # Validation
    times_encountered: int = 1
    successfully_prevented: int = 0


class PatternLearningDB:
    """
    Database for learning improvement patterns.
    
    Implements "Mistake Notebook Learning" research:
    - Self-curate generalizable guidance from failures
    - Build knowledge base over time
    - Apply learned patterns to new situations
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize pattern learning database."""
        self.db_path = db_path or self._get_default_db_path()
        self._init_database()
        
        # Cache frequently used patterns
        self._pattern_cache: Dict[str, LearnedPattern] = {}
        self._mistake_cache: Dict[str, MistakeEntry] = {}
        
        logger.info("PatternLearningDB initialized")
    
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        data_dir = Path.home() / ".demi"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "patterns.db")
    
    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Learned patterns table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    trigger_issue TEXT NOT NULL,
                    trigger_keywords TEXT NOT NULL,
                    effective_strategy TEXT NOT NULL,
                    before_example TEXT,
                    after_example TEXT,
                    times_applied INTEGER DEFAULT 0,
                    times_successful INTEGER DEFAULT 0,
                    avg_improvement REAL DEFAULT 0
                )
            """)
            
            # Mistake notebook table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mistakes (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    mistake_type TEXT NOT NULL,
                    mistake_description TEXT NOT NULL,
                    example_response TEXT,
                    correction_strategy TEXT NOT NULL,
                    corrected_response TEXT,
                    root_cause TEXT,
                    prevention_tip TEXT,
                    times_encountered INTEGER DEFAULT 1,
                    successfully_prevented INTEGER DEFAULT 0
                )
            """)
            
            # Pattern application log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_applications (
                    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    pattern_id TEXT,
                    response_context TEXT,
                    was_successful BOOLEAN,
                    improvement_score REAL
                )
            """)
            
            conn.commit()
    
    def learn_from_revision(
        self,
        original_issue: str,
        strategy_used: str,
        was_successful: bool,
        improvement_score: float,
        before_text: str,
        after_text: str,
    ) -> Optional[str]:
        """
        Learn from a revision attempt.
        
        Args:
            original_issue: What was wrong with original
            strategy_used: Which strategy fixed it
            was_successful: Did the fix work
            improvement_score: How much it improved
            before_text: Original response
            after_text: Fixed response
            
        Returns:
            Pattern ID if new pattern created
        """
        import uuid
        
        # Extract keywords from issue
        keywords = self._extract_keywords(original_issue)
        
        # Check if similar pattern exists
        existing = self._find_similar_pattern(original_issue, keywords)
        
        if existing:
            # Update existing pattern
            self._update_pattern_stats(
                existing.pattern_id,
                was_successful,
                improvement_score
            )
            return existing.pattern_id
        
        elif was_successful and improvement_score > 0.5:
            # Create new pattern for successful fix
            pattern = LearnedPattern(
                pattern_id=f"pat_{uuid.uuid4().hex[:12]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                trigger_issue=original_issue,
                trigger_keywords=keywords,
                effective_strategy=strategy_used,
                before_example=before_text[:500],
                after_example=after_text[:500],
                times_applied=1,
                times_successful=1 if was_successful else 0,
                avg_improvement=improvement_score,
            )
            
            self._store_pattern(pattern)
            self._pattern_cache[pattern.pattern_id] = pattern
            
            logger.info(
                f"New pattern learned: {pattern.pattern_id}",
                issue=original_issue[:50],
                strategy=strategy_used,
            )
            
            return pattern.pattern_id
        
        return None
    
    def add_mistake(
        self,
        mistake_type: str,
        mistake_description: str,
        example_response: str,
        correction_strategy: str,
        corrected_response: str,
        root_cause: str,
        prevention_tip: str,
    ) -> str:
        """
        Add entry to mistake notebook.
        
        Args:
            mistake_type: Category of mistake
            mistake_description: What went wrong
            example_response: Bad example
            correction_strategy: How it was fixed
            corrected_response: Good example
            root_cause: Why it happened
            prevention_tip: How to prevent
            
        Returns:
            Entry ID
        """
        import uuid
        
        # Check if similar mistake exists
        existing = self._find_similar_mistake(mistake_type, mistake_description)
        
        if existing:
            # Update count
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE mistakes 
                    SET times_encountered = times_encountered + 1
                    WHERE entry_id = ?
                    """,
                    (existing.entry_id,)
                )
                conn.commit()
            
            existing.times_encountered += 1
            return existing.entry_id
        
        # Create new entry
        entry = MistakeEntry(
            entry_id=f"mist_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            mistake_type=mistake_type,
            mistake_description=mistake_description,
            example_response=example_response[:500],
            correction_strategy=correction_strategy,
            corrected_response=corrected_response[:500],
            root_cause=root_cause,
            prevention_tip=prevention_tip,
        )
        
        self._store_mistake(entry)
        self._mistake_cache[entry.entry_id] = entry
        
        logger.info(
            f"New mistake entry: {entry.entry_id}",
            type=mistake_type,
            description=mistake_description[:50],
        )
        
        return entry.entry_id
    
    def find_patterns_for_issue(
        self,
        issue_description: str,
        top_k: int = 3
    ) -> List[LearnedPattern]:
        """
        Find patterns that might fix a given issue.
        
        Args:
            issue_description: Description of the issue
            top_k: Number of patterns to return
            
        Returns:
            List of relevant patterns, sorted by effectiveness
        """
        keywords = self._extract_keywords(issue_description)
        
        # Score patterns by keyword overlap
        scored_patterns = []
        
        for pattern in self._get_all_patterns():
            # Keyword overlap score
            overlap = len(set(keywords) & set(pattern.trigger_keywords))
            
            # Success rate weight
            success_weight = pattern.success_rate()
            
            # Recency weight (prefer newer patterns)
            try:
                pattern_time = datetime.fromisoformat(pattern.timestamp)
                days_old = (datetime.now(timezone.utc) - pattern_time).days
                recency_weight = max(0.5, 1.0 - (days_old / 30))  # Decay over 30 days
            except:
                recency_weight = 0.5
            
            # Combined score
            score = (overlap * 2) + (success_weight * 3) + recency_weight
            
            if overlap > 0:  # Must have some keyword overlap
                scored_patterns.append((score, pattern))
        
        # Sort by score and return top_k
        scored_patterns.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored_patterns[:top_k]]
    
    def find_mistake_prevention(
        self,
        response_text: str
    ) -> List[MistakeEntry]:
        """
        Find mistake prevention tips for a response.
        
        Args:
            response_text: Response to check
            
        Returns:
            List of relevant prevention tips
        """
        response_lower = response_text.lower()
        relevant = []
        
        for mistake in self._get_all_mistakes():
            # Check if this mistake pattern appears in response
            mistake_keywords = self._extract_keywords(mistake.mistake_description)
            
            # Or if the example is similar
            example_keywords = self._extract_keywords(mistake.example_response)
            
            all_keywords = set(mistake_keywords + example_keywords)
            matches = sum(1 for kw in all_keywords if kw in response_lower)
            
            if matches >= 2:  # At least 2 keyword matches
                relevant.append((matches, mistake))
        
        # Sort by relevance and return
        relevant.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in relevant[:5]]
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of what has been learned."""
        with sqlite3.connect(self.db_path) as conn:
            # Pattern stats
            pattern_count = conn.execute(
                "SELECT COUNT(*) FROM patterns"
            ).fetchone()[0]
            
            avg_success_rate = conn.execute(
                """
                SELECT AVG(
                    CAST(times_successful AS FLOAT) / NULLIF(times_applied, 0)
                )
                FROM patterns
                """
            ).fetchone()[0] or 0
            
            # Mistake stats
            mistake_count = conn.execute(
                "SELECT COUNT(*) FROM mistakes"
            ).fetchone()[0]
            
            # Top strategies
            top_strategies = conn.execute(
                """
                SELECT effective_strategy, 
                       AVG(avg_improvement) as avg_imp,
                       SUM(times_successful) as total_success
                FROM patterns
                GROUP BY effective_strategy
                ORDER BY avg_imp DESC
                LIMIT 5
                """
            ).fetchall()
            
            # Recent learning (last 7 days)
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            recent_patterns = conn.execute(
                "SELECT COUNT(*) FROM patterns WHERE timestamp > ?",
                (week_ago,)
            ).fetchone()[0]
            
            recent_mistakes = conn.execute(
                "SELECT COUNT(*) FROM mistakes WHERE timestamp > ?",
                (week_ago,)
            ).fetchone()[0]
            
            return {
                'total_patterns_learned': pattern_count,
                'average_pattern_success_rate': f"{100*avg_success_rate:.1f}%",
                'total_mistake_entries': mistake_count,
                'top_strategies': [
                    {'strategy': s[0], 'avg_improvement': round(s[1], 2), 'successes': s[2]}
                    for s in top_strategies
                ],
                'recent_learning': {
                    'patterns_last_7d': recent_patterns,
                    'mistakes_last_7d': recent_mistakes,
                },
            }
    
    def export_mistake_notebook(self) -> str:
        """Export mistake notebook as formatted text."""
        mistakes = self._get_all_mistakes()
        
        lines = [
            "# Demi's Mistake Notebook",
            "",
            "Learned from errors to prevent future mistakes.",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Total Entries: {len(mistakes)}",
            "",
            "---",
            "",
        ]
        
        # Group by type
        by_type = defaultdict(list)
        for m in mistakes:
            by_type[m.mistake_type].append(m)
        
        for mistake_type, entries in sorted(by_type.items()):
            lines.append(f"## {mistake_type.upper()}")
            lines.append("")
            
            for entry in sorted(entries, key=lambda x: x.times_encountered, reverse=True):
                lines.append(f"### {entry.mistake_description}")
                lines.append(f"**Encountered:** {entry.times_encountered} times")
                lines.append(f"**Root Cause:** {entry.root_cause}")
                lines.append(f"**Prevention:** {entry.prevention_tip}")
                lines.append(f"**Fix Strategy:** {entry.correction_strategy}")
                
                if entry.successfully_prevented > 0:
                    lines.append(f"**Successfully Prevented:** {entry.successfully_prevented} times ✓")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Simple keyword extraction
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                      'could', 'should', 'may', 'might', 'can', 'this', 'that',
                      'these', 'those', 'and', 'or', 'but', 'in', 'on', 'at',
                      'to', 'for', 'of', 'with', 'by', 'from', 'as', 'it', 'its'}
        
        words = text.lower().split()
        keywords = [w.strip('.,!?;:') for w in words 
                   if len(w) > 3 and w.lower() not in stop_words]
        
        return keywords[:10]  # Limit to top 10
    
    def _find_similar_pattern(
        self,
        issue: str,
        keywords: List[str]
    ) -> Optional[LearnedPattern]:
        """Find existing pattern similar to issue."""
        for pattern in self._get_all_patterns():
            # Check issue similarity
            if issue.lower() == pattern.trigger_issue.lower():
                return pattern
            
            # Check keyword overlap
            overlap = len(set(keywords) & set(pattern.trigger_keywords))
            if overlap >= 3:  # Significant overlap
                return pattern
        
        return None
    
    def _find_similar_mistake(
        self,
        mistake_type: str,
        description: str
    ) -> Optional[MistakeEntry]:
        """Find existing mistake entry similar to new one."""
        for entry in self._get_all_mistakes():
            if (entry.mistake_type == mistake_type and
                entry.mistake_description.lower() == description.lower()):
                return entry
        
        return None
    
    def _store_pattern(self, pattern: LearnedPattern):
        """Store pattern in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO patterns 
                (pattern_id, timestamp, trigger_issue, trigger_keywords,
                 effective_strategy, before_example, after_example,
                 times_applied, times_successful, avg_improvement)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pattern.pattern_id,
                    pattern.timestamp,
                    pattern.trigger_issue,
                    json.dumps(pattern.trigger_keywords),
                    pattern.effective_strategy,
                    pattern.before_example,
                    pattern.after_example,
                    pattern.times_applied,
                    pattern.times_successful,
                    pattern.avg_improvement,
                )
            )
            conn.commit()
    
    def _store_mistake(self, entry: MistakeEntry):
        """Store mistake entry in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO mistakes 
                (entry_id, timestamp, mistake_type, mistake_description,
                 example_response, correction_strategy, corrected_response,
                 root_cause, prevention_tip, times_encountered, successfully_prevented)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.entry_id,
                    entry.timestamp,
                    entry.mistake_type,
                    entry.mistake_description,
                    entry.example_response,
                    entry.correction_strategy,
                    entry.corrected_response,
                    entry.root_cause,
                    entry.prevention_tip,
                    entry.times_encountered,
                    entry.successfully_prevented,
                )
            )
            conn.commit()
    
    def _update_pattern_stats(
        self,
        pattern_id: str,
        was_successful: bool,
        improvement_score: float
    ):
        """Update pattern statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE patterns 
                SET times_applied = times_applied + 1,
                    times_successful = times_successful + ?,
                    avg_improvement = (avg_improvement * times_applied + ?) / (times_applied + 1)
                WHERE pattern_id = ?
                """,
                (1 if was_successful else 0, improvement_score, pattern_id)
            )
            conn.commit()
    
    def _get_all_patterns(self) -> List[LearnedPattern]:
        """Get all patterns from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM patterns").fetchall()
            
            patterns = []
            for row in rows:
                patterns.append(LearnedPattern(
                    pattern_id=row['pattern_id'],
                    timestamp=row['timestamp'],
                    trigger_issue=row['trigger_issue'],
                    trigger_keywords=json.loads(row['trigger_keywords']),
                    effective_strategy=row['effective_strategy'],
                    before_example=row['before_example'],
                    after_example=row['after_example'],
                    times_applied=row['times_applied'],
                    times_successful=row['times_successful'],
                    avg_improvement=row['avg_improvement'],
                ))
            
            return patterns
    
    def _get_all_mistakes(self) -> List[MistakeEntry]:
        """Get all mistake entries from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM mistakes").fetchall()
            
            mistakes = []
            for row in rows:
                mistakes.append(MistakeEntry(
                    entry_id=row['entry_id'],
                    timestamp=row['timestamp'],
                    mistake_type=row['mistake_type'],
                    mistake_description=row['mistake_description'],
                    example_response=row['example_response'],
                    correction_strategy=row['correction_strategy'],
                    corrected_response=row['corrected_response'],
                    root_cause=row['root_cause'],
                    prevention_tip=row['prevention_tip'],
                    times_encountered=row['times_encountered'],
                    successfully_prevented=row['successfully_prevented'],
                ))
            
            return mistakes
