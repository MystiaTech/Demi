"""
Self-improvement system for Demi.

Enables autonomous code review, refactoring suggestions, and learning
from interactions to improve responses over time.
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from src.core.logger import get_logger
from src.llm.codebase_reader import CodebaseReader

logger = get_logger()


class ImprovementSuggestion:
    """A suggestion for code improvement."""
    
    def __init__(
        self,
        file_path: str,
        suggestion: str,
        priority: str = "medium",
        confidence: float = 0.5,
    ):
        self.file_path = file_path
        self.suggestion = suggestion
        self.priority = priority  # low, medium, high
        self.confidence = confidence
        self.created_at = datetime.now(timezone.utc)
        self.implemented = False


class SelfImprovementSystem:
    """
    Handles self-improvement through code review and learning.
    
    Features:
    - Periodic code review of own codebase
    - Learning from conversation patterns
    - Suggesting refactoring opportunities
    """
    
    def __init__(self, conductor=None):
        self.conductor = conductor
        self.logger = logger
        self.enabled = True
        self.last_review_time: Optional[datetime] = None
        self.suggestions: List[ImprovementSuggestion] = []
        self.codebase_reader: Optional[CodebaseReader] = None
        
        # Initialize codebase reader if conductor available
        if conductor and hasattr(conductor, 'codebase_reader'):
            self.codebase_reader = conductor.codebase_reader
        else:
            try:
                self.codebase_reader = CodebaseReader(logger=self.logger)
            except Exception as e:
                self.logger.warning(f"Could not initialize codebase reader: {e}")
        
        self.logger.info("SelfImprovementSystem initialized")
    
    async def run_code_review(self) -> List[ImprovementSuggestion]:
        """
        Review codebase and generate improvement suggestions.
        
        Returns:
            List of suggestions
        """
        if not self.enabled or not self.conductor:
            return []
        
        if not self.codebase_reader:
            self.logger.warning("Codebase reader not available")
            return []
        
        try:
            self.logger.info("Starting self-code review...")
            
            # Get recent conversation patterns
            recent_interactions = self._get_recent_interactions()
            
            # Build prompt for code review
            review_prompt = self._build_review_prompt(recent_interactions)
            
            # Run review through LLM
            messages = [{"role": "user", "content": review_prompt}]
            response = await self.conductor.request_inference(messages)
            
            # Parse suggestions
            suggestions = self._parse_review_response(response)
            
            self.suggestions.extend(suggestions)
            self.last_review_time = datetime.now(timezone.utc)
            
            self.logger.info(f"Code review complete: {len(suggestions)} suggestions")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Code review failed: {e}")
            return []
    
    def _build_review_prompt(self, recent_interactions: List[Dict]) -> str:
        """Build prompt for code review."""
        
        # Get sample of codebase
        sample_code = self._get_codebase_sample()
        
        prompt = f"""You are reviewing your own code (Demi's codebase) to identify improvement opportunities.

Recent conversation patterns:
{self._format_interactions(recent_interactions)}

Sample of current code:
{sample_code}

Based on this, identify:
1. Code that could be optimized or simplified
2. Missing error handling
3. Opportunities for better modularity
4. Places where patterns from conversations suggest improvements

Format your response as:
FILE: <filepath>
PRIORITY: <low/medium/high>
SUGGESTION: <detailed suggestion>
CONFIDENCE: <0-1>

Be constructive and specific. Focus on concrete improvements."""
        
        return prompt
    
    def _get_codebase_sample(self) -> str:
        """Get a sample of codebase for review."""
        if not self.codebase_reader:
            return "# Codebase not available"
        
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
                full_path = Path(file_path)
                if full_path.exists():
                    with open(full_path, 'r') as f:
                        content = f.read()
                        # Limit to first 100 lines
                        lines = content.split('\n')[:100]
                        sample.append(f"\n# {file_path}\n" + '\n'.join(lines))
            except Exception as e:
                self.logger.debug(f"Could not read {file_path}: {e}")
        
        return '\n'.join(sample) if sample else "# No sample available"
    
    def _get_recent_interactions(self) -> List[Dict]:
        """Get recent conversation patterns."""
        # This would integrate with conversation history
        # For now, return empty list
        return []
    
    def _format_interactions(self, interactions: List[Dict]) -> str:
        """Format interactions for prompt."""
        if not interactions:
            return "No recent interactions available"
        return "\n".join([f"- {i.get('content', '')[:100]}" for i in interactions[-10:]])
    
    def _parse_review_response(self, response: str) -> List[ImprovementSuggestion]:
        """Parse LLM review response into suggestions."""
        suggestions = []
        
        # Simple parsing - look for FILE: blocks
        current_suggestion = {}
        
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('FILE:'):
                if current_suggestion:
                    suggestions.append(self._create_suggestion(current_suggestion))
                current_suggestion = {'file': line.replace('FILE:', '').strip()}
            elif line.startswith('PRIORITY:'):
                current_suggestion['priority'] = line.replace('PRIORITY:', '').strip().lower()
            elif line.startswith('SUGGESTION:'):
                current_suggestion['suggestion'] = line.replace('SUGGESTION:', '').strip()
            elif line.startswith('CONFIDENCE:'):
                try:
                    current_suggestion['confidence'] = float(line.replace('CONFIDENCE:', '').strip())
                except ValueError:
                    current_suggestion['confidence'] = 0.5
            elif current_suggestion.get('suggestion') and line:
                current_suggestion['suggestion'] += ' ' + line
        
        if current_suggestion:
            suggestions.append(self._create_suggestion(current_suggestion))
        
        return suggestions
    
    def _create_suggestion(self, data: Dict) -> ImprovementSuggestion:
        """Create ImprovementSuggestion from parsed data."""
        return ImprovementSuggestion(
            file_path=data.get('file', 'unknown'),
            suggestion=data.get('suggestion', 'No suggestion provided'),
            priority=data.get('priority', 'medium'),
            confidence=data.get('confidence', 0.5),
        )
    
    def get_pending_suggestions(self, priority_filter: Optional[str] = None) -> List[ImprovementSuggestion]:
        """Get pending suggestions, optionally filtered by priority."""
        pending = [s for s in self.suggestions if not s.implemented]
        if priority_filter:
            pending = [s for s in pending if s.priority == priority_filter]
        return pending
    
    def mark_implemented(self, suggestion: ImprovementSuggestion):
        """Mark a suggestion as implemented."""
        suggestion.implemented = True
        self.logger.info(f"Marked suggestion as implemented: {suggestion.file_path}")
    
    def get_status(self) -> Dict:
        """Get current status of self-improvement system."""
        return {
            "enabled": self.enabled,
            "last_review": self.last_review_time.isoformat() if self.last_review_time else None,
            "total_suggestions": len(self.suggestions),
            "pending_suggestions": len(self.get_pending_suggestions()),
            "implemented_suggestions": len([s for s in self.suggestions if s.implemented]),
            "high_priority": len(self.get_pending_suggestions("high")),
        }
