"""
Long-Running Stability Test for Demi.

Validates Demi's ability to operate continuously for 7+ days without
manual intervention. Tracks uptime, memory, response times, and emotional
state consistency over time.

Requirements:
    - HEALTH-01: 7-day continuous operation validation
"""

import asyncio
import time
import signal
import sys
import json
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

from src.conductor.orchestrator import Conductor, SystemStatus
from src.conductor.health import get_health_monitor, HealthStatus, HealthCheckResult
from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.core.logger import get_logger

logger = get_logger()


class TestStatus(Enum):
    """Status of the stability test."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPING = "stopping"


@dataclass
class StabilityTestConfig:
    """Configuration for long-running stability test."""
    duration_hours: float = 168.0  # 7 days default
    checkpoint_interval_minutes: int = 60
    load_pattern: str = "casual_user"  # active_user, casual_user, sporadic_user, stress_test
    memory_threshold_percent: float = 80.0
    cpu_threshold_percent: float = 80.0
    response_time_threshold_ms: float = 3000.0  # 3 seconds p90
    emotion_check_interval_minutes: int = 30
    health_check_interval_seconds: float = 5.0


@dataclass
class StabilityMetrics:
    """Metrics collected during stability test."""
    start_time: float = field(default_factory=time.time)
    total_interactions: int = 0
    successful_responses: int = 0
    failed_responses: int = 0
    restarts: int = 0
    emotion_checks: List[Dict] = field(default_factory=list)
    resource_snapshots: List[Dict] = field(default_factory=list)
    response_times: List[float] = field(default_factory=list)
    error_log: List[Dict] = field(default_factory=list)
    
    @property
    def uptime_hours(self) -> float:
        """Calculate uptime in hours."""
        return (time.time() - self.start_time) / 3600
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of responses."""
        total = self.successful_responses + self.failed_responses
        return self.successful_responses / total if total > 0 else 0.0
    
    @property
    def p90_response_time(self) -> float:
        """Calculate p90 response time in milliseconds."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.9)
        return sorted_times[min(index, len(sorted_times) - 1)] * 1000
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time in milliseconds."""
        if not self.response_times:
            return 0.0
        return (sum(self.response_times) / len(self.response_times)) * 1000
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "uptime_hours": self.uptime_hours,
            "total_interactions": self.total_interactions,
            "successful_responses": self.successful_responses,
            "failed_responses": self.failed_responses,
            "success_rate": self.success_rate,
            "p90_response_time_ms": self.p90_response_time,
            "avg_response_time_ms": self.avg_response_time,
            "restarts": self.restarts,
            "emotion_check_count": len(self.emotion_checks),
            "resource_snapshot_count": len(self.resource_snapshots),
            "error_count": len(self.error_log),
        }


class LongRunningStabilityTest:
    """
    Long-running stability test harness for Demi.
    
    Runs continuous tests for a specified duration (default 7 days),
    monitoring system health, resource usage, response times, and
    emotional state consistency.
    
    Features:
    - Automatic checkpointing for resume capability
    - Graceful shutdown on signals
    - Resource usage monitoring
    - Response time tracking
    - Emotional state consistency verification
    - Error logging and recovery
    
    Example:
        >>> test = LongRunningStabilityTest(duration_hours=168)
        >>> await test.setup()
        >>> await test.run()
        >>> print(test.generate_report())
    """
    
    def __init__(
        self,
        duration_hours: float = 168,
        checkpoint_interval_minutes: int = 60,
        config: Optional[StabilityTestConfig] = None
    ):
        """
        Initialize stability test.
        
        Args:
            duration_hours: Test duration in hours (default 168 = 7 days)
            checkpoint_interval_minutes: How often to save progress
            config: Optional custom configuration
        """
        self.config = config or StabilityTestConfig(
            duration_hours=duration_hours,
            checkpoint_interval_minutes=checkpoint_interval_minutes
        )
        self.duration_hours = duration_hours
        self.checkpoint_interval = checkpoint_interval_minutes
        
        self.metrics = StabilityMetrics()
        self.status = TestStatus.INITIALIZING
        
        # System components
        self.conductor: Optional[Conductor] = None
        self.emotion_persistence: Optional[EmotionPersistence] = None
        
        # State
        self._shutdown_requested = False
        self._last_checkpoint_time = 0.0
        self._last_emotion_check_time = 0.0
        self._start_time: Optional[float] = None
        
        # Tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._emotion_check_task: Optional[asyncio.Task] = None
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info(
            "stability_test_initialized",
            duration_hours=duration_hours,
            checkpoint_interval=checkpoint_interval_minutes
        )
    
    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self._shutdown_requested = True
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except Exception as e:
            logger.warning(f"Failed to setup signal handlers: {e}")
    
    async def setup(self, config_overrides: Optional[Dict] = None) -> bool:
        """
        Setup the stability test environment.
        
        Args:
            config_overrides: Optional configuration overrides
            
        Returns:
            True if setup successful
        """
        try:
            logger.info("Setting up stability test...")
            
            # Create checkpoint directory
            checkpoint_dir = self._checkpoint_path().parent
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize emotion persistence
            self.emotion_persistence = EmotionPersistence()
            
            # Initialize conductor (but don't start it yet)
            # We use a lightweight mode for testing
            self.conductor = None  # Will be created on demand
            
            # Load previous checkpoint if exists
            checkpoint = self._load_checkpoint()
            if checkpoint:
                logger.info("Resuming from checkpoint")
                self.metrics.start_time = checkpoint.get("start_time", time.time())
                self.metrics.total_interactions = checkpoint.get("metrics", {}).get("total_interactions", 0)
                self.metrics.successful_responses = checkpoint.get("metrics", {}).get("successful_responses", 0)
                self.metrics.failed_responses = checkpoint.get("metrics", {}).get("failed_responses", 0)
            
            self.status = TestStatus.RUNNING
            self._start_time = time.time()
            self._last_checkpoint_time = self._start_time
            self._last_emotion_check_time = self._start_time
            
            logger.info("Stability test setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            self.status = TestStatus.FAILED
            return False
    
    async def run(self) -> bool:
        """
        Run the main stability test loop.
        
        Returns:
            True if test completed successfully
        """
        if self.status != TestStatus.RUNNING:
            logger.error("Test not in running state, call setup() first")
            return False
        
        logger.info(f"Starting stability test for {self.duration_hours} hours")
        
        try:
            # Start monitoring tasks
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            self._emotion_check_task = asyncio.create_task(self._emotion_check_loop())
            
            # Main test loop
            end_time = self.metrics.start_time + (self.duration_hours * 3600)
            
            while not self._shutdown_requested:
                current_time = time.time()
                
                # Check if test duration complete
                if current_time >= end_time:
                    logger.info("Test duration complete")
                    break
                
                # Sleep briefly to prevent busy waiting
                await asyncio.sleep(1)
                
                # Log progress every hour
                elapsed_hours = (current_time - self.metrics.start_time) / 3600
                remaining_hours = self.duration_hours - elapsed_hours
                
                if int(elapsed_hours) > int((current_time - 1 - self.metrics.start_time) / 3600):
                    progress = (elapsed_hours / self.duration_hours) * 100
                    logger.info(
                        f"Progress: {progress:.1f}% ({elapsed_hours:.1f}h / {self.duration_hours}h), "
                        f"Interactions: {self.metrics.total_interactions}, "
                        f"Success rate: {self.metrics.success_rate:.1%}"
                    )
            
            # Wait for monitoring tasks to complete
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            if self._checkpoint_task:
                self._checkpoint_task.cancel()
                try:
                    await self._checkpoint_task
                except asyncio.CancelledError:
                    pass
            
            if self._emotion_check_task:
                self._emotion_check_task.cancel()
                try:
                    await self._emotion_check_task
                except asyncio.CancelledError:
                    pass
            
            # Final checkpoint
            await self._save_checkpoint()
            
            self.status = TestStatus.COMPLETED
            logger.info("Stability test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.status = TestStatus.FAILED
            self.metrics.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "type": "test_failure"
            })
            return False
    
    async def _monitoring_loop(self):
        """Background loop for resource monitoring."""
        logger.info("Starting monitoring loop")
        
        while not self._shutdown_requested:
            try:
                # Collect resource metrics every 30 seconds
                snapshot = self._collect_resource_snapshot()
                self.metrics.resource_snapshots.append(snapshot)
                
                # Check for resource threshold violations
                if snapshot.get("memory_percent", 0) > self.config.memory_threshold_percent:
                    logger.warning(f"Memory threshold exceeded: {snapshot['memory_percent']:.1f}%")
                    self.metrics.error_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "error": f"Memory threshold exceeded: {snapshot['memory_percent']:.1f}%",
                        "type": "resource_warning"
                    })
                
                if snapshot.get("cpu_percent", 0) > self.config.cpu_threshold_percent:
                    logger.warning(f"CPU threshold exceeded: {snapshot['cpu_percent']:.1f}%")
                
                # Maintain rolling window of snapshots (last 7 days)
                max_snapshots = int(7 * 24 * 3600 / 30)  # 7 days of 30-second intervals
                if len(self.metrics.resource_snapshots) > max_snapshots:
                    self.metrics.resource_snapshots = self.metrics.resource_snapshots[-max_snapshots:]
                
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _checkpoint_loop(self):
        """Background loop for checkpointing."""
        logger.info(f"Starting checkpoint loop (interval: {self.checkpoint_interval} minutes)")
        
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.checkpoint_interval * 60)
                
                if not self._shutdown_requested:
                    await self._save_checkpoint()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Checkpoint loop error: {e}")
    
    async def _emotion_check_loop(self):
        """Background loop for emotional state verification."""
        logger.info("Starting emotion check loop")
        
        while not self._shutdown_requested:
            try:
                check_interval = self.config.emotion_check_interval_minutes * 60
                await asyncio.sleep(check_interval)
                
                if not self._shutdown_requested:
                    await self._check_emotional_consistency()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Emotion check loop error: {e}")
    
    def _collect_resource_snapshot(self) -> Dict:
        """Collect current resource usage snapshot."""
        try:
            process = psutil.Process()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "process_memory_mb": process.memory_info().rss / (1024 * 1024),
                "process_cpu_percent": process.cpu_percent(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
            }
        except Exception as e:
            logger.error(f"Failed to collect resource snapshot: {e}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}
    
    async def _check_emotional_consistency(self) -> Dict:
        """Check emotional state consistency."""
        try:
            if not self.emotion_persistence:
                return {"status": "error", "message": "Emotion persistence not initialized"}
            
            state = self.emotion_persistence.load_latest_state()
            
            if not state:
                return {"status": "no_state", "message": "No emotional state found"}
            
            # Record emotion check
            check_result = {
                "timestamp": datetime.now().isoformat(),
                "state": state.to_dict(),
                "dominant_emotions": state.get_dominant_emotions(3),
            }
            
            # Validate all emotions in valid range
            issues = []
            for name, value in state.get_all_emotions().items():
                if not (0 <= value <= 1):
                    issues.append(f"{name}={value} out of range [0,1]")
                if value != value:  # NaN check
                    issues.append(f"{name} is NaN")
            
            check_result["issues"] = issues
            check_result["valid"] = len(issues) == 0
            
            self.metrics.emotion_checks.append(check_result)
            
            if issues:
                logger.warning(f"Emotion consistency issues: {issues}")
            
            return check_result
            
        except Exception as e:
            logger.error(f"Emotion consistency check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _save_checkpoint(self):
        """Save current test state to checkpoint file."""
        try:
            checkpoint = {
                "timestamp": time.time(),
                "start_time": self.metrics.start_time,
                "duration_hours": self.duration_hours,
                "metrics": self.metrics.to_dict(),
                "progress_percent": (self.metrics.uptime_hours / self.duration_hours) * 100,
                "status": self.status.value,
            }
            
            checkpoint_path = self._checkpoint_path()
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            
            self._last_checkpoint_time = time.time()
            logger.debug(f"Checkpoint saved: {checkpoint_path}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def _load_checkpoint(self) -> Optional[Dict]:
        """Load previous checkpoint if exists."""
        try:
            checkpoint_path = self._checkpoint_path()
            if checkpoint_path.exists():
                with open(checkpoint_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def _checkpoint_path(self) -> Path:
        """Get path to checkpoint file."""
        checkpoint_dir = Path("~/.demi/stability_checkpoints").expanduser()
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir / "stability_test_checkpoint.json"
    
    async def record_interaction(
        self,
        success: bool,
        response_time_seconds: float,
        error: Optional[str] = None
    ):
        """
        Record an interaction result.
        
        Args:
            success: Whether the interaction was successful
            response_time_seconds: Response time in seconds
            error: Optional error message
        """
        self.metrics.total_interactions += 1
        self.metrics.response_times.append(response_time_seconds)
        
        if success:
            self.metrics.successful_responses += 1
        else:
            self.metrics.failed_responses += 1
            if error:
                self.metrics.error_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "error": error,
                    "type": "interaction_failure"
                })
        
        # Check response time threshold
        if response_time_seconds * 1000 > self.config.response_time_threshold_ms:
            logger.warning(f"Response time threshold exceeded: {response_time_seconds*1000:.0f}ms")
    
    def verify_response_times(self) -> Dict:
        """
        Verify that response times meet requirements.
        
        Returns:
            Dict with verification results
        """
        p90 = self.metrics.p90_response_time
        avg = self.metrics.avg_response_time
        
        passed = p90 <= self.config.response_time_threshold_ms
        
        return {
            "passed": passed,
            "p90_ms": p90,
            "avg_ms": avg,
            "threshold_ms": self.config.response_time_threshold_ms,
            "total_samples": len(self.metrics.response_times),
        }
    
    def verify_emotional_consistency(self) -> Dict:
        """
        Verify emotional state consistency over test period.
        
        Returns:
            Dict with verification results
        """
        if not self.metrics.emotion_checks:
            return {"passed": False, "message": "No emotion checks recorded"}
        
        invalid_checks = [c for c in self.metrics.emotion_checks if not c.get("valid", True)]
        
        passed = len(invalid_checks) == 0
        
        return {
            "passed": passed,
            "total_checks": len(self.metrics.emotion_checks),
            "invalid_checks": len(invalid_checks),
            "issues": [c.get("issues", []) for c in invalid_checks],
        }
    
    async def graceful_shutdown(self):
        """Perform graceful shutdown."""
        logger.info("Initiating graceful shutdown...")
        self.status = TestStatus.STOPPING
        self._shutdown_requested = True
        
        # Save final checkpoint
        await self._save_checkpoint()
        
        logger.info("Graceful shutdown complete")
    
    def generate_report(self) -> str:
        """
        Generate human-readable test report.
        
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("DEMI STABILITY TEST REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Test Status: {self.status.value}")
        lines.append(f"Duration: {self.metrics.uptime_hours:.2f} hours / {self.duration_hours} hours")
        lines.append(f"Progress: {(self.metrics.uptime_hours / self.duration_hours) * 100:.1f}%")
        lines.append("")
        
        # Interactions
        lines.append("INTERACTIONS")
        lines.append("-" * 40)
        lines.append(f"Total Interactions: {self.metrics.total_interactions}")
        lines.append(f"Successful: {self.metrics.successful_responses}")
        lines.append(f"Failed: {self.metrics.failed_responses}")
        lines.append(f"Success Rate: {self.metrics.success_rate:.1%}")
        lines.append("")
        
        # Response times
        response_check = self.verify_response_times()
        lines.append("RESPONSE TIMES")
        lines.append("-" * 40)
        lines.append(f"P90 Response Time: {response_check['p90_ms']:.1f}ms (threshold: {response_check['threshold_ms']:.0f}ms)")
        lines.append(f"Average Response Time: {response_check['avg_ms']:.1f}ms")
        lines.append(f"Status: {'PASS' if response_check['passed'] else 'FAIL'}")
        lines.append("")
        
        # Resource usage
        if self.metrics.resource_snapshots:
            latest = self.metrics.resource_snapshots[-1]
            lines.append("RESOURCE USAGE (Latest)")
            lines.append("-" * 40)
            lines.append(f"Memory: {latest.get('memory_percent', 'N/A')}%")
            lines.append(f"CPU: {latest.get('cpu_percent', 'N/A')}%")
            lines.append(f"Process Memory: {latest.get('process_memory_mb', 'N/A'):.1f} MB")
            lines.append("")
        
        # Emotional state
        emotion_check = self.verify_emotional_consistency()
        lines.append("EMOTIONAL STATE")
        lines.append("-" * 40)
        lines.append(f"Total Checks: {emotion_check['total_checks']}")
        lines.append(f"Invalid Checks: {emotion_check['invalid_checks']}")
        lines.append(f"Status: {'PASS' if emotion_check['passed'] else 'FAIL'}")
        lines.append("")
        
        # Errors
        lines.append("ERRORS")
        lines.append("-" * 40)
        lines.append(f"Total Errors: {len(self.metrics.error_log)}")
        if self.metrics.error_log:
            lines.append("Recent errors:")
            for error in self.metrics.error_log[-5:]:
                lines.append(f"  - [{error.get('timestamp', 'N/A')}] {error.get('error', 'Unknown')}")
        lines.append("")
        
        # Overall result
        lines.append("=" * 70)
        all_passed = (
            response_check['passed'] and
            emotion_check['passed'] and
            self.metrics.success_rate >= 0.95
        )
        if all_passed:
            lines.append("OVERALL RESULT: PASS")
        else:
            lines.append("OVERALL RESULT: FAIL")
        lines.append("=" * 70)
        
        return "\n".join(lines)


async def main():
    """Run stability test from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run long-running stability test")
    parser.add_argument(
        "--duration",
        type=float,
        default=168,
        help="Test duration in hours (default: 168 = 7 days)"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=60,
        help="Checkpoint interval in minutes"
    )
    parser.add_argument(
        "--load-pattern",
        type=str,
        default="casual_user",
        choices=["active_user", "casual_user", "sporadic_user", "stress_test"],
        help="Load pattern for simulated interactions"
    )
    
    args = parser.parse_args()
    
    config = StabilityTestConfig(
        duration_hours=args.duration,
        checkpoint_interval_minutes=args.checkpoint_interval,
        load_pattern=args.load_pattern
    )
    
    test = LongRunningStabilityTest(
        duration_hours=args.duration,
        checkpoint_interval_minutes=args.checkpoint_interval,
        config=config
    )
    
    await test.setup()
    try:
        await test.run()
    finally:
        report = test.generate_report()
        print(report)


if __name__ == "__main__":
    asyncio.run(main())
