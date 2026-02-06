"""
Demi Autonomy System - Full Self-Modification Capabilities.

This package provides Demi with the ability to:
- Review and analyze her own codebase
- Generate improvement suggestions
- Safely modify her own code
- Track changes with Git version control
- Validate changes through testing
- Protect against dangerous modifications
- Self-heal when things go wrong

Components:
- SelfImprovementSystem: Main interface for all self-modification
- SafeCodeModifier: Safe file modification with backups
- GitManager: Version control integration
- ModificationValidator: Testing and validation
- SafetyGuard: Rate limiting and protections
- EmergencyHealing: Self-repair system
- AutonomyConfig: Configuration management

Usage:
    from src.autonomy import SelfImprovementSystem
    
    # Initialize
    improvement = SelfImprovementSystem(conductor)
    
    # Review code
    suggestions = await improvement.run_code_review()
    
    # Apply improvements (with full safety)
    for suggestion in suggestions:
        success = await improvement.apply_suggestion(suggestion)
"""

from src.autonomy.self_improvement import (
    SelfImprovementSystem,
    ImprovementSuggestion,
    ImprovementStatus,
)

from src.autonomy.code_modifier import (
    SafeCodeModifier,
    ModificationResult,
    ModificationContext,
    ModificationAttempt,
)

from src.autonomy.git_manager import (
    GitManager,
    GitResult,
    GitCommit,
    GitOperation,
    ModificationBranch,
)

from src.autonomy.modification_validator import (
    ModificationValidator,
    ValidationResult,
    ValidationCheck,
    ValidationReport,
)

from src.autonomy.safety_guard import (
    SafetyGuard,
    SafetyLevel,
    SafetyViolation,
    SafetyEvent,
)

from src.autonomy.emergency_healing import (
    EmergencyHealing,
    HealingAction,
    HealingResult,
    HealingEvent,
    HealthCheck,
)

from src.autonomy.autonomy_config import (
    SelfModificationConfig,
    AutonomyConfigManager,
    get_autonomy_config,
    get_autonomy_config_manager,
)

__all__ = [
    # Main system
    "SelfImprovementSystem",
    "ImprovementSuggestion",
    "ImprovementStatus",
    
    # Code modification
    "SafeCodeModifier",
    "ModificationResult",
    "ModificationContext",
    "ModificationAttempt",
    
    # Git integration
    "GitManager",
    "GitResult",
    "GitCommit",
    "GitOperation",
    "ModificationBranch",
    
    # Validation
    "ModificationValidator",
    "ValidationResult",
    "ValidationCheck",
    "ValidationReport",
    
    # Safety
    "SafetyGuard",
    "SafetyLevel",
    "SafetyViolation",
    "SafetyEvent",
    
    # Healing
    "EmergencyHealing",
    "HealingAction",
    "HealingResult",
    "HealingEvent",
    "HealthCheck",
    
    # Configuration
    "SelfModificationConfig",
    "AutonomyConfigManager",
    "get_autonomy_config",
    "get_autonomy_config_manager",
]

__version__ = "1.0.0"
