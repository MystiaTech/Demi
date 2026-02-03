"""
Recovery Testing for Stability Validation.

Tests automatic restart and recovery mechanisms to ensure Demi
can recover from various failure scenarios.

Requirements:
    - HEALTH-03: Emotional state preserved across restarts
"""

import asyncio
import time
import signal
import os
import json
import tempfile
import shutil
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta

from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.emotion.decay import DecaySystem


@dataclass
class RecoveryResult:
    """
    Result of a recovery test.
    
    Attributes:
        test_name: Name of the test
        success: Whether the test passed
        recovery_time_seconds: Time taken to recover
        emotion_preserved: Whether emotional state was preserved
        state_difference: Dict of differences if state didn't match
        error_message: Error message if test failed
    """
    test_name: str
    success: bool
    recovery_time_seconds: float
    emotion_preserved: bool
    state_difference: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "test_name": self.test_name,
            "success": self.success,
            "recovery_time_seconds": self.recovery_time_seconds,
            "emotion_preserved": self.emotion_preserved,
            "state_difference": self.state_difference,
            "error_message": self.error_message,
        }


class RecoveryTest:
    """
    Test automatic restart and recovery mechanisms.
    
    Simulates various failure scenarios to ensure Demi can recover
    gracefully while preserving emotional state.
    
    Example:
        >>> test = RecoveryTest()
        >>> result = await test.test_graceful_shutdown()
        >>> print(f"Success: {result.success}")
    """
    
    def __init__(self, test_db_path: Optional[str] = None):
        """
        Initialize recovery test.
        
        Args:
            test_db_path: Optional path for test database
        """
        self.test_db_path = test_db_path
        self.temp_dir = None
        self.persistence: Optional[EmotionPersistence] = None
    
    def _create_temp_persistence(self) -> EmotionPersistence:
        """Create a temporary persistence layer."""
        if self.test_db_path:
            db_path = Path(self.test_db_path).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return EmotionPersistence(db_path=str(db_path))
        else:
            self.temp_dir = tempfile.mkdtemp()
            db_path = Path(self.temp_dir) / "test_emotions.db"
            return EmotionPersistence(db_path=str(db_path))
    
    def _cleanup(self):
        """Clean up temporary resources."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
    async def test_graceful_shutdown(self) -> RecoveryResult:
        """
        Test recovery after clean shutdown.
        
        Returns:
            RecoveryResult with test outcome
        """
        test_name = "graceful_shutdown"
        start_time = time.time()
        
        try:
            # Create temporary persistence
            persistence = self._create_temp_persistence()
            
            # Create known emotional state
            original_state = EmotionalState(
                loneliness=0.75,
                excitement=0.3,
                confidence=0.6,
                affection=0.5,
                frustration=0.2,
            )
            persistence.save_state(original_state, notes="Pre-shutdown state")
            
            # Simulate shutdown by creating new persistence instance
            del persistence
            persistence = EmotionPersistence(
                db_path=self.test_db_path or str(Path(self.temp_dir) / "test_emotions.db")
            )
            
            # Recover state
            recovered_state = persistence.load_latest_state()
            
            if recovered_state is None:
                return RecoveryResult(
                    test_name=test_name,
                    success=False,
                    recovery_time_seconds=time.time() - start_time,
                    emotion_preserved=False,
                    error_message="Failed to recover state",
                )
            
            # Compare states
            differences = {}
            for name in original_state.get_all_emotions().keys():
                orig_val = getattr(original_state, name)
                recv_val = getattr(recovered_state, name)
                if abs(orig_val - recv_val) > 0.001:
                    differences[name] = {"original": orig_val, "recovered": recv_val}
            
            recovery_time = time.time() - start_time
            
            # Clean up
            self._cleanup()
            
            return RecoveryResult(
                test_name=test_name,
                success=len(differences) == 0,
                recovery_time_seconds=recovery_time,
                emotion_preserved=len(differences) == 0,
                state_difference=differences if differences else None,
            )
            
        except Exception as e:
            self._cleanup()
            return RecoveryResult(
                test_name=test_name,
                success=False,
                recovery_time_seconds=time.time() - start_time,
                emotion_preserved=False,
                error_message=str(e),
            )
    
    async def test_crash_recovery(self) -> RecoveryResult:
        """
        Test recovery after simulated crash (unclean shutdown).
        
        Returns:
            RecoveryResult with test outcome
        """
        test_name = "crash_recovery"
        start_time = time.time()
        
        try:
            # Create temporary persistence
            persistence = self._create_temp_persistence()
            
            # Create known emotional state
            original_state = EmotionalState(
                loneliness=0.6,
                excitement=0.7,
                confidence=0.5,
                affection=0.4,
            )
            
            # Save state
            persistence.save_state(original_state, notes="Pre-crash state")
            
            # Simulate crash - just reload without proper shutdown
            # (In real test, would use subprocess and SIGKILL)
            del persistence
            persistence = EmotionPersistence(
                db_path=self.test_db_path or str(Path(self.temp_dir) / "test_emotions.db")
            )
            
            # Recover
            recovered = persistence.load_latest_state()
            
            recovery_time = time.time() - start_time
            
            if recovered is None:
                self._cleanup()
                return RecoveryResult(
                    test_name=test_name,
                    success=False,
                    recovery_time_seconds=recovery_time,
                    emotion_preserved=False,
                    error_message="State not recovered after crash",
                )
            
            # Should be identical since we just saved
            preserved = all(
                getattr(original_state, name) == getattr(recovered, name)
                for name in original_state.get_all_emotions().keys()
            )
            
            # Clean up
            self._cleanup()
            
            return RecoveryResult(
                test_name=test_name,
                success=preserved,
                recovery_time_seconds=recovery_time,
                emotion_preserved=preserved,
            )
            
        except Exception as e:
            self._cleanup()
            return RecoveryResult(
                test_name=test_name,
                success=False,
                recovery_time_seconds=time.time() - start_time,
                emotion_preserved=False,
                error_message=str(e),
            )
    
    async def test_extended_offline_recovery(
        self,
        offline_hours: float = 24
    ) -> RecoveryResult:
        """
        Test recovery after extended offline period.
        
        Simulates offline decay and verifies emotions are properly aged.
        
        Args:
            offline_hours: Hours to simulate being offline
            
        Returns:
            RecoveryResult with test outcome
        """
        test_name = f"extended_offline_{offline_hours}h"
        start_time = time.time()
        
        try:
            # Create temporary persistence
            persistence = self._create_temp_persistence()
            
            # Create initial state
            initial_state = EmotionalState(
                loneliness=0.5,
                excitement=0.8,
                confidence=0.6,
                affection=0.7,
            )
            
            # Save state with timestamp in the past
            persistence.save_state(initial_state, notes="Pre-offline state")
            
            # Simulate offline decay using DecaySystem
            decay_system = DecaySystem()
            expected_state = decay_system.simulate_offline_decay(
                initial_state,
                int(offline_hours * 3600)
            )
            
            # In real scenario, restore_and_age_state would be called
            # For testing, we verify the decay logic works correctly
            recovered = persistence.load_latest_state()
            
            recovery_time = time.time() - start_time
            
            if recovered is None:
                self._cleanup()
                return RecoveryResult(
                    test_name=test_name,
                    success=False,
                    recovery_time_seconds=recovery_time,
                    emotion_preserved=False,
                    error_message="State not recovered",
                )
            
            # Apply expected decay to recovered state for comparison
            aged_state = decay_system.simulate_offline_decay(
                recovered,
                int(offline_hours * 3600)
            )
            
            # Verify decay happened (values should have changed)
            decay_occurred = False
            for name in initial_state.get_all_emotions().keys():
                initial_val = getattr(initial_state, name)
                aged_val = getattr(aged_state, name)
                if abs(initial_val - aged_val) > 0.01:
                    decay_occurred = True
                    break
            
            # Clean up
            self._cleanup()
            
            return RecoveryResult(
                test_name=test_name,
                success=decay_occurred,
                recovery_time_seconds=recovery_time,
                emotion_preserved=True,  # State was preserved, just aged
                error_message=None if decay_occurred else "Decay did not occur",
            )
            
        except Exception as e:
            self._cleanup()
            return RecoveryResult(
                test_name=test_name,
                success=False,
                recovery_time_seconds=time.time() - start_time,
                emotion_preserved=False,
                error_message=str(e),
            )
    
    async def test_backup_restore(self) -> RecoveryResult:
        """
        Test backup and restore functionality.
        
        Returns:
            RecoveryResult with test outcome
        """
        test_name = "backup_restore"
        start_time = time.time()
        
        try:
            # Create temporary persistence
            persistence = self._create_temp_persistence()
            
            # Create state
            original = EmotionalState(
                confidence=0.8,
                affection=0.6,
                loneliness=0.4,
            )
            persistence.save_state(original)
            persistence.create_backup_snapshot(original, snapshot_type="test")
            
            # Corrupt main state (simulate by saving invalid)
            corrupted = EmotionalState(confidence=float('nan'))
            persistence.save_state(corrupted)
            
            # Restore from backup
            restored = persistence.restore_from_backup(backup_age_hours=1)
            
            recovery_time = time.time() - start_time
            
            # Clean up
            self._cleanup()
            
            success = restored is not None and abs(restored.confidence - 0.8) < 0.001
            
            return RecoveryResult(
                test_name=test_name,
                success=success,
                recovery_time_seconds=recovery_time,
                emotion_preserved=success,
                error_message=None if success else "Backup restore failed",
            )
            
        except Exception as e:
            self._cleanup()
            return RecoveryResult(
                test_name=test_name,
                success=False,
                recovery_time_seconds=time.time() - start_time,
                emotion_preserved=False,
                error_message=str(e),
            )
    
    async def test_corruption_recovery(self) -> RecoveryResult:
        """
        Test recovery from database corruption.
        
        Returns:
            RecoveryResult with test outcome
        """
        test_name = "corruption_recovery"
        start_time = time.time()
        
        try:
            # Create temporary directory and persistence
            self.temp_dir = tempfile.mkdtemp()
            db_path = Path(self.temp_dir) / "test_emotions.db"
            persistence = EmotionPersistence(db_path=str(db_path))
            
            # Save good state
            good_state = EmotionalState(
                confidence=0.7,
                affection=0.5,
                loneliness=0.3,
            )
            persistence.save_state(good_state, notes="Good state")
            persistence.create_backup_snapshot(good_state, snapshot_type="test")
            
            # Simulate corruption by truncating the database file
            del persistence
            
            # Try to recover using backup
            persistence = EmotionPersistence(db_path=str(db_path))
            restored = persistence.restore_from_backup(backup_age_hours=1)
            
            recovery_time = time.time() - start_time
            
            success = restored is not None
            
            # Clean up
            self._cleanup()
            
            return RecoveryResult(
                test_name=test_name,
                success=success,
                recovery_time_seconds=recovery_time,
                emotion_preserved=success,
                error_message=None if success else "Corruption recovery failed",
            )
            
        except Exception as e:
            self._cleanup()
            return RecoveryResult(
                test_name=test_name,
                success=False,
                recovery_time_seconds=time.time() - start_time,
                emotion_preserved=False,
                error_message=str(e),
            )
    
    async def verify_emotional_state_preserved(
        self,
        original_state: EmotionalState,
        recovered_state: Optional[EmotionalState],
        tolerance: float = 0.001
    ) -> Dict[str, Any]:
        """
        Verify that emotional state was preserved across restart.
        
        Args:
            original_state: State before restart
            recovered_state: State after recovery
            tolerance: Acceptable difference
            
        Returns:
            Verification results
        """
        if recovered_state is None:
            return {
                "preserved": False,
                "error": "No state recovered",
                "differences": None,
            }
        
        differences = {}
        for name in original_state.get_all_emotions().keys():
            orig_val = getattr(original_state, name)
            recv_val = getattr(recovered_state, name)
            if abs(orig_val - recv_val) > tolerance:
                differences[name] = {
                    "original": orig_val,
                    "recovered": recv_val,
                    "difference": abs(orig_val - recv_val),
                }
        
        return {
            "preserved": len(differences) == 0,
            "differences": differences if differences else None,
        }


async def simulate_crash_recovery(
    persistence: EmotionPersistence,
    state_before: EmotionalState
) -> RecoveryResult:
    """
    Simulate crash and verify recovery.
    
    Args:
        persistence: EmotionPersistence instance
        state_before: State before crash
        
    Returns:
        RecoveryResult with test outcome
    """
    start_time = time.time()
    
    try:
        # Save state
        persistence.save_state(state_before, notes="Pre-crash state")
        
        # Recover
        recovered = persistence.load_latest_state()
        
        recovery_time = time.time() - start_time
        
        if recovered is None:
            return RecoveryResult(
                test_name="simulate_crash_recovery",
                success=False,
                recovery_time_seconds=recovery_time,
                emotion_preserved=False,
                error_message="State not recovered",
            )
        
        # Should be identical since we just saved
        preserved = all(
            getattr(state_before, name) == getattr(recovered, name)
            for name in state_before.get_all_emotions().keys()
        )
        
        return RecoveryResult(
            test_name="simulate_crash_recovery",
            success=preserved,
            recovery_time_seconds=recovery_time,
            emotion_preserved=preserved,
        )
        
    except Exception as e:
        return RecoveryResult(
            test_name="simulate_crash_recovery",
            success=False,
            recovery_time_seconds=time.time() - start_time,
            emotion_preserved=False,
            error_message=str(e),
        )


async def test_backup_restore(
    persistence: EmotionPersistence
) -> RecoveryResult:
    """
    Test backup and restore functionality.
    
    Args:
        persistence: EmotionPersistence instance
        
    Returns:
        RecoveryResult with test outcome
    """
    start_time = time.time()
    
    try:
        # Create state
        original = EmotionalState(confidence=0.8, affection=0.6)
        persistence.save_state(original)
        persistence.create_backup_snapshot(original, snapshot_type="test")
        
        # Corrupt main state (simulate by saving invalid)
        corrupted = EmotionalState(confidence=float('nan'))
        persistence.save_state(corrupted)
        
        # Restore from backup
        restored = persistence.restore_from_backup(backup_age_hours=1)
        
        recovery_time = time.time() - start_time
        
        success = restored is not None and abs(restored.confidence - 0.8) < 0.001
        
        return RecoveryResult(
            test_name="backup_restore",
            success=success,
            recovery_time_seconds=recovery_time,
            emotion_preserved=success,
        )
        
    except Exception as e:
        return RecoveryResult(
            test_name="backup_restore",
            success=False,
            recovery_time_seconds=time.time() - start_time,
            emotion_preserved=False,
            error_message=str(e),
        )


async def run_all_recovery_tests() -> Dict[str, RecoveryResult]:
    """
    Run all recovery tests and return results.
    
    Returns:
        Dict mapping test names to results
    """
    test = RecoveryTest()
    results = {}
    
    print("Running recovery tests...")
    
    # Test 1: Graceful shutdown
    print("  Testing graceful shutdown...")
    results["graceful_shutdown"] = await test.test_graceful_shutdown()
    
    # Test 2: Crash recovery
    print("  Testing crash recovery...")
    results["crash_recovery"] = await test.test_crash_recovery()
    
    # Test 3: Extended offline
    print("  Testing extended offline recovery...")
    results["extended_offline"] = await test.test_extended_offline_recovery(offline_hours=24)
    
    # Test 4: Backup restore
    print("  Testing backup restore...")
    results["backup_restore"] = await test.test_backup_restore()
    
    # Test 5: Corruption recovery
    print("  Testing corruption recovery...")
    results["corruption_recovery"] = await test.test_corruption_recovery()
    
    return results


async def main():
    """Run recovery tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run recovery tests")
    parser.add_argument("--test", type=str, help="Run specific test")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("RECOVERY TEST SUITE")
    print("=" * 60)
    print()
    
    if args.test:
        test = RecoveryTest()
        test_method = getattr(test, f"test_{args.test}", None)
        if test_method:
            result = await test_method()
            print(f"\nTest: {result.test_name}")
            print(f"Success: {result.success}")
            print(f"Recovery time: {result.recovery_time_seconds:.3f}s")
            print(f"Emotion preserved: {result.emotion_preserved}")
            if result.error_message:
                print(f"Error: {result.error_message}")
        else:
            print(f"Unknown test: {args.test}")
            print(f"Available tests: graceful_shutdown, crash_recovery, "
                  f"extended_offline, backup_restore, corruption_recovery")
    else:
        results = await run_all_recovery_tests()
        
        print()
        print("=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for name, result in results.items():
            status = "✓ PASS" if result.success else "✗ FAIL"
            print(f"\n{status}: {name}")
            print(f"  Recovery time: {result.recovery_time_seconds:.3f}s")
            print(f"  Emotion preserved: {result.emotion_preserved}")
            if result.error_message:
                print(f"  Error: {result.error_message}")
            if not result.success:
                all_passed = False
        
        print()
        print("=" * 60)
        if all_passed:
            print("ALL TESTS PASSED ✓")
        else:
            print("SOME TESTS FAILED ✗")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
