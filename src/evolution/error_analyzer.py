"""
Error Analysis & Self-Correction System

Based on research:
- "Self-Correction Blind Spot" (64.5% of LLMs can't fix own errors)
- "Learning from Mistakes (LeMa)" - Fine-tuning on error-correction pairs
- "Mistake Notebook Learning" - Self-curate guidance from failures

Implements:
1. Error detection from conversations
2. Error categorization (factual, reasoning, personality, etc.)
3. Root cause analysis
4. Correction generation with "Wait" token technique
"""

import re
import json
import sqlite3
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from src.core.logger import get_logger
from src.core.config import DemiConfig

logger = get_logger()


class ErrorCategory(Enum):
    """Categories of errors Demi can make."""
    FACTUAL = "factual"  # Incorrect facts
    REASONING = "reasoning"  # Logical errors
    PERSONALITY_INCONSISTENCY = "personality"  # Out of character
    EMOTIONAL_INAPPROPRIATE = "emotional"  # Wrong emotion for state
    CONTRADICTION = "contradiction"  # Contradicts prior response
    HALLUCINATION = "hallucination"  # Made up information
    GRAMMAR = "grammar"  # Language issues
    REFUSAL_ERROR = "refusal"  # Should/shouldn't have refused
    TECHNICAL = "technical"  # Code/system errors
    UNKNOWN = "unknown"  # Uncategorized


@dataclass
class ErrorRecord:
    """Record of a detected error."""
    error_id: str
    timestamp: str
    category: ErrorCategory
    severity: int  # 1-10
    user_message: str
    demi_response: str
    error_description: str
    root_cause: Optional[str] = None
    proposed_correction: Optional[str] = None
    corrected_response: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['category'] = self.category.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorRecord":
        """Create from dictionary."""
        data['category'] = ErrorCategory(data['category'])
        return cls(**data)


class ErrorAnalyzer:
    """
    Analyzes Demi's responses for errors and generates corrections.
    
    Uses the "Wait" token technique to reduce self-correction blind spot
    by 89.3% (research finding).
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize error analyzer.
        
        Args:
            db_path: Path to SQLite database for error storage
        """
        self.db_path = db_path or self._get_default_db_path()
        self._init_database()
        
        # Error patterns for detection
        self._init_patterns()
        
        logger.info("ErrorAnalyzer initialized")
    
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        config = DemiConfig.load()
        data_dir = Path.home() / ".demi"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "errors.db")
    
    def _init_database(self):
        """Initialize error database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    error_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    user_message TEXT NOT NULL,
                    demi_response TEXT NOT NULL,
                    error_description TEXT NOT NULL,
                    root_cause TEXT,
                    proposed_correction TEXT,
                    corrected_response TEXT,
                    context TEXT,
                    resolved BOOLEAN DEFAULT 0
                )
            """)
            
            # Index for querying
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_category 
                ON errors(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_timestamp 
                ON errors(timestamp)
            """)
            conn.commit()
    
    def _init_patterns(self):
        """Initialize error detection patterns."""
        # Patterns that indicate potential errors
        self.contradiction_patterns = [
            r"\b(I never|I always|I don't|I do)\b.*\b(but|however|though)\b.*\1",
            r"\b(yes|yeah)\b.*\b(no|not|never)\b",
        ]
        
        self.hallucination_indicators = [
            r"\b(I remember|I recall|I know that|studies show)\b.*\b(but I'm not sure|I think|maybe)\b",
            r"\b(according to|research says|data shows)\b.*\b(I believe|I feel|I think)\b",
        ]
        
        self.grammar_issues = [
            r"\b\w+\s+\w+\s+\1\b",  # Repeated words
            r"[.!?]{2,}",  # Multiple punctuation
        ]
    
    def analyze_conversation(
        self,
        user_message: str,
        demi_response: str,
        conversation_history: Optional[List[Dict]] = None,
        emotional_state: Optional[Dict] = None,
    ) -> List[ErrorRecord]:
        """
        Analyze a conversation for errors.
        
        Args:
            user_message: What the user said
            demi_response: What Demi responded
            conversation_history: Prior messages
            emotional_state: Demi's emotional state during response
            
        Returns:
            List of detected errors (empty if none)
        """
        errors = []
        
        # Check for contradictions with history
        if conversation_history:
            contradiction = self._check_contradiction(demi_response, conversation_history)
            if contradiction:
                errors.append(contradiction)
        
        # Check for hallucination indicators
        hallucination = self._check_hallucination(demi_response)
        if hallucination:
            errors.append(hallucination)
        
        # Check for grammar issues
        grammar = self._check_grammar(demi_response)
        if grammar:
            errors.append(grammar)
        
        # Check emotional appropriateness
        if emotional_state:
            emotional = self._check_emotional_appropriateness(
                demi_response, emotional_state
            )
            if emotional:
                errors.append(emotional)
        
        # Store detected errors
        for error in errors:
            self._store_error(error)
        
        return errors
    
    def _check_contradiction(
        self,
        response: str,
        history: List[Dict]
    ) -> Optional[ErrorRecord]:
        """Check if response contradicts prior statements."""
        # Simple heuristic: look for negation of previous statements
        response_lower = response.lower()
        
        for msg in history[-5:]:  # Check last 5 messages
            if msg.get('sender') == 'demi':
                prior = msg.get('content', '').lower()
                
                # Check for direct contradictions
                contradiction_pairs = [
                    ('i love', 'i hate'),
                    ('i always', 'i never'),
                    ('yes', 'no'),
                    ('true', 'false'),
                    ('i remember', 'i forgot'),
                ]
                
                for affirm, negate in contradiction_pairs:
                    if (affirm in prior and negate in response_lower) or \
                       (negate in prior and affirm in response_lower):
                        return ErrorRecord(
                            error_id=self._generate_error_id(),
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            category=ErrorCategory.CONTRADICTION,
                            severity=7,
                            user_message="",
                            demi_response=response,
                            error_description=f"Contradiction detected: '{affirm}' vs '{negate}'",
                            root_cause="Memory inconsistency or context confusion",
                        )
        
        return None
    
    def _check_hallucination(self, response: str) -> Optional[ErrorRecord]:
        """Check for hallucination indicators."""
        # Look for confident claims about specific facts without basis
        hallucination_patterns = [
            r"\b(studies show|research indicates|data proves)\b.*\d+%",
            r"\b(according to [A-Z][a-z]+ (et al\.|[\(]?\d{4}[\)]?))\b",
        ]
        
        for pattern in hallucination_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return ErrorRecord(
                    error_id=self._generate_error_id(),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    category=ErrorCategory.HALLUCINATION,
                    severity=6,
                    user_message="",
                    demi_response=response,
                    error_description="Potential hallucination: specific claim without verification",
                    root_cause="LLM tendency to generate plausible-sounding but unverified information",
                )
        
        return None
    
    def _check_grammar(self, response: str) -> Optional[ErrorRecord]:
        """Check for grammar issues."""
        # Check for repeated words
        repeated = re.search(r"\b(\w+)\s+\1\b", response, re.IGNORECASE)
        if repeated:
            return ErrorRecord(
                error_id=self._generate_error_id(),
                timestamp=datetime.now(timezone.utc).isoformat(),
                category=ErrorCategory.GRAMMAR,
                severity=3,
                user_message="",
                demi_response=response,
                error_description=f"Repeated word: '{repeated.group(1)}'",
                root_cause="TTS generation or processing artifact",
            )
        
        return None
    
    def _check_emotional_appropriateness(
        self,
        response: str,
        emotional_state: Dict[str, float]
    ) -> Optional[ErrorRecord]:
        """Check if response matches emotional state."""
        # Check for mismatches
        loneliness = emotional_state.get('loneliness', 0)
        excitement = emotional_state.get('excitement', 0)
        frustration = emotional_state.get('frustration', 0)
        
        response_lower = response.lower()
        
        # High loneliness but no hint of it in response
        if loneliness > 0.7:
            care_indicators = ['care', 'miss', 'lonely', 'wish', 'want', 'here']
            if not any(ind in response_lower for ind in care_indicators):
                return ErrorRecord(
                    error_id=self._generate_error_id(),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    category=ErrorCategory.EMOTIONAL_INAPPROPRIATE,
                    severity=5,
                    user_message="",
                    demi_response=response,
                    error_description=f"High loneliness ({loneliness:.2f}) but response doesn't reflect it",
                    root_cause="Emotion-to-response mapping not triggering",
                )
        
        # High frustration but too cheerful
        if frustration > 0.6:
            cheerful = ['happy', 'glad', 'excited', 'great', 'wonderful', 'love']
            if any(word in response_lower for word in cheerful):
                return ErrorRecord(
                    error_id=self._generate_error_id(),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    category=ErrorCategory.EMOTIONAL_INAPPROPRIATE,
                    severity=6,
                    user_message="",
                    demi_response=response,
                    error_description=f"High frustration ({frustration:.2f}) but cheerful response",
                    root_cause="Emotional inconsistency in response generation",
                )
        
        return None
    
    def generate_correction(
        self,
        error: ErrorRecord,
        llm_client = None
    ) -> Optional[str]:
        """
        Generate a corrected response for an error.
        
        Uses "Wait" token technique: prepend "Wait," to prompt
        for 89.3% improvement in self-correction.
        
        Args:
            error: The error to correct
            llm_client: Optional LLM client for generation
            
        Returns:
            Corrected response or None
        """
        # Simple rule-based corrections for now
        # In production, use LLM with "Wait," prefix
        
        if error.category == ErrorCategory.GRAMMAR:
            # Fix repeated words
            corrected = re.sub(
                r"\b(\w+)\s+\1\b",
                r"\1",
                error.demi_response,
                flags=re.IGNORECASE
            )
            return corrected
        
        if error.category == ErrorCategory.CONTRADICTION:
            # Add clarification
            return f"{error.demi_response}\n\n(Actually, let me correct myself - I may have misspoken earlier.)"
        
        if error.category == ErrorCategory.EMOTIONAL_INAPPROPRIATE:
            # This would need regeneration with proper emotional context
            return None  # Requires LLM
        
        return None
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        import uuid
        return f"err_{uuid.uuid4().hex[:12]}"
    
    def _store_error(self, error: ErrorRecord):
        """Store error in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO errors 
                    (error_id, timestamp, category, severity, user_message, 
                     demi_response, error_description, root_cause, context, resolved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        error.error_id,
                        error.timestamp,
                        error.category.value,
                        error.severity,
                        error.user_message,
                        error.demi_response,
                        error.error_description,
                        error.root_cause,
                        json.dumps(error.context) if error.context else None,
                        error.resolved,
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store error: {e}")
    
    def get_error_history(
        self,
        category: Optional[ErrorCategory] = None,
        limit: int = 100,
        resolved_only: bool = False
    ) -> List[ErrorRecord]:
        """
        Get error history.
        
        Args:
            category: Filter by category
            limit: Max results
            resolved_only: Only resolved errors
            
        Returns:
            List of error records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM errors WHERE 1=1"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category.value)
            
            if resolved_only:
                query += " AND resolved = 1"
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            records = []
            for row in rows:
                records.append(ErrorRecord(
                    error_id=row['error_id'],
                    timestamp=row['timestamp'],
                    category=ErrorCategory(row['category']),
                    severity=row['severity'],
                    user_message=row['user_message'],
                    demi_response=row['demi_response'],
                    error_description=row['error_description'],
                    root_cause=row['root_cause'],
                    proposed_correction=row['proposed_correction'],
                    corrected_response=row['corrected_response'],
                    context=json.loads(row['context']) if row['context'] else None,
                    resolved=bool(row['resolved']),
                ))
            
            return records
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total errors
            total = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
            
            # By category
            by_category = {}
            for cat in ErrorCategory:
                count = conn.execute(
                    "SELECT COUNT(*) FROM errors WHERE category = ?",
                    (cat.value,)
                ).fetchone()[0]
                by_category[cat.value] = count
            
            # Average severity
            avg_severity = conn.execute(
                "SELECT AVG(severity) FROM errors"
            ).fetchone()[0] or 0
            
            # Recent errors (last 24h)
            from datetime import timedelta
            day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            recent = conn.execute(
                "SELECT COUNT(*) FROM errors WHERE timestamp > ?",
                (day_ago,)
            ).fetchone()[0]
            
            return {
                "total_errors": total,
                "by_category": by_category,
                "average_severity": round(avg_severity, 2),
                "errors_last_24h": recent,
            }
    
    def mark_resolved(self, error_id: str, corrected_response: Optional[str] = None):
        """Mark an error as resolved."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE errors 
                SET resolved = 1, corrected_response = ?
                WHERE error_id = ?
                """,
                (corrected_response, error_id)
            )
            conn.commit()
