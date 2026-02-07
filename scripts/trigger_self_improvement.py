#!/usr/bin/env python3
"""
Trigger Demi's self-improvement system immediately.

This script allows Demi to review her codebase and apply improvements
without waiting for the scheduled review cycle.

Usage:
    python scripts/trigger_self_improvement.py
    
Environment Variables:
    DEMI_AUTO_APPLY: Set to "true" to auto-apply suggestions (default: true)
    DEMI_REQUIRE_APPROVAL: Set to "true" to require human approval (default: false)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.autonomy.self_improvement import SelfImprovementSystem
from src.llm.codebase_reader import CodebaseReader
from src.core.logger import get_logger

logger = get_logger()


async def main():
    """Run self-improvement review."""
    print("=" * 60)
    print("🤖 DEMI SELF-IMPROVEMENT SYSTEM")
    print("=" * 60)
    print()
    
    # Initialize self-improvement system
    print("📦 Initializing self-improvement system...")
    improvement = SelfImprovementSystem(project_root=str(project_root))
    
    # Configure for full autonomy
    improvement.config.require_human_approval = os.getenv("DEMI_REQUIRE_APPROVAL", "false").lower() == "true"
    improvement.config.auto_apply_low_risk = os.getenv("DEMI_AUTO_APPLY", "true").lower() == "true"
    improvement.config.auto_merge = os.getenv("DEMI_AUTO_MERGE", "true").lower() == "true"
    
    print(f"   Human approval required: {improvement.config.require_human_approval}")
    print(f"   Auto-apply low risk: {improvement.config.auto_apply_low_risk}")
    print(f"   Auto-merge to main: {improvement.config.auto_merge}")
    print()
    
    # Run code review
    print("🔍 Running code review...")
    print()
    
    try:
        suggestions = await improvement.run_code_review()
        
        if not suggestions:
            print("✅ No improvements needed - codebase is already optimal!")
            return
        
        print(f"📝 Found {len(suggestions)} improvement suggestions:")
        print()
        
        for i, sugg in enumerate(suggestions, 1):
            print(f"  {i}. {sugg.file_path}")
            print(f"     Priority: {sugg.priority.upper()} | Confidence: {sugg.confidence:.1%}")
            print(f"     Description: {sugg.description}")
            print(f"     Status: {sugg.status.value}")
            print()
        
        # Show pending approvals if any
        pending = improvement.get_pending_suggestions()
        if pending:
            print(f"⏳ {len(pending)} suggestions pending approval:")
            for sugg in pending:
                print(f"   - {sugg.suggestion_id}: {sugg.file_path} ({sugg.priority})")
            print()
        
        print("=" * 60)
        print("✨ Self-improvement review complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during self-improvement: {e}")
        logger.error(f"Self-improvement error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
