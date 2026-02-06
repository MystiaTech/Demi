"""
Demi Self-Evolution Systems (Phase 2)

Modules for autonomous self-improvement:
- error_analyzer: Detect and categorize errors
- conversation_quality: Measure response quality
- self_critique: Evaluate own responses
- self_reward: Generate training signals
- meta_learning: Learn how to learn
- continual_learning: Learn without forgetting

Research-backed implementations from:
- SELF_EVOLUTION_RESEARCH_REPORT.md
- 100+ academic papers
"""

from src.evolution.error_analyzer import ErrorAnalyzer, ErrorCategory, ErrorRecord
from src.evolution.conversation_quality import ConversationQualityAnalyzer, QualityMetrics
from src.evolution.self_critique import SelfCritique, CritiqueResult
from src.evolution.self_reward import SelfRewarder, RewardSignal
from src.evolution.change_tracker import ChangeTracker, ChangeRecord
from src.evolution.response_revisor import ResponseRevisor, RevisionSession, RevisionStrategy
from src.evolution.pattern_learning import PatternLearningDB, LearnedPattern, MistakeEntry

__all__ = [
    "ErrorAnalyzer",
    "ErrorCategory", 
    "ErrorRecord",
    "ConversationQualityAnalyzer",
    "QualityMetrics",
    "SelfCritique",
    "CritiqueResult",
    "SelfRewarder",
    "RewardSignal",
    "ChangeTracker",
    "ChangeRecord",
    "ResponseRevisor",
    "RevisionSession",
    "RevisionStrategy",
    "PatternLearningDB",
    "LearnedPattern",
    "MistakeEntry",
]
