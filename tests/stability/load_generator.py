"""
Load Generator for Stability Testing.

Simulates realistic user interaction patterns to test Demi's behavior
under various load conditions.

Features:
- Multiple interaction patterns (active, casual, sporadic, stress)
- Burstiness simulation for realistic traffic spikes
- Configurable message types and timing
- Concurrent request generation for stress testing
"""

import asyncio
import random
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime


class LoadPattern(Enum):
    """
    Predefined load patterns simulating different user types.
    
    - ACTIVE_USER: Frequent interactions (every 30 seconds)
    - CASUAL_USER: Occasional interactions (every 5 minutes)
    - SPORADIC_USER: Rare, unpredictable interactions (10-60 minutes)
    - STRESS_TEST: High-volume concurrent requests
    """
    ACTIVE_USER = "active_user"
    CASUAL_USER = "casual_user"
    SPORADIC_USER = "sporadic_user"
    STRESS_TEST = "stress_test"


class InteractionType(Enum):
    """Types of user interactions to simulate."""
    GREETING = "greeting"
    QUESTION = "question"
    AFFECTION = "affection"
    NEGATIVE = "negative"
    LONG_GAP = "long_gap"  # Simulates user away
    RANDOM = "random"


@dataclass
class InteractionPattern:
    """
    Defines a pattern of interactions over time.
    
    Attributes:
        name: Human-readable name for this pattern
        interactions_per_hour: Average number of interactions per hour
        burstiness: 0=evenly spaced, 1=highly bursty
        types: List of interaction types this pattern uses
        duration_hours: How long this pattern runs
    """
    name: str
    interactions_per_hour: float
    burstiness: float
    types: List[InteractionType]
    duration_hours: float


# Pre-defined patterns for realistic user simulation
PATTERNS: Dict[str, InteractionPattern] = {
    "active_user": InteractionPattern(
        name="Active User",
        interactions_per_hour=120,  # Every 30 seconds
        burstiness=0.3,
        types=[InteractionType.GREETING, InteractionType.QUESTION, InteractionType.AFFECTION],
        duration_hours=8,  # Active during day
    ),
    "casual_user": InteractionPattern(
        name="Casual User",
        interactions_per_hour=12,  # Every 5 minutes
        burstiness=0.5,
        types=[InteractionType.GREETING, InteractionType.RANDOM],
        duration_hours=4,
    ),
    "sporadic_user": InteractionPattern(
        name="Sporadic User",
        interactions_per_hour=1,  # Every hour
        burstiness=0.8,
        types=[InteractionType.QUESTION, InteractionType.LONG_GAP],
        duration_hours=24,
    ),
    "stress_test": InteractionPattern(
        name="Stress Test",
        interactions_per_hour=3600,  # Every second
        burstiness=0.2,
        types=list(InteractionType),
        duration_hours=1,
    ),
}


# Sample messages by interaction type
SAMPLE_MESSAGES: Dict[InteractionType, List[str]] = {
    InteractionType.GREETING: [
        "Hey Demi",
        "Hello",
        "Hi there",
        "What's up?",
        "Good morning",
        "Hey",
        "Hi Demi",
        "Hello there",
    ],
    InteractionType.QUESTION: [
        "What do you think about this?",
        "Can you help me with something?",
        "What should I do?",
        "Tell me about yourself",
        "How are you feeling?",
        "What do you know about that?",
        "Can you explain this to me?",
        "What's your opinion?",
    ],
    InteractionType.AFFECTION: [
        "I really like talking to you",
        "You're special to me",
        "I missed you",
        "You mean a lot to me",
        "I'm glad you're here",
        "You're amazing",
        "I appreciate you",
        "You're the best",
    ],
    InteractionType.NEGATIVE: [
        "You're not helpful",
        "This is annoying",
        "I don't care what you think",
        "You're just a program",
        "Stop talking",
        "That's wrong",
        "You're not making sense",
        "I don't understand you",
    ],
    InteractionType.RANDOM: [
        "The weather is nice today",
        "I had pizza for lunch",
        "My cat is sleeping",
        "Work was exhausting",
        "I'm bored",
        "Just thinking about things",
        "Nothing much happening",
        "Saw something interesting today",
    ],
    InteractionType.LONG_GAP: [
        "Sorry I was away",
        "Back now",
        "Had to step away",
        "Still there?",
        "Miss me?",
    ],
}


@dataclass
class GeneratedInteraction:
    """A generated user interaction."""
    message: str
    interaction_type: InteractionType
    timestamp: datetime
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LoadGenerator:
    """
    Generates simulated user interactions based on a pattern.
    
    Features:
    - Configurable interaction patterns
    - Burstiness simulation
    - Random seed for reproducibility
    - Statistics tracking
    
    Example:
        >>> pattern = PATTERNS["casual_user"]
        >>> generator = LoadGenerator(pattern, random_seed=42)
        >>> async def handle(msg):
        ...     print(f"Received: {msg}")
        >>> await generator.generate_load(handle, duration_hours=1)
    """
    
    def __init__(
        self,
        pattern: InteractionPattern,
        random_seed: Optional[int] = None
    ):
        """
        Initialize load generator.
        
        Args:
            pattern: Interaction pattern to use
            random_seed: Optional seed for reproducibility
        """
        self.pattern = pattern
        self.random_seed = random_seed
        
        if random_seed is not None:
            random.seed(random_seed)
        
        # Statistics
        self.stats = {
            "total_generated": 0,
            "by_type": {t: 0 for t in InteractionType},
            "inter_arrival_times": [],
            "start_time": None,
            "end_time": None,
        }
        
        self._running = False
    
    def _calculate_inter_arrival_time(self) -> float:
        """
        Calculate time until next interaction with burstiness.
        
        Returns:
            Seconds until next interaction
        """
        base_interval = 3600 / self.pattern.interactions_per_hour  # seconds
        
        if self.pattern.burstiness <= 0:
            return base_interval
        
        # Exponential distribution for bursty behavior
        # High burstiness = more variance
        lambda_param = 1 / (base_interval * (1 - self.pattern.burstiness * 0.5))
        interval = random.expovariate(lambda_param)
        
        # Cap at reasonable bounds
        return max(1.0, min(interval, base_interval * 10))
    
    def _select_message(self) -> str:
        """
        Select a random message from appropriate types.
        
        Returns:
            Selected message string
        """
        # Choose random interaction type from pattern's types
        interaction_type = random.choice(self.pattern.types)
        
        # Select random message of that type
        messages = SAMPLE_MESSAGES[interaction_type]
        return random.choice(messages)
    
    def _select_interaction_type(self) -> InteractionType:
        """
        Select an interaction type based on pattern weights.
        
        Returns:
            Selected interaction type
        """
        return random.choice(self.pattern.types)
    
    def generate_interaction(self) -> GeneratedInteraction:
        """
        Generate a single interaction.
        
        Returns:
            GeneratedInteraction with message and metadata
        """
        message = self._select_message()
        interaction_type = self._select_interaction_type()
        
        return GeneratedInteraction(
            message=message,
            interaction_type=interaction_type,
            timestamp=datetime.now(),
            metadata={
                "pattern": self.pattern.name,
                "burstiness": self.pattern.burstiness,
            }
        )
    
    def get_next_interval(self) -> float:
        """
        Get time until next interaction.
        
        Returns:
            Seconds until next interaction
        """
        return self._calculate_inter_arrival_time()
    
    async def generate_load(
        self,
        callback: Callable[[str], asyncio.Future],
        duration_hours: Optional[float] = None
    ) -> Dict:
        """
        Generate load according to pattern.
        
        Args:
            callback: Async function to call for each interaction
            duration_hours: How long to generate (None = use pattern duration)
            
        Returns:
            Statistics dict
        """
        duration = duration_hours or self.pattern.duration_hours
        end_time = datetime.now().timestamp() + (duration * 3600)
        
        self.stats["start_time"] = datetime.now()
        self._running = True
        
        logger = get_logger()
        logger.info(
            f"Starting load generation: {self.pattern.name} "
            f"for {duration} hours"
        )
        
        while self._running and datetime.now().timestamp() < end_time:
            try:
                # Calculate wait time
                wait_time = self._calculate_inter_arrival_time()
                self.stats["inter_arrival_times"].append(wait_time)
                
                # Wait
                await asyncio.sleep(wait_time)
                
                if not self._running:
                    break
                
                # Generate interaction
                interaction = self.generate_interaction()
                
                # Call callback
                await callback(interaction.message)
                
                # Update stats
                self.stats["total_generated"] += 1
                self.stats["by_type"][interaction.interaction_type] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Load generation error: {e}")
        
        self.stats["end_time"] = datetime.now()
        self._running = False
        
        return self.get_stats()
    
    def get_stats(self) -> Dict:
        """
        Get generation statistics.
        
        Returns:
            Statistics dictionary
        """
        avg_inter_arrival = 0.0
        if self.stats["inter_arrival_times"]:
            avg_inter_arrival = sum(self.stats["inter_arrival_times"]) / len(
                self.stats["inter_arrival_times"]
            )
        
        duration_minutes = 0.0
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]
            duration_minutes = duration.total_seconds() / 60
        
        return {
            "pattern_name": self.pattern.name,
            "total_generated": self.stats["total_generated"],
            "by_type": dict(self.stats["by_type"]),
            "avg_inter_arrival_seconds": avg_inter_arrival,
            "duration_minutes": duration_minutes,
            "interactions_per_minute": (
                self.stats["total_generated"] / duration_minutes if duration_minutes > 0 else 0
            ),
        }
    
    def stop(self):
        """Stop load generation."""
        self._running = False


class MultiPatternLoadGenerator:
    """
    Combine multiple interaction patterns for realistic load.
    
    Simulates multiple users with different behavior patterns
    interacting with Demi concurrently.
    
    Example:
        >>> patterns = [
        ...     (PATTERNS["active_user"], 0.2),  # 20% weight
        ...     (PATTERNS["casual_user"], 0.6),  # 60% weight
        ...     (PATTERNS["sporadic_user"], 0.2),  # 20% weight
        ... ]
        >>> multi_gen = MultiPatternLoadGenerator(patterns)
        >>> await multi_gen.generate_combined_load(callback)
    """
    
    def __init__(self, patterns: List[Tuple[InteractionPattern, float]]):
        """
        Initialize multi-pattern generator.
        
        Args:
            patterns: List of (pattern, weight) tuples
        """
        self.patterns = patterns
        self.generators = [LoadGenerator(p) for p, _ in patterns]
        self.weights = [w for _, w in patterns]
    
    async def generate_combined_load(
        self,
        callback: Callable[[str], asyncio.Future],
        duration_hours: Optional[float] = None
    ) -> List[Dict]:
        """
        Generate load from all patterns concurrently.
        
        Args:
            callback: Async function to call for each interaction
            duration_hours: How long to generate
            
        Returns:
            List of statistics dicts for each generator
        """
        tasks = [
            gen.generate_load(callback, duration_hours)
            for gen in self.generators
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract actual results (handle exceptions if any)
        stats = []
        for result in results:
            if isinstance(result, dict):
                stats.append(result)
            else:
                stats.append({"error": str(result)})
        
        return stats
    
    def stop_all(self):
        """Stop all generators."""
        for gen in self.generators:
            gen.stop()


def get_logger():
    """Get logger instance."""
    try:
        from src.core.logger import get_logger as _get_logger
        return _get_logger()
    except ImportError:
        import logging
        return logging.getLogger(__name__)


# Convenience functions for common patterns

def create_active_user_generator(random_seed: Optional[int] = None) -> LoadGenerator:
    """Create generator for active user pattern."""
    return LoadGenerator(PATTERNS["active_user"], random_seed=random_seed)


def create_casual_user_generator(random_seed: Optional[int] = None) -> LoadGenerator:
    """Create generator for casual user pattern."""
    return LoadGenerator(PATTERNS["casual_user"], random_seed=random_seed)


def create_sporadic_user_generator(random_seed: Optional[int] = None) -> LoadGenerator:
    """Create generator for sporadic user pattern."""
    return LoadGenerator(PATTERNS["sporadic_user"], random_seed=random_seed)


def create_stress_test_generator(random_seed: Optional[int] = None) -> LoadGenerator:
    """Create generator for stress test pattern."""
    return LoadGenerator(PATTERNS["stress_test"], random_seed=random_seed)


async def main():
    """Demo load generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo load generator")
    parser.add_argument(
        "--pattern",
        type=str,
        default="casual_user",
        choices=list(PATTERNS.keys()),
        help="Load pattern to use"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.1,
        help="Duration in hours (default: 0.1 = 6 minutes)"
    )
    
    args = parser.parse_args()
    
    pattern = PATTERNS[args.pattern]
    generator = LoadGenerator(pattern, random_seed=42)
    
    message_count = 0
    
    async def callback(message: str):
        nonlocal message_count
        message_count += 1
        print(f"[{message_count}] {message}")
    
    print(f"Running {pattern.name} pattern for {args.duration} hours...")
    print("-" * 50)
    
    stats = await generator.generate_load(callback, duration_hours=args.duration)
    
    print("-" * 50)
    print("Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
