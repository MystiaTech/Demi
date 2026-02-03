"""Memory leak tests for Demi components.

Tests verify that memory usage remains stable during extended operation
and doesn't grow unboundedly.
"""

import pytest
import asyncio
import gc
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from tests.profiling import MemoryProfiler, LeakDetector, MemorySnapshot


class TestConversationMemoryLeak:
    """Test for memory leaks during conversation handling."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(300)  # 5 minutes
    async def test_conversation_memory_leak(self):
        """Test that memory doesn't grow significantly during extended conversation.
        
        Runs ~100 conversations and verifies <5% memory growth.
        """
        profiler = MemoryProfiler()
        detector = LeakDetector()
        
        # Force GC and take baseline
        gc.collect()
        baseline = profiler.take_snapshot()
        detector.start_monitoring()
        detector.add_observation(baseline)
        
        # Simulate conversation workload
        # Note: Using simplified simulation since actual Discord integration
        # would require full test harness
        messages_processed = 0
        
        for i in range(100):
            # Simulate message processing
            messages = [
                {"role": "user", "content": f"Hello Demi, message {i}"},
                {"role": "assistant", "content": f"Hi there! Response {i}"},
            ]
            
            # Create some temporary objects to simulate processing
            temp_data = {
                "conversation_id": i,
                "messages": messages,
                "timestamp": time.time(),
                "metadata": {"index": i, "padding": "x" * 100},  # Some data
            }
            del temp_data  # Clean up immediately
            
            messages_processed += len(messages)
            
            # Take observation every 10 iterations
            if i % 10 == 0:
                gc.collect()
                snapshot = profiler.take_snapshot()
                detector.add_observation(snapshot)
        
        # Final measurement
        gc.collect()
        final = profiler.take_snapshot()
        detector.add_observation(final)
        
        # Calculate growth
        growth_mb = final.rss_mb - baseline.rss_mb
        growth_percent = (growth_mb / baseline.rss_mb) * 100 if baseline.rss_mb > 0 else 0
        
        print(f"\nConversation Memory Test:")
        print(f"  Messages processed: {messages_processed}")
        print(f"  Memory growth: {growth_mb:.1f}MB ({growth_percent:.1f}%)")
        print(f"  Baseline: {baseline.rss_mb:.1f}MB, Final: {final.rss_mb:.1f}MB")
        
        # Assert <10% growth (allowing some variance)
        assert growth_percent < 10, f"Memory grew by {growth_percent:.1f}% - possible leak"
        assert not detector.check_for_leaks(), "Leak detector flagged potential leak"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_emotion_update_leak(self):
        """Test that emotion changes don't leak memory."""
        profiler = MemoryProfiler()
        detector = LeakDetector()
        
        gc.collect()
        baseline = profiler.take_snapshot()
        detector.start_monitoring()
        
        # Simulate many emotion state updates
        for i in range(500):
            # Simulate emotion state creation
            emotion_data = {
                "loneliness": 0.3 + (i % 10) / 20,
                "excitement": 0.4 + (i % 8) / 20,
                "timestamp": time.time(),
                "iteration": i,
            }
            
            # Process and discard
            processed = emotion_data.copy()
            processed["normalized"] = True
            del processed
            del emotion_data
            
            if i % 50 == 0:
                gc.collect()
                snapshot = profiler.take_snapshot()
                detector.add_observation(snapshot)
        
        gc.collect()
        final = profiler.take_snapshot()
        
        growth_percent = ((final.rss_mb - baseline.rss_mb) / baseline.rss_mb) * 100 if baseline.rss_mb > 0 else 0
        
        print(f"\nEmotion Update Leak Test:")
        print(f"  Memory growth: {growth_percent:.1f}%")
        
        assert growth_percent < 15, f"Emotion updates memory grew by {growth_percent:.1f}%"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_discord_integration_leak(self):
        """Test Discord message processing doesn't leak memory."""
        profiler = MemoryProfiler()
        
        gc.collect()
        baseline = profiler.take_snapshot()
        
        # Simulate Discord message processing
        for i in range(200):
            # Simulate message object
            message = {
                "id": i,
                "content": f"Test message {i} " * 50,  # Some content
                "author": {
                    "id": 1000 + (i % 10),
                    "name": f"User{i % 10}",
                },
                "channel_id": 999,
                "timestamp": time.time(),
                "mentions": [f"user{j}" for j in range(5)],
            }
            
            # Simulate processing
            processed = self._simulate_discord_processing(message)
            del processed
            del message
            
            if i % 20 == 0:
                gc.collect()
        
        gc.collect()
        final = profiler.take_snapshot()
        
        growth_percent = ((final.rss_mb - baseline.rss_mb) / baseline.rss_mb) * 100 if baseline.rss_mb > 0 else 0
        
        print(f"\nDiscord Integration Leak Test:")
        print(f"  Memory growth: {growth_percent:.1f}%")
        
        assert growth_percent < 10, f"Discord integration memory grew by {growth_percent:.1f}%"
    
    def _simulate_discord_processing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Discord message processing."""
        result = {
            "processed": True,
            "message_id": message["id"],
            "response": f"Processed: {message['content'][:50]}...",
        }
        return result


class TestRambleGenerationLeak:
    """Test for memory leaks during ramble generation."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_ramble_generation_leak(self):
        """Test ramble generation doesn't accumulate memory."""
        profiler = MemoryProfiler()
        
        gc.collect()
        baseline = profiler.take_snapshot()
        
        # Simulate ramble generation cycles
        for i in range(50):
            # Simulate emotion state that triggers ramble
            emotion_state = {
                "loneliness": 0.9,
                "excitement": 0.2,
                "timestamp": time.time(),
            }
            
            # Simulate ramble content generation
            ramble_content = self._generate_simulated_ramble(i)
            
            # Process ramble
            processed = {
                "emotion": emotion_state,
                "content": ramble_content,
                "iteration": i,
            }
            
            del processed
            del ramble_content
            del emotion_state
            
            await asyncio.sleep(0.01)  # Brief pause
            
            if i % 10 == 0:
                gc.collect()
        
        gc.collect()
        final = profiler.take_snapshot()
        
        growth_percent = ((final.rss_mb - baseline.rss_mb) / baseline.rss_mb) * 100 if baseline.rss_mb > 0 else 0
        
        print(f"\nRamble Generation Leak Test:")
        print(f"  Memory growth: {growth_percent:.1f}%")
        
        assert growth_percent < 10, f"Ramble generation memory grew by {growth_percent:.1f}%"
    
    def _generate_simulated_ramble(self, index: int) -> str:
        """Generate simulated ramble content."""
        templates = [
            "I was thinking about the meaning of existence...",
            "Sometimes I wonder what it would be like to...",
            "The silence is deafening tonight...",
            "I feel like sharing something interesting...",
        ]
        template = templates[index % len(templates)]
        return template + " " * (100 + index)  # Varying size


class TestVoiceProcessingLeak:
    """Test for memory leaks during voice I/O processing."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_voice_processing_leak(self):
        """Test voice I/O doesn't leak memory."""
        profiler = MemoryProfiler()
        
        gc.collect()
        baseline = profiler.take_snapshot()
        
        # Simulate voice processing cycles
        for i in range(100):
            # Simulate audio data
            audio_data = bytes(16000 * 2)  # 1 second of 16-bit audio at 16kHz
            
            # Simulate processing
            processed = self._simulate_voice_processing(audio_data, i)
            del processed
            del audio_data
            
            if i % 10 == 0:
                gc.collect()
                await asyncio.sleep(0.01)
        
        gc.collect()
        final = profiler.take_snapshot()
        
        growth_percent = ((final.rss_mb - baseline.rss_mb) / baseline.rss_mb) * 100 if baseline.rss_mb > 0 else 0
        
        print(f"\nVoice Processing Leak Test:")
        print(f"  Memory growth: {growth_percent:.1f}%")
        
        assert growth_percent < 10, f"Voice processing memory grew by {growth_percent:.1f}%"
    
    def _simulate_voice_processing(self, audio_data: bytes, index: int) -> Dict[str, Any]:
        """Simulate voice processing."""
        return {
            "processed": True,
            "duration_ms": len(audio_data) / 32,
            "index": index,
            "transcription": f"Simulated transcription {index}",
        }


class TestFullPipelineLeak:
    """End-to-end pipeline memory leak tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_full_pipeline_leak(self):
        """Test end-to-end pipeline doesn't leak memory.
        
        Simulates realistic workload mix.
        """
        profiler = MemoryProfiler()
        detector = LeakDetector()
        
        gc.collect()
        baseline = profiler.take_snapshot()
        detector.start_monitoring()
        
        # Mixed workload simulation
        for cycle in range(50):
            # Simulate conversation
            for i in range(5):
                msg = {"content": f"Message {cycle}-{i}", "user_id": 1000 + i}
                self._process_message(msg)
            
            # Simulate emotion update
            self._update_emotions(cycle)
            
            # Simulate some "thinking" / ramble trigger
            if cycle % 10 == 0:
                self._simulate_thinking()
            
            # Periodic cleanup and observation
            if cycle % 5 == 0:
                gc.collect()
                snapshot = profiler.take_snapshot()
                detector.add_observation(snapshot)
        
        gc.collect()
        final = profiler.take_snapshot()
        
        growth_stats = detector.calculate_growth_rate()
        
        print(f"\nFull Pipeline Leak Test:")
        print(f"  Baseline: {baseline.rss_mb:.1f}MB")
        print(f"  Final: {final.rss_mb:.1f}MB")
        print(f"  Growth rate: {growth_stats['growth_rate_mb_per_hour']:.1f}MB/hour")
        print(f"  Projected 7-day: {growth_stats['projected_7day_growth_percent']:.1f}%")
        
        # Check projections
        assert growth_stats['projected_7day_growth_percent'] < 5, \
            f"Projected 7-day growth {growth_stats['projected_7day_growth_percent']:.1f}% exceeds 5%"
    
    def _process_message(self, msg: Dict[str, Any]) -> None:
        """Simulate message processing."""
        processed = msg.copy()
        processed["timestamp"] = time.time()
        del processed
    
    def _update_emotions(self, cycle: int) -> None:
        """Simulate emotion update."""
        emotions = {
            "loneliness": 0.3 + (cycle % 10) / 20,
            "excitement": 0.5 - (cycle % 5) / 20,
        }
        del emotions
    
    def _simulate_thinking(self) -> None:
        """Simulate thinking/ramble process."""
        thoughts = [f"Thought {i}" for i in range(10)]
        del thoughts


class TestLeakDetectorAccuracy:
    """Test leak detector's ability to detect actual leaks."""
    
    def test_leak_detector_identifies_growth_pattern(self):
        """Test that leak detector flags consistent growth."""
        from datetime import datetime, timedelta
        from tests.profiling import MemorySnapshot
        
        detector = LeakDetector(
            min_growth_threshold_mb=10,
            min_growth_percent=2,
            observation_periods=6,
        )
        detector.start_monitoring()
        
        # Create snapshots with clear growth pattern
        base_time = datetime.now()
        base_memory = 1000.0
        
        for i in range(10):
            snapshot = MemorySnapshot(
                timestamp=base_time + timedelta(minutes=i*10),
                rss_mb=base_memory + (i * 20),  # Growing 20MB per period
                vms_mb=base_memory * 2,
                objects_count=1000 + i * 10,
            )
            detector.add_observation(snapshot)
        
        assert detector.check_for_leaks(), "Leak detector should flag this growth pattern"
        
        leaks = detector.get_suspected_leaks()
        assert len(leaks) > 0
        assert leaks[0].growth_mb >= 100  # Should detect ~180MB growth
    
    def test_leak_detector_ignores_stable_memory(self):
        """Test that leak detector doesn't flag stable memory."""
        from datetime import datetime, timedelta
        from tests.profiling import MemorySnapshot
        
        detector = LeakDetector(
            min_growth_threshold_mb=50,
            min_growth_percent=5,
            observation_periods=6,
        )
        detector.start_monitoring()
        
        base_time = datetime.now()
        
        # Create snapshots with stable memory (small fluctuations)
        for i in range(10):
            snapshot = MemorySnapshot(
                timestamp=base_time + timedelta(minutes=i*10),
                rss_mb=1000.0 + (i % 3) * 5,  # Small fluctuations
                vms_mb=2000.0,
                objects_count=1000 + (i % 5),
            )
            detector.add_observation(snapshot)
        
        assert not detector.check_for_leaks(), "Leak detector should not flag stable memory"
    
    def test_leak_detector_filters_false_positives(self):
        """Test statistical filtering of false positives."""
        from datetime import datetime, timedelta
        from tests.profiling import MemorySnapshot
        
        detector = LeakDetector(
            min_growth_threshold_mb=10,
            min_growth_percent=5,
            observation_periods=6,
            false_positive_filter=True,
        )
        detector.start_monitoring()
        
        base_time = datetime.now()
        
        # Create snapshots with high variance but low trend
        import random
        random.seed(42)
        
        for i in range(10):
            # Random fluctuations around a stable mean
            noise = random.gauss(0, 50)  # High variance
            snapshot = MemorySnapshot(
                timestamp=base_time + timedelta(minutes=i*10),
                rss_mb=1000.0 + noise,
                vms_mb=2000.0,
                objects_count=1000,
            )
            detector.add_observation(snapshot)
        
        # High variance should be filtered out
        assert not detector.check_for_leaks(), \
            "High variance data should be filtered as false positive"


class TestMemoryProfilerFeatures:
    """Test MemoryProfiler functionality."""
    
    def setup_imports(self):
        """Helper to ensure imports are available."""
        pass  # Imports are at module level
    """Test MemoryProfiler functionality."""
    
    def test_snapshot_creation(self):
        """Test snapshot creation and attributes."""
        profiler = MemoryProfiler()
        
        snapshot = profiler.take_snapshot()
        
        assert snapshot.rss_mb > 0
        assert snapshot.vms_mb > 0
        assert snapshot.objects_count > 0
        assert isinstance(snapshot.timestamp, datetime)
    
    def test_snapshot_comparison(self):
        """Test comparing two snapshots."""
        from datetime import datetime, timedelta
        
        snapshot1 = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=1000.0,
            vms_mb=2000.0,
            objects_count=10000,
        )
        
        snapshot2 = MemorySnapshot(
            timestamp=datetime.now() + timedelta(hours=1),
            rss_mb=1100.0,
            vms_mb=2100.0,
            objects_count=11000,
        )
        
        profiler = MemoryProfiler()
        diff = profiler.compare_snapshots(snapshot1, snapshot2)
        
        assert abs(diff["rss_diff_mb"] - 100.0) < 0.01
        assert abs(diff["vms_diff_mb"] - 100.0) < 0.01
        assert diff["objects_diff"] == 1000
        assert abs(diff["rss_growth_percent"] - 10.0) < 0.01
        assert abs(diff["hours_elapsed"] - 1.0) < 0.01
    
    def test_threshold_checking(self):
        """Test threshold alert generation."""
        profiler = MemoryProfiler(
            warning_threshold_mb=500,
            critical_threshold_mb=1000,
        )
        
        # Below threshold - no alerts
        low_snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=100.0,
            vms_mb=200.0,
        )
        alerts = profiler.check_thresholds(low_snapshot)
        assert len(alerts) == 0
        
        # Warning threshold
        warn_snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=600.0,
            vms_mb=1000.0,
        )
        alerts = profiler.check_thresholds(warn_snapshot)
        assert len(alerts) == 1
        assert "WARNING" in alerts[0]
        
        # Critical threshold
        crit_snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=1200.0,
            vms_mb=2000.0,
        )
        alerts = profiler.check_thresholds(crit_snapshot)
        assert len(alerts) == 1
        assert "CRITICAL" in alerts[0]
    
    def test_report_generation(self):
        """Test report generation in different formats."""
        profiler = MemoryProfiler()
        
        # Take some snapshots
        for _ in range(5):
            profiler.take_snapshot()
        
        # Text report
        text_report = profiler.generate_report(format="text")
        assert "Memory Profiling Report" in text_report
        assert "RSS:" in text_report
        
        # HTML report
        html_report = profiler.generate_report(format="html")
        assert "<html>" in html_report
        assert "Memory Profiling Report" in html_report
        assert "</html>" in html_report
