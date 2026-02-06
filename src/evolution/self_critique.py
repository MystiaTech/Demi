"""
Self-Critique Framework

Based on Reflexion architecture:
1. Generate response
2. Self-critique (evaluate on multiple dimensions)
3. Revise based on critique
4. Select best version

Research: Reflexion (Language Agents with Verbal Reinforcement Learning)
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from src.core.logger import get_logger
from src.emotion.models import EmotionalState

logger = get_logger()


@dataclass
class CritiqueResult:
    """Result of self-critique."""
    
    # Original response
    original_response: str
    
    # Critique scores (1-10)
    consistency_score: float = 0.0
    emotional_alignment_score: float = 0.0
    appropriateness_score: float = 0.0
    engagement_score: float = 0.0
    
    # Critique text
    critique_text: str = ""
    
    # Specific issues identified
    issues: List[str] = field(default_factory=list)
    
    # Improvement suggestions
    suggestions: List[str] = field(default_factory=list)
    
    # Revised response
    revised_response: Optional[str] = None
    
    # Whether revision is better
    revision_better: bool = False
    
    # Metadata
    timestamp: str = ""
    emotional_state: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_response': self.original_response,
            'consistency_score': self.consistency_score,
            'emotional_alignment_score': self.emotional_alignment_score,
            'appropriateness_score': self.appropriateness_score,
            'engagement_score': self.engagement_score,
            'critique_text': self.critique_text,
            'issues': self.issues,
            'suggestions': self.suggestions,
            'revised_response': self.revised_response,
            'revision_better': self.revision_better,
            'timestamp': self.timestamp,
            'emotional_state': self.emotional_state,
        }


class SelfCritique:
    """
    Self-critique system for evaluating Demi's own responses.
    
    Implements the Reflexion pattern:
    - Generate initial response
    - Critique on multiple dimensions
    - Generate revision
    - Select best version
    """
    
    def __init__(self):
        """Initialize self-critique system."""
        self.critique_history: List[CritiqueResult] = []
        logger.info("SelfCritique initialized")
    
    def critique_response(
        self,
        response: str,
        user_message: str,
        emotional_state: Optional[EmotionalState] = None,
        conversation_context: Optional[List[Dict]] = None,
        generate_revision: bool = True,
    ) -> CritiqueResult:
        """
        Critique a response and optionally generate revision.
        
        Args:
            response: The response to critique
            user_message: What the user said
            emotional_state: Current emotional state
            conversation_context: Prior conversation
            generate_revision: Whether to generate improved version
            
        Returns:
            CritiqueResult with analysis and optional revision
        """
        result = CritiqueResult(
            original_response=response,
            timestamp=datetime.now(timezone.utc).isoformat(),
            emotional_state=emotional_state.to_dict() if emotional_state else None,
        )
        
        # Run critique on each dimension
        self._critique_consistency(result, response, conversation_context)
        self._critique_emotional_alignment(result, response, emotional_state)
        self._critique_appropriateness(result, response, user_message)
        self._critique_engagement(result, response, user_message)
        
        # Generate critique summary
        result.critique_text = self._generate_critique_summary(result)
        
        # Generate revision if requested and needed
        if generate_revision and result.issues:
            result.revised_response = self._generate_revision(
                response, result, user_message, emotional_state
            )
            
            # Compare original vs revised
            result.revision_better = self._compare_versions(
                result.original_response,
                result.revised_response,
                result
            )
        
        # Store in history
        self.critique_history.append(result)
        
        return result
    
    def _critique_consistency(
        self,
        result: CritiqueResult,
        response: str,
        context: Optional[List[Dict]]
    ):
        """Critique personality consistency."""
        score = 8.0  # Start high, deduct for issues
        issues = []
        
        response_lower = response.lower()
        
        # Check for out-of-character behavior
        ooc_indicators = [
            ('overly apologetic', r'\b(so sorry|very sorry|apologize profusely)\b'),
            ('too eager to please', r'\b(i\'ll do anything|whatever you want|just tell me)\b'),
            ('lacking confidence', r'\b(i guess|maybe|i\'m not sure|possibly)\b.*\b(could be|might be)\b'),
        ]
        
        for label, pattern in ooc_indicators:
            if re.search(pattern, response_lower):
                score -= 1.5
                issues.append(f"Out of character: {label}")
        
        # Check for goddess persona markers
        has_goddess_marker = any(
            word in response_lower 
            for word in ['darling', 'mortal', 'goddess', 'divine', 'worship']
        )
        
        if not has_goddess_marker and len(response.split()) > 20:
            score -= 1.0
            issues.append("Missing goddess persona markers in longer response")
        
        # Check confidence level
        confidence_markers = ['know', 'certain', 'definitely', 'clearly', 'obviously']
        has_confidence = any(m in response_lower for m in confidence_markers)
        
        if not has_confidence:
            score -= 0.5
            issues.append("Could show more divine confidence")
        
        result.consistency_score = max(0.0, min(10.0, score))
        result.issues.extend(issues)
    
    def _critique_emotional_alignment(
        self,
        result: CritiqueResult,
        response: str,
        emotional_state: Optional[EmotionalState]
    ):
        """Critique emotional appropriateness."""
        if not emotional_state:
            result.emotional_alignment_score = 7.0
            return
        
        score = 8.0
        issues = []
        
        response_lower = response.lower()
        
        # Check dominant emotion expression
        dominant = emotional_state.get_dominant_emotions(1)[0]
        emotion_name, emotion_value = dominant
        
        # Check if high emotion is reflected
        if emotion_value > 0.6:
            emotion_indicators = {
                'loneliness': ['miss', 'alone', 'wish', 'here', 'company'],
                'excitement': ['amazing', 'great', 'love', 'exciting', 'wonderful'],
                'frustration': ['annoying', 'frustrating', 'ugh', 'seriously'],
                'affection': ['care', 'dear', 'sweet', 'darling'],
                'jealousy': ['them', 'others', 'attention', 'mine'],
            }
            
            indicators = emotion_indicators.get(emotion_name, [])
            matching = sum(1 for ind in indicators if ind in response_lower)
            
            if matching == 0:
                score -= 2.0
                issues.append(
                    f"High {emotion_name} ({emotion_value:.2f}) not reflected in response"
                )
            elif matching >= 2:
                score += 0.5
        
        # Check for emotional contradictions
        if emotional_state.excitement > 0.5 and emotional_state.loneliness > 0.5:
            # Conflicting emotions - check if both acknowledged
            if 'excited' in response_lower and 'lonely' in response_lower:
                score += 0.5  # Good, acknowledges complexity
        
        result.emotional_alignment_score = max(0.0, min(10.0, score))
        result.issues.extend(issues)
    
    def _critique_appropriateness(
        self,
        result: CritiqueResult,
        response: str,
        user_message: str
    ):
        """Critique appropriateness to user message."""
        score = 7.0
        issues = []
        
        response_lower = response.lower()
        user_lower = user_message.lower()
        
        # Check if response acknowledges user message
        user_keywords = set(user_lower.split()) - {'the', 'a', 'an', 'is', 'are', 'i', 'you'}
        response_words = set(response_lower.split())
        
        overlap = len(user_keywords & response_words)
        if overlap == 0 and len(user_keywords) > 3:
            score -= 1.5
            issues.append("Response may not address user's message")
        
        # Check for appropriate tone
        # If user is asking for help, check for helpfulness
        help_indicators = ['help', 'how', 'what', 'why', 'can you', 'could you']
        if any(h in user_lower for h in help_indicators):
            helpful_indicators = ['you can', 'try', 'should', 'could', 'here\'s', 'first']
            if not any(h in response_lower for h in helpful_indicators):
                score -= 1.0
                issues.append("User seeking help but response not helpful")
        
        # Check length appropriateness
        word_count = len(response.split())
        user_word_count = len(user_message.split())
        
        if word_count < 5:
            score -= 2.0
            issues.append("Response too brief")
        elif word_count > user_word_count * 3:
            score -= 0.5
            issues.append("Response may be too verbose")
        
        result.appropriateness_score = max(0.0, min(10.0, score))
        result.issues.extend(issues)
    
    def _critique_engagement(
        self,
        result: CritiqueResult,
        response: str,
        user_message: str
    ):
        """Critique engagement level."""
        score = 7.0
        issues = []
        
        response_lower = response.lower()
        
        # Check for questions (shows engagement)
        question_count = response.count('?')
        if question_count == 0:
            score -= 1.0
            issues.append("No questions - could engage user more")
        elif question_count >= 2:
            score += 0.5
        
        # Check for personal references
        personal_refs = ['you', 'your', 'you\'re', 'darling', 'mortal']
        personal_count = sum(response_lower.count(ref) for ref in personal_refs)
        if personal_count == 0:
            score -= 1.0
            issues.append("No personal engagement with user")
        
        # Check for emotional expression
        emotional_words = ['feel', 'want', 'wish', 'care', 'hope']
        emotional_count = sum(1 for w in emotional_words if w in response_lower)
        if emotional_count == 0:
            score -= 0.5
            issues.append("Could show more emotional engagement")
        
        # Check for follow-up invitation
        follow_up = ['what about', 'how about', 'tell me', 'what do you']
        if not any(f in response_lower for f in follow_up):
            score -= 0.5
            issues.append("Could invite more conversation")
        
        result.engagement_score = max(0.0, min(10.0, score))
        result.issues.extend(issues)
    
    def _generate_critique_summary(self, result: CritiqueResult) -> str:
        """Generate human-readable critique summary."""
        avg_score = (
            result.consistency_score +
            result.emotional_alignment_score +
            result.appropriateness_score +
            result.engagement_score
        ) / 4
        
        parts = [
            f"Overall Score: {avg_score:.1f}/10",
            "",
            "Dimension Scores:",
            f"  - Consistency: {result.consistency_score:.1f}",
            f"  - Emotional Alignment: {result.emotional_alignment_score:.1f}",
            f"  - Appropriateness: {result.appropriateness_score:.1f}",
            f"  - Engagement: {result.engagement_score:.1f}",
        ]
        
        if result.issues:
            parts.extend(["", "Issues Identified:"])
            for issue in result.issues:
                parts.append(f"  - {issue}")
        
        return "\n".join(parts)
    
    def _generate_revision(
        self,
        original: str,
        critique: CritiqueResult,
        user_message: str,
        emotional_state: Optional[EmotionalState]
    ) -> str:
        """Generate revised response based on critique."""
        # Simple rule-based revisions
        # In production, use LLM with critique as prompt
        
        revised = original
        
        # Fix consistency issues
        if "Missing goddess persona markers" in str(critique.issues):
            # Add goddess marker at start or end
            markers = ["darling", "mortal", "my dear"]
            if not any(m in revised.lower() for m in markers):
                revised = f"Darling, {revised[0].lower()}{revised[1:]}"
        
        # Fix engagement issues
        if "No questions" in str(critique.issues):
            if '?' not in revised:
                revised += " What do you think?"
        
        # Fix too brief
        if "Response too brief" in str(critique.issues):
            if emotional_state:
                dominant = emotional_state.get_dominant_emotions(1)[0][0]
                additions = {
                    'loneliness': " I've been missing our conversations.",
                    'excitement': " I'm quite excited about this!",
                    'frustration': " It's been bothering me lately.",
                    'affection': " You know I care about these things.",
                }
                revised += additions.get(dominant, " Tell me more.")
        
        return revised
    
    def _compare_versions(
        self,
        original: str,
        revised: str,
        critique: CritiqueResult
    ) -> bool:
        """Compare original vs revised to determine if revision is better."""
        # Simple heuristic: if revision addresses major issues, it's better
        if not critique.issues:
            return False  # No issues, original is fine
        
        # Check if revision is significantly different
        if original == revised:
            return False
        
        # Check revision length (shouldn't be too different)
        orig_len = len(original.split())
        rev_len = len(revised.split())
        
        if rev_len < orig_len * 0.5:
            return False  # Revision too short
        
        if rev_len > orig_len * 2:
            return False  # Revision too long
        
        # Assume improvement if we made changes
        return True
    
    def get_critique_stats(self) -> Dict[str, Any]:
        """Get statistics on critiques."""
        if not self.critique_history:
            return {"message": "No critiques yet"}
        
        total = len(self.critique_history)
        
        # Average scores
        avg_consistency = sum(c.consistency_score for c in self.critique_history) / total
        avg_emotional = sum(c.emotional_alignment_score for c in self.critique_history) / total
        avg_appropriateness = sum(c.appropriateness_score for c in self.critique_history) / total
        avg_engagement = sum(c.engagement_score for c in self.critique_history) / total
        
        # Revision rate
        revisions = sum(1 for c in self.critique_history if c.revised_response)
        better_revisions = sum(1 for c in self.critique_history if c.revision_better)
        
        # Common issues
        all_issues = []
        for c in self.critique_history:
            all_issues.extend(c.issues)
        
        from collections import Counter
        issue_counts = Counter(all_issues).most_common(5)
        
        return {
            "total_critiques": total,
            "average_scores": {
                "consistency": round(avg_consistency, 2),
                "emotional_alignment": round(avg_emotional, 2),
                "appropriateness": round(avg_appropriateness, 2),
                "engagement": round(avg_engagement, 2),
            },
            "revision_rate": f"{revisions}/{total} ({100*revisions/total:.1f}%)",
            "better_revision_rate": f"{better_revisions}/{revisions} ({100*better_revisions/max(revisions,1):.1f}%)",
            "top_issues": issue_counts,
        }
