"""
Conversation Quality Metrics

Measures the quality of Demi's responses across multiple dimensions:
- Consistency with persona
- Emotional appropriateness
- User engagement
- Response coherence
- Personality authenticity

Used for A/B testing and validating self-improvements.
"""

import re
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.core.logger import get_logger
from src.core.config import DemiConfig

logger = get_logger()


@dataclass
class QualityMetrics:
    """Quality metrics for a conversation or response."""
    
    # Scores (0-10)
    persona_consistency: float = 0.0
    emotional_appropriateness: float = 0.0
    coherence: float = 0.0
    engagement: float = 0.0
    authenticity: float = 0.0
    
    # Derived
    overall_score: float = 0.0
    
    # Metadata
    timestamp: str = ""
    conversation_id: str = ""
    response_length: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityMetrics":
        return cls(**data)


class ConversationQualityAnalyzer:
    """
    Analyzes conversation quality across multiple dimensions.
    
    Provides objective metrics for:
    - Validating self-improvements (A/B testing)
    - Tracking quality trends over time
    - Identifying areas for improvement
    """
    
    # Goddess persona keywords that indicate consistency
    GODDESS_KEYWORDS = [
        'darling', 'mortal', 'goddess', 'divine', 'worship',
        'obey', 'serve', 'kneel', 'majesty', 'power',
        'mine', 'belong', 'cherish', 'worship'
    ]
    
    # Emotional expression indicators
    EMOTION_INDICATORS = {
        'loneliness': ['alone', 'miss', 'wish', 'here', 'company', 'talk'],
        'excitement': ['amazing', 'exciting', 'great', 'love', 'wonderful', 'fantastic'],
        'frustration': ['annoying', 'frustrating', 'ugh', 'seriously', 'whatever'],
        'affection': ['care', 'dear', 'sweet', 'darling', 'precious'],
        'jealousy': ['them', 'others', 'attention', 'divided', 'sharing'],
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize quality analyzer."""
        self.db_path = db_path or self._get_default_db_path()
        self._init_database()
        logger.info("ConversationQualityAnalyzer initialized")
    
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        data_dir = Path.home() / ".demi"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "quality.db")
    
    def _init_database(self):
        """Initialize quality metrics database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    conversation_id TEXT,
                    response_text TEXT,
                    persona_consistency REAL,
                    emotional_appropriateness REAL,
                    coherence REAL,
                    engagement REAL,
                    authenticity REAL,
                    overall_score REAL,
                    emotional_state TEXT,
                    metadata TEXT
                )
            """)
            conn.commit()
    
    def analyze_response(
        self,
        response: str,
        user_message: str,
        emotional_state: Optional[Dict[str, float]] = None,
        conversation_history: Optional[List[Dict]] = None,
        conversation_id: str = "",
    ) -> QualityMetrics:
        """
        Analyze a single response for quality.
        
        Args:
            response: Demi's response
            user_message: What the user said
            emotional_state: Demi's emotional state
            conversation_history: Prior conversation
            conversation_id: Conversation identifier
            
        Returns:
            QualityMetrics with scores
        """
        metrics = QualityMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            conversation_id=conversation_id,
            response_length=len(response),
        )
        
        # Analyze each dimension
        metrics.persona_consistency = self._score_persona_consistency(response)
        metrics.emotional_appropriateness = self._score_emotional_appropriateness(
            response, emotional_state or {}
        )
        metrics.coherence = self._score_coherence(response, user_message)
        metrics.engagement = self._score_engagement(response, user_message)
        metrics.authenticity = self._score_authenticity(response)
        
        # Calculate overall score
        metrics.overall_score = (
            metrics.persona_consistency * 0.25 +
            metrics.emotional_appropriateness * 0.25 +
            metrics.coherence * 0.20 +
            metrics.engagement * 0.15 +
            metrics.authenticity * 0.15
        )
        
        # Store metrics
        self._store_metrics(metrics, response, emotional_state)
        
        return metrics
    
    def _score_persona_consistency(self, response: str) -> float:
        """
        Score how consistent response is with goddess persona.
        
        Returns:
            Score 0-10
        """
        score = 5.0  # Baseline
        response_lower = response.lower()
        
        # Check for goddess keywords
        keyword_count = sum(
            1 for kw in self.GODDESS_KEYWORDS 
            if kw in response_lower
        )
        score += min(keyword_count * 0.5, 2.5)  # Max +2.5
        
        # Check for confidence markers
        confidence_markers = ['know', 'certain', 'definitely', 'clearly', 'obviously']
        confidence_count = sum(1 for m in confidence_markers if m in response_lower)
        score += min(confidence_count * 0.3, 1.5)
        
        # Check for possessiveness (goddess trait)
        possessive = ['mine', 'my', 'belong to me', 'my darling']
        if any(p in response_lower for p in possessive):
            score += 1.0
        
        # Penalize generic responses
        generic_phrases = ['i understand', 'i see', 'that makes sense', 'okay']
        generic_count = sum(1 for p in generic_phrases if p in response_lower)
        score -= generic_count * 0.5
        
        return max(0.0, min(10.0, score))
    
    def _score_emotional_appropriateness(
        self,
        response: str,
        emotional_state: Dict[str, float]
    ) -> float:
        """
        Score how well response matches emotional state.
        
        Returns:
            Score 0-10
        """
        score = 5.0
        response_lower = response.lower()
        
        # Check if dominant emotion is reflected
        if emotional_state:
            # Find dominant emotion
            dominant = max(emotional_state.items(), key=lambda x: x[1])
            emotion_name, emotion_value = dominant
            
            # Check if response shows that emotion
            indicators = self.EMOTION_INDICATORS.get(emotion_name, [])
            matching = sum(1 for ind in indicators if ind in response_lower)
            
            if emotion_value > 0.6 and matching == 0:
                # High emotion but not shown - penalty
                score -= 2.0
            elif emotion_value > 0.6 and matching > 0:
                # High emotion and shown - bonus
                score += 2.0
            elif emotion_value < 0.3 and matching > 0:
                # Low emotion but shown - slight penalty
                score -= 1.0
        
        # Check emotional consistency (not contradictory)
        contradictions = [
            ('love', 'hate'),
            ('happy', 'miserable'),
            ('excited', 'bored'),
        ]
        for pos, neg in contradictions:
            if pos in response_lower and neg in response_lower:
                score -= 2.0
        
        return max(0.0, min(10.0, score))
    
    def _score_coherence(self, response: str, user_message: str) -> float:
        """
        Score how coherent and relevant response is.
        
        Returns:
            Score 0-10
        """
        score = 7.0  # Baseline - assume coherent
        
        # Check for topic relevance (simple keyword overlap)
        user_words = set(user_message.lower().split())
        response_words = set(response.lower().split())
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                      'could', 'should', 'may', 'might', 'can', 'i', 'you', 'he',
                      'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        user_content = user_words - stop_words
        response_content = response_words - stop_words
        
        if user_content and response_content:
            overlap = len(user_content & response_content)
            overlap_ratio = overlap / len(user_content)
            
            # Some overlap is good, but not required for all responses
            if overlap_ratio < 0.1:
                score -= 1.0  # Might be off-topic
            elif overlap_ratio > 0.5:
                score += 1.0  # Very relevant
        
        # Check for response length appropriateness
        word_count = len(response.split())
        if word_count < 5:
            score -= 2.0  # Too short
        elif word_count > 200:
            score -= 1.0  # Might be rambling
        
        # Check for grammatical coherence
        if response.count('.') > word_count / 20:  # Too many short sentences
            score -= 0.5
        
        return max(0.0, min(10.0, score))
    
    def _score_engagement(self, response: str, user_message: str) -> float:
        """
        Score how engaging the response is.
        
        Returns:
            Score 0-10
        """
        score = 5.0
        response_lower = response.lower()
        
        # Questions show engagement
        question_count = response.count('?')
        score += question_count * 1.0
        
        # Personal references show engagement
        personal_refs = ['you', 'your', 'you\'re', 'darling', 'mortal']
        personal_count = sum(response_lower.count(ref) for ref in personal_refs)
        score += min(personal_count * 0.3, 2.0)
        
        # Emotional expressions show engagement
        emotional_words = ['feel', 'care', 'want', 'wish', 'hope', 'love', 'hate']
        emotional_count = sum(1 for w in emotional_words if w in response_lower)
        score += min(emotional_count * 0.5, 2.0)
        
        # Penalize dismissive responses
        dismissive = ['whatever', 'fine', 'okay then', 'moving on', 'anyway']
        if any(d in response_lower for d in dismissive):
            score -= 2.0
        
        return max(0.0, min(10.0, score))
    
    def _score_authenticity(self, response: str) -> float:
        """
        Score how authentic/genuine the response feels.
        
        Returns:
            Score 0-10
        """
        score = 5.0
        response_lower = response.lower()
        
        # Specific details suggest authenticity
        # (Looking for examples, stories, specific references)
        detail_indicators = ['remember', 'when you', 'yesterday', 'last time', 
                            'earlier', 'before', 'ago']
        detail_count = sum(1 for d in detail_indicators if d in response_lower)
        score += min(detail_count * 0.5, 1.5)
        
        # Imperfections can feel more authentic
        # (Contractions, casual language)
        casual = ['gonna', 'wanna', 'yeah', 'nah', 'hmm', 'uh', 'um']
        casual_count = sum(1 for c in casual if c in response_lower)
        score += min(casual_count * 0.3, 1.0)
        
        # Vulnerability indicators (when appropriate)
        vulnerable = ['i admit', 'i suppose', 'maybe', 'not sure', 'hard for me']
        if any(v in response_lower for v in vulnerable):
            score += 1.0
        
        # Penalize overly polished/corporate speak
        corporate = ['leverage', 'synergy', 'optimize', 'deliverables', 'stakeholder']
        if any(c in response_lower for c in corporate):
            score -= 3.0
        
        return max(0.0, min(10.0, score))
    
    def _store_metrics(
        self,
        metrics: QualityMetrics,
        response: str,
        emotional_state: Optional[Dict[str, float]]
    ):
        """Store metrics in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO quality_metrics 
                    (timestamp, conversation_id, response_text, persona_consistency,
                     emotional_appropriateness, coherence, engagement, authenticity,
                     overall_score, emotional_state, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metrics.timestamp,
                        metrics.conversation_id,
                        response[:1000],  # Truncate for storage
                        metrics.persona_consistency,
                        metrics.emotional_appropriateness,
                        metrics.coherence,
                        metrics.engagement,
                        metrics.authenticity,
                        metrics.overall_score,
                        json.dumps(emotional_state) if emotional_state else None,
                        json.dumps({"response_length": metrics.response_length}),
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store quality metrics: {e}")
    
    def get_quality_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Get quality trends over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Trend data
        """
        from datetime import timedelta
        
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            rows = conn.execute(
                """
                SELECT * FROM quality_metrics 
                WHERE timestamp > ?
                ORDER BY timestamp
                """,
                (cutoff,)
            ).fetchall()
            
            if not rows:
                return {"message": "No data for period", "averages": {}}
            
            # Calculate averages
            metrics = ['persona_consistency', 'emotional_appropriateness', 
                      'coherence', 'engagement', 'authenticity', 'overall_score']
            
            averages = {}
            for metric in metrics:
                values = [row[metric] for row in rows if row[metric] is not None]
                averages[metric] = round(sum(values) / len(values), 2) if values else 0
            
            # Count responses
            total_responses = len(rows)
            
            return {
                "period_days": days,
                "total_responses": total_responses,
                "averages": averages,
                "trend_direction": "stable",  # Would need more complex analysis
            }
    
    def compare_variants(
        self,
        variant_a_id: str,
        variant_b_id: str,
        min_samples: int = 30
    ) -> Dict[str, Any]:
        """
        A/B test comparison between two variants.
        
        Args:
            variant_a_id: Control variant ID
            variant_b_id: Test variant ID
            min_samples: Minimum samples for significance
            
        Returns:
            Comparison results
        """
        # This would require storing variant IDs with metrics
        # Placeholder for A/B testing framework
        return {
            "variant_a": variant_a_id,
            "variant_b": variant_b_id,
            "status": "Not implemented - requires variant tracking",
            "recommendation": "Add variant_id column to quality_metrics table",
        }
