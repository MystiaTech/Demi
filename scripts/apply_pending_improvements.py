#!/usr/bin/env python3
"""
Apply pending improvement suggestions from self-improvement system.

This script applies any suggestions that are waiting in the queue.
Useful for applying suggestions generated from LM Studio conversations.

Usage:
    python scripts/apply_pending_improvements.py
    python scripts/apply_pending_improvements.py --suggestion-id <id>
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.autonomy.self_improvement import SelfImprovementSystem
from src.core.logger import get_logger

logger = get_logger()


async def apply_specific(suggestion_id: str):
    """Apply a specific suggestion by ID."""
    print(f"🔧 Applying suggestion: {suggestion_id}")
    
    improvement = SelfImprovementSystem(project_root=str(project_root))
    
    # Find the suggestion
    suggestion = improvement.suggestions.get(suggestion_id)
    if not suggestion:
        print(f"❌ Suggestion {suggestion_id} not found")
        return False
    
    print(f"   File: {suggestion.file_path}")
    print(f"   Description: {suggestion.description}")
    print()
    
    # Apply it
    result = await improvement.apply_suggestion(suggestion)
    
    if result:
        print(f"✅ Successfully applied {suggestion_id}")
        return True
    else:
        print(f"❌ Failed to apply {suggestion_id}")
        print(f"   Error: {suggestion.error_message}")
        return False


async def apply_all_pending():
    """Apply all pending suggestions."""
    print("🔧 Applying all pending suggestions...")
    print()
    
    improvement = SelfImprovementSystem(project_root=str(project_root))
    
    # Get pending suggestions
    pending = improvement.get_pending_suggestions()
    
    if not pending:
        print("✅ No pending suggestions to apply")
        return
    
    print(f"Found {len(pending)} pending suggestions:")
    for sugg in pending:
        print(f"  - {sugg.suggestion_id}: {sugg.file_path} ({sugg.priority})")
    print()
    
    # Apply each one
    results = []
    for suggestion in pending:
        print(f"Applying {suggestion.suggestion_id}...")
        result = await improvement.apply_suggestion(suggestion)
        results.append((suggestion.suggestion_id, result))
        
        if result:
            print(f"  ✅ Success")
        else:
            print(f"  ❌ Failed: {suggestion.error_message}")
    
    print()
    print("=" * 60)
    success_count = sum(1 for _, r in results if r)
    print(f"Applied {success_count}/{len(results)} suggestions")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Apply self-improvement suggestions")
    parser.add_argument(
        "--suggestion-id",
        help="Apply a specific suggestion by ID"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Apply all pending suggestions"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 DEMI PENDING IMPROVEMENTS APPLIER")
    print("=" * 60)
    print()
    
    if args.suggestion_id:
        success = await apply_specific(args.suggestion_id)
        sys.exit(0 if success else 1)
    elif args.all:
        await apply_all_pending()
    else:
        # Default: show pending and apply all
        improvement = SelfImprovementSystem(project_root=str(project_root))
        pending = improvement.get_pending_suggestions()
        
        if not pending:
            print("✅ No pending suggestions to apply")
            return
        
        print(f"Found {len(pending)} pending suggestions")
        print("Use --all to apply them all, or --suggestion-id <id> for a specific one")
        print()
        for sugg in pending:
            print(f"  - {sugg.suggestion_id}: {sugg.file_path}")
            print(f"    {sugg.description[:80]}...")


if __name__ == "__main__":
    asyncio.run(main())
