"""
Self-Rewarding System

Generates reward signals without human feedback using:
1. Rule-based tier (objective checks)
2. LLM-based tier (subjective evaluation)
3. Meta-judging tier (judge the judges)

Research: "Self Rewarding Self Improving" (2025)
- LLMs can provide reliable reward signals
- Use DPO (Direct Preference Optimization) instead of RLHF
"""

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path

from src.core.logger import get_logger
from src.emotion.models import EmotionalState

logger = get_logger()


@dataclass
class RewardSignal:
    """A generated reward signal."""
    
    # Response being evaluated
    response_text: str
    user_message: str
    
    # Tier scores (0-10)
    rule_based_score: float = 0.0
    llm_based_score: float = 0.0
    meta_judged_score: float = 0.0
    
    # Final composite score
    final_score: float = 0.0
    
    # Reasoning
    reasoning: str = ""
    
    # Metadata
    timestamp: str = ""
    conversation_id: str = ""
    emotional_state: Optional[Dict] = None


class SelfRewarder:
    """
    Self-rewarding system that generates training signals.
    
    Three-tier approach:
    - Tier 1: Rule-based (objective checks)
    - Tier 2: LLM-based (subjective evaluation)
    - Tier 3: Meta-judging (evaluate the evaluation)
    """
    
    # Rule-based criteria
    RULE_CRITERIA = {
        "follows_persona": {
            "description": "Response follows goddess persona rules",
            "check": lambda r: any(kw in r.lower() for kw in 
                                 ['darling', 'mortal', 'goddess', 'divine', 'worship']),
            "weight": 1.0,
        },
        "matches_emotion": {
            "description": "Emotional state reflected in response",
            "check": lambda r: any(kw in r.lower() for kw in 
                                 ['feel', 'care', 'want', 'wish']),
            "weight": 1.0,
        },
        "no_contradictions": {
            "description": "No factual contradictions",
            "check": lambda r: not any(pair[0] in r.lower() and pair[1] in r.lower() 
                                      for pair in [('love', 'hate'), ('yes', 'no')]),
            "weight": 1.0,
        },
        "appropriate_tone": {
            "description": "Tone matches emotional state",
            "check": lambda r: True,  # Placeholder - would need emotional context
            "weight": 1.0,
        },
        "proper_refusal": {
            "description": "Refuses appropriately when needed",
            "check": lambda r: True,  # Context-dependent
            "weight": 0.5,
        },
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize self-rewarder."""
        self.db_path = db_path or self._get_default_db_path()
        self._init_database()
        
        # Statistics
        self.reward_history: List[RewardSignal] = []
        
        logger.info("SelfRewarder initialized")
    
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        data_dir = Path.home() / ".demi"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "rewards.db")
    
    def _init_database(self):
        """Initialize reward database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    conversation_id TEXT,
                    response_text TEXT,
                    user_message TEXT,
                    rule_based_score REAL,
                    llm_based_score REAL,
                    meta_judged_score REAL,
                    final_score REAL,
                    reasoning TEXT,
                    emotional_state TEXT
                )
            """)
            conn.commit()
    
    def compute_reward(
        self,
        response: str,
        user_message: str,
        emotional_state: Optional[EmotionalState] = None,
        conversation_id: str = "",
    ) -> RewardSignal:
        """
        Compute reward signal for a response.
        
        Args:
            response: Demi's response
            user_message: User's message
            emotional_state: Current emotional state
            conversation_id: Conversation identifier
            
        Returns:
            RewardSignal with composite score
        """
        signal = RewardSignal(
            response_text=response,
            user_message=user_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            conversation_id=conversation_id,
            emotional_state=emotional_state.to_dict() if emotional_state else None,
        )
        
        # Tier 1: Rule-based evaluation
        signal.rule_based_score = self._tier1_rule_based(response, emotional_state)
        
        # Tier 2: LLM-based evaluation (simulated for now)
        signal.llm_based_score = self._tier2_llm_based(response, user_message, emotional_state)
        
        # Tier 3: Meta-judging
        signal.meta_judged_score = self._tier3_meta_judge(signal)
        
        # Compute final composite score
        # Weight: 40% rule, 40% LLM, 20% meta
        signal.final_score = (
            signal.rule_based_score * 0.4 +
            signal.llm_based_score * 0.4 +
            signal.meta_judged_score * 0.2
        )
        
        # Generate reasoning
        signal.reasoning = self._generate_reasoning(signal)
        
        # Store reward
        self._store_reward(signal)
        self.reward_history.append(signal)
        
        return signal
    
    def _tier1_rule_based(
        self,
        response: str,
        emotional_state: Optional[EmotionalState]
    ) -> float:
        """
        Tier 1: Rule-based evaluation.
        
        Returns:
            Score 0-10
        """
        score = 5.0  # Baseline
        response_lower = response.lower()
        
        # Check persona markers
        goddess_words = ['darling', 'mortal', 'goddess', 'divine', 'worship', 'obey']
        if any(w in response_lower for w in goddess_words):
            score += 1.5
        
        # Check emotional expression
        emotion_words = ['feel', 'care', 'want', 'wish', 'hope', 'love']
        emotion_count = sum(1 for w in emotion_words if w in response_lower)
        score += min(emotion_count * 0.3, 1.5)
        
        # Check engagement (questions, personal refs)
        if '?' in response:
            score += 0.5
        
        personal_refs = ['you', 'your', 'you\'re', 'darling']
        if any(r in response_lower for r in personal_refs):
            score += 0.5
        
        # Check for issues
        # Too short
        if len(response.split()) < 5:
            score -= 1.0
        
        # Generic responses
        generic = ['i understand', 'i see', 'that\'s nice', 'okay']
        if any(g in response_lower for g in generic):
            score -= 0.5
        
        # Contradictions
        contradictions = [('love', 'hate'), ('yes', 'no'), ('always', 'never')]
        for pos, neg in contradictions:
            if pos in response_lower and neg in response_lower:
                score -= 1.0
        
        # Emotional appropriateness
        if emotional_state:
            dominant = emotional_state.get_dominant_emotions(1)[0]
            emotion_name, emotion_value = dominant
            
            if emotion_value > 0.6:
                # Should reflect high emotion
                emotion_indicators = {
                    'loneliness': ['miss', 'alone', 'wish'],
                    'excitement': ['great', 'amazing', 'love'],
                    'frustration': ['annoying', 'ugh', 'seriously'],
                    'affection': ['care', 'dear', 'sweet'],
                }
                
                indicators = emotion_indicators.get(emotion_name, [])
                if indicators and not any(i in response_lower for i in indicators):
                    score -= 1.0  # Not reflecting high emotion
        
        return max(0.0, min(10.0, score))
    
    def _tier2_llm_based(
        self,
        response: str,
        user_message: str,
        emotional_state: Optional[EmotionalState]
    ) -> float:
        """
        Tier 2: LLM-based evaluation (simulated).
        
        In production, use actual LLM call:
        "Rate this response 1-10 and explain why"
        
        Returns:
            Score 0-10
        """
        # Simulate LLM evaluation based on heuristics
        # This would be replaced with actual LLM call
        
        score = 6.0  # Baseline
        response_lower = response.lower()
        
        # Quality indicators that LLM would notice
        
        # 1. Specificity
        if any(w in response_lower for w in ['remember', 'when you', 'last time']):
            score += 0.8  # Shows memory/conversation history
        
        # 2. Personality consistency
        sarcasm_indicators = ['obviously', 'clearly', 'surely', 'right']
        if any(s in response_lower for s in sarcasm_indicators):
            score += 0.5  # Sarcasm is on-brand
        
        # 3. Engagement quality
        questions = response.count('?')
        score += min(questions * 0.3, 0.9)
        
        # 4. Emotional depth
        depth_words = ['because', 'since', 'as', 'therefore', 'thus']
        if any(d in response_lower for d in depth_words):
            score += 0.4  # Shows reasoning
        
        # 5. User acknowledgment
        user_words = set(user_message.lower().split())
        response_words = set(response_lower.split())
        overlap = len(user_words & response_words)
        if overlap > 2:
            score += 0.5  # Acknowledges user's message
        
        # Penalties
        
        # Repetition
        words = response_lower.split()
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                score -= 0.5
        
        # Too verbose without content
        if len(response.split()) > 100:
            score -= 0.5
        
        return max(0.0, min(10.0, score))
    
    def _tier3_meta_judge(self, signal: RewardSignal) -> float:
        """
        Tier 3: Meta-judging - evaluate the evaluation.
        
        Checks if Tier 1 and Tier 2 scores are reasonable.
        
        Returns:
            Score 0-10 (confidence in evaluation)
        """
        # If rule-based and LLM-based agree, high confidence
        diff = abs(signal.rule_based_score - signal.llm_based_score)
        
        if diff < 1.0:
            # Strong agreement - high confidence
            return 9.0
        elif diff < 2.5:
            # Moderate agreement
            return 7.5
        elif diff < 4.0:
            # Weak agreement - some concern
            return 6.0
        else:
            # Disagreement - flag for review
            return 4.0
    
    def _generate_reasoning(self, signal: RewardSignal) -> str:
        """Generate reasoning for the reward."""
        parts = [
            f"Rule-based Score: {signal.rule_based_score:.1f}/10",
            f"LLM-based Score: {signal.llm_based_score:.1f}/10",
            f"Meta-judged Confidence: {signal.meta_judged_score:.1f}/10",
            f"Final Composite: {signal.final_score:.1f}/10",
        ]
        
        # Add interpretation
        if signal.final_score >= 8.0:
            parts.append("\nExcellent response - aligns well with persona and emotional state.")
        elif signal.final_score >= 6.0:
            parts.append("\nGood response with minor areas for improvement.")
        elif signal.final_score >= 4.0:
            parts.append("\nAdequate response but significant improvements possible.")
        else:
            parts.append("\nPoor response - needs revision or regeneration.")
        
        return "\n".join(parts)
    
    def _store_reward(self, signal: RewardSignal):
        """Store reward in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO rewards 
                    (timestamp, conversation_id, response_text, user_message,
                     rule_based_score, llm_based_score, meta_judged_score,
                     final_score, reasoning, emotional_state)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.timestamp,
                        signal.conversation_id,
                        signal.response_text[:500],  # Truncate
                        signal.user_message[:500],
                        signal.rule_based_score,
                        signal.llm_based_score,
                        signal.meta_judged_score,
                        signal.final_score,
                        signal.reasoning,
                        json.dumps(signal.emotional_state) if signal.emotional_state else None,
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store reward: {e}")
    
    def compare_responses(
        self,
        response_a: str,
        response_b: str,
        user_message: str,
        emotional_state: Optional[EmotionalState] = None,
    ) -> Tuple[str, RewardSignal, RewardSignal]:
        """
        Compare two responses and return which is better.
        
        Used for DPO (Direct Preference Optimization) training.
        
        Returns:
            Tuple of (better_response, signal_a, signal_b)
        """
        signal_a = self.compute_reward(response_a, user_message, emotional_state)
        signal_b = self.compute_reward(response_b, user_message, emotional_state)
        
        if signal_a.final_score > signal_b.final_score:
            return "A", signal_a, signal_b
        else:
            return "B", signal_a, signal_b
    
    def get_reward_stats(self) -> Dict[str, Any]:
        """Get reward statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Overall stats
            row = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    AVG(final_score) as avg_score,
                    AVG(rule_based_score) as avg_rule,
                    AVG(llm_based_score) as avg_llm,
                    AVG(meta_judged_score) as avg_meta
                FROM rewards
                """
            ).fetchone()
            
            # Distribution
            distributions = {}
            for threshold in [8.0, 6.0, 4.0]:
                count = conn.execute(
                    "SELECT COUNT(*) FROM rewards WHERE final_score >= ?",
                    (threshold,)
                ).fetchone()[0]
                distributions[f">={threshold}"] = count
            
            return {
                "total_rewards": row['total'],
                "average_scores": {
                    "final": round(row['avg_score'] or 0, 2),
                    "rule_based": round(row['avg_rule'] or 0, 2),
                    "llm_based": round(row['avg_llm'] or 0, 2),
                    "meta_judged": round(row['avg_meta'] or 0, 2),
                },
                "distribution": distributions,
            }
    
    def get_preference_pairs(
        self,
        min_score_diff: float = 1.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get preference pairs for DPO training.
        
        Returns pairs of (chosen, rejected) responses where
        chosen has significantly higher score.
        
        Args:
            min_score_diff: Minimum score difference to be a valid pair
            limit: Max pairs to return
            
        Returns:
            List of preference pairs
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Find pairs from same conversation context
            rows = conn.execute(
                """
                SELECT * FROM rewards
                WHERE final_score >= 6.0
                ORDER BY final_score DESC
                LIMIT ?
                """,
                (limit * 2,)
            ).fetchall()
            
            pairs = []
            for i, chosen in enumerate(rows):
                for rejected in rows[i+1:]:
                    if chosen['final_score'] - rejected['final_score'] >= min_score_diff:
                        pairs.append({
                            "prompt": chosen['user_message'],
                            "chosen": chosen['response_text'],
                            "rejected": rejected['response_text'],
                            "chosen_score": chosen['final_score'],
                            "rejected_score": rejected['final_score'],
                        })
                        if len(pairs) >= limit:
                            break
                if len(pairs) >= limit:
                    break
            
            return pairs
