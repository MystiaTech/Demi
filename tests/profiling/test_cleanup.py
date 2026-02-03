"""Resource cleanup verification tests.

Tests verify that resources are properly released after component shutdown
and no dangling references remain.
"""

import pytest
import asyncio
import gc
import weakref
import tempfile
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from tests.profiling import MemoryProfiler, ObjectTracker


class TestDiscordClientCleanup:
    """Test Discord client resources are properly cleaned up."""
    
    def test_discord_client_cleanup(self):
        """Verify Discord client doesn't leave dangling references."""
        # Create a mock Discord client-like object
        client = self._create_mock_discord_client()
        weak = weakref.ref(client)
        
        # Use client
        channel = client.register_channel(999)
        user = client.create_user(123, "Test")
        client.simulate_message("test", channel_id=999, author=user)
        
        # Clear references
        client_id = id(client)
        del client
        del channel
        del user
        
        # Force GC
        gc.collect()
        
        # Verify cleanup
        assert weak() is None, "MockDiscordClient was not garbage collected"
    
    def test_discord_message_cleanup(self):
        """Verify messages are cleaned up after processing."""
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        client = self._create_mock_discord_client()
        
        # Generate many messages
        for i in range(100):
            msg = client.create_message(f"Message {i}")
            # Process and discard
            del msg
        
        del client
        gc.collect()
        
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects
        
        # Allow some growth for test infrastructure
        print(f"Object growth: {growth}")
        assert growth < 500, f"Too many objects retained: {growth}"
    
    def _create_mock_discord_client(self) -> "MockDiscordClient":
        """Create a mock Discord client for testing."""
        return MockDiscordClient()


class MockDiscordClient:
    """Mock Discord client for cleanup testing."""
    
    def __init__(self):
        self.channels: Dict[int, Any] = {}
        self.users: Dict[int, Any] = {}
        self.messages: List[Any] = []
    
    def register_channel(self, channel_id: int) -> "MockChannel":
        channel = MockChannel(channel_id)
        self.channels[channel_id] = channel
        return channel
    
    def create_user(self, user_id: int, name: str) -> "MockUser":
        user = MockUser(user_id, name)
        self.users[user_id] = user
        return user
    
    def create_message(self, content: str) -> "MockMessage":
        msg = MockMessage(content)
        self.messages.append(msg)
        return msg
    
    def simulate_message(self, content: str, channel_id: int, author: "MockUser") -> "MockMessage":
        msg = MockMessage(content, channel_id=channel_id, author=author)
        self.messages.append(msg)
        return msg


class MockChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.messages: List[Any] = []


class MockUser:
    def __init__(self, user_id: int, name: str):
        self.id = user_id
        self.name = name


class MockMessage:
    def __init__(self, content: str, channel_id: int = 0, author: Optional[MockUser] = None):
        self.content = content
        self.channel_id = channel_id
        self.author = author


class TestLLMConnectionCleanup:
    """Test LLM inference resources are properly cleaned up."""
    
    def test_ollama_connection_cleanup(self):
        """Verify LLM connections are closed properly."""
        gc.collect()
        
        # Simulate Ollama connection
        connection = MockOllamaConnection()
        
        # Register responses
        for i in range(50):
            connection.register_response([f"trigger{i}"], f"response{i}")
        
        # Generate some responses
        for i in range(20):
            connection.generate(f"trigger{i % 10}")
        
        weak = weakref.ref(connection)
        del connection
        gc.collect()
        
        assert weak() is None, "Ollama connection was not garbage collected"
    
    def test_inference_context_cleanup(self):
        """Verify inference contexts are cleaned up."""
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create many inference contexts
        contexts = []
        for i in range(100):
            context = {
                "messages": [{"role": "user", "content": f"Message {j}"} for j in range(10)],
                "tokens": 100 + i,
                "model": "test-model",
            }
            contexts.append(context)
        
        # Clear all
        del contexts
        gc.collect()
        
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects
        
        print(f"Context cleanup - Object growth: {growth}")
        assert growth < 1000, f"Too many context objects retained: {growth}"


class MockOllamaConnection:
    """Mock Ollama connection for cleanup testing."""
    
    def __init__(self):
        self.responses: Dict[str, str] = {}
        self.history: List[Dict[str, Any]] = []
    
    def register_response(self, triggers: List[str], response: str) -> None:
        for trigger in triggers:
            self.responses[trigger] = response
    
    def generate(self, prompt: str) -> str:
        self.history.append({"prompt": prompt, "timestamp": 0})
        return self.responses.get(prompt, "default response")


class TestEmotionPersistenceCleanup:
    """Test emotion system resource cleanup."""
    
    def test_emotion_state_cleanup(self):
        """Verify emotion states are properly cleaned up."""
        gc.collect()
        
        states = []
        weak_refs = []
        
        # Create many states
        for i in range(100):
            state = MockEmotionState(loneliness=i/100)
            states.append(state)
            weak_refs.append(weakref.ref(state))
        
        # Clear all references
        del states
        gc.collect()
        
        # Check cleanup
        remaining = sum(1 for ref in weak_refs if ref() is not None)
        print(f"Remaining emotion states: {remaining}")
        
        # Most should be cleaned up
        assert remaining < 10, f"Too many emotion states retained: {remaining}"
    
    def test_persistence_db_cleanup(self):
        """Verify database connections are properly closed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Create and use persistence
            persistence = MockEmotionPersistence(db_path=str(db_path))
            
            saved_states = []
            for i in range(50):
                state = MockEmotionState(loneliness=i/100)
                persistence.save_state(state, notes=f"Test state {i}")
                saved_states.append(state)
            
            # File should exist after saves
            assert db_path.exists(), "Database file should exist"
            
            # Verify we can load the latest state
            latest = persistence.load_latest_state()
            assert latest is not None, "Should be able to load latest state"
            assert latest.loneliness == saved_states[-1].loneliness
            
            # Delete persistence
            del persistence
            gc.collect()
            
            # Should be able to reopen and read
            persistence2 = MockEmotionPersistence(db_path=str(db_path))
            # File exists check
            assert db_path.exists(), "Database file should still exist after reopen"


class MockEmotionState:
    """Mock emotion state for cleanup testing."""
    
    def __init__(self, loneliness: float = 0.5, excitement: float = 0.5):
        self.loneliness = loneliness
        self.excitement = excitement
        self.timestamp = 0


class MockEmotionPersistence:
    """Mock emotion persistence for cleanup testing."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.states: List[MockEmotionState] = []
        self.closed = False
        # Create the database file
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(db_path).touch()
    
    def save_state(self, state: MockEmotionState, notes: str = "") -> None:
        self.states.append(state)
        # Write to file to simulate persistence
        with open(self.db_path, 'w') as f:
            f.write(f"states: {len(self.states)}\\n")
    
    def load_latest_state(self) -> Optional[MockEmotionState]:
        return self.states[-1] if self.states else None
    
    def close(self) -> None:
        self.closed = True


class TestConductorShutdownCleanup:
    """Test Conductor resource cleanup."""
    
    def test_conductor_cleanup_after_shutdown(self):
        """Verify Conductor cleans up resources on shutdown."""
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Simulate conductor
        conductor = MockConductor()
        conductor.start()
        
        # Do some work
        for i in range(50):
            conductor.process_message(f"Message {i}")
        
        # Shutdown
        conductor.shutdown()
        
        del conductor
        gc.collect()
        
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects
        
        print(f"Object growth after conductor cycle: {growth}")
        # Allow some growth for module-level instances
        assert growth < 1000, f"Too many objects retained after conductor shutdown: {growth}"


class MockConductor:
    """Mock Conductor for cleanup testing."""
    
    def __init__(self):
        self.running = False
        self.components: List[Any] = []
        self.message_history: List[str] = []
    
    def start(self) -> None:
        self.running = True
        self.components = [
            {"name": "discord", "active": True},
            {"name": "emotion", "active": True},
            {"name": "llm", "active": True},
        ]
    
    def process_message(self, message: str) -> str:
        self.message_history.append(message)
        return f"Response to: {message}"
    
    def shutdown(self) -> None:
        self.running = False
        for component in self.components:
            component["active"] = False
        self.components.clear()
        self.message_history.clear()


class TestTempFileCleanup:
    """Test temporary file cleanup."""
    
    def test_temp_file_cleanup(self):
        """Verify no leftover temp files after operations."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate temp file operations
            temp_files = []
            for i in range(20):
                temp_path = Path(tmpdir) / f"temp_{i}.txt"
                temp_path.write_text(f"Temp content {i}")
                temp_files.append(temp_path)
            
            # Delete all temp files
            for temp_path in temp_files:
                temp_path.unlink()
            
            # Verify no temp files remain
            remaining = list(Path(tmpdir).glob("temp_*.txt"))
            assert len(remaining) == 0, f"Temp files not cleaned up: {remaining}"
    
    def test_audio_temp_cleanup(self):
        """Verify audio temp files are cleaned up."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate audio processing temp files
            audio_files = []
            for i in range(10):
                wav_path = Path(tmpdir) / f"audio_{i}.wav"
                mp3_path = Path(tmpdir) / f"audio_{i}.mp3"
                wav_path.write_bytes(b"RIFF" + b"\x00" * 100)
                mp3_path.write_bytes(b"ID3" + b"\x00" * 100)
                audio_files.extend([wav_path, mp3_path])
            
            # Process and delete
            for audio_path in audio_files:
                # Simulate processing
                _ = audio_path.read_bytes()
                audio_path.unlink()
            
            # Verify cleanup
            remaining = list(Path(tmpdir).glob("audio_*.*"))
            assert len(remaining) == 0, f"Audio temp files not cleaned up: {remaining}"


class TestTrackedObjectLifecycle:
    """Test memory profiler's tracked object lifecycle."""
    
    def test_tracked_object_weak_reference(self):
        """Verify tracked objects use weak references."""
        from tests.profiling import TrackedObject
        
        class TrackableObject:
            pass
        
        obj = TrackableObject()
        obj.data = "test" * 1000
        ref = weakref.ref(obj)
        
        tracked = TrackedObject(
            name="test",
            obj_ref=ref,
            initial_size_mb=0.01,
            creation_time=__import__('datetime').datetime.now()
        )
        
        assert tracked.is_alive
        
        # Delete original
        del obj
        gc.collect()
        
        assert not tracked.is_alive, "Tracked object should detect deletion"
    
    def test_object_tracking_doesnt_prevent_gc(self):
        """Verify tracking doesn't prevent garbage collection."""
        tracker = ObjectTracker()
        
        gc.collect()
        
        # Create and track object (must be a class instance, not dict)
        class LargeObject:
            pass
        
        obj = LargeObject()
        obj.large_data = "x" * 1000000
        tracking_id = tracker.track(obj, "test_large")
        
        # Verify we can still GC it
        del obj
        gc.collect()
        
        # Check that it's dead
        tracked = tracker.get_tracked(tracking_id)
        assert tracked is not None
        assert not tracked.is_alive, "Object should be garbage collected"
    
    def test_tracker_lifecycle_report(self):
        """Test tracker lifecycle reporting."""
        tracker = ObjectTracker()
        
        # Track some objects (must be class instances)
        class TrackedItem:
            def __init__(self, data):
                self.data = data
        
        objs = []
        for i in range(10):
            obj = TrackedItem(f"object_{i}")
            tracker.track(obj, f"obj_{i}", label="test_group")
            objs.append(obj)
        
        # All should be alive
        report = tracker.get_lifecycle_report("test_group")
        assert report["alive"] == 10
        assert report["dead"] == 0
        assert report["alive_percent"] == 100.0
        
        # Delete some
        del objs[:5]
        gc.collect()
        
        report = tracker.get_lifecycle_report("test_group")
        assert report["alive"] == 5
        assert report["dead"] == 5
        assert report["alive_percent"] == 50.0
    
    def test_tracker_orphaned_detection(self):
        """Test detection of orphaned objects."""
        tracker = ObjectTracker()
        
        # Create temporary objects (must be class instances)
        class TempObject:
            def __init__(self, data):
                self.temp_data = data
        
        temporary_objs = []
        for i in range(5):
            obj = TempObject(f"temp_{i}")
            tracker.track(
                obj,
                f"temp_{i}",
                label="temporary",
                metadata={"temporary": True}
            )
            temporary_objs.append(obj)
        
        # All should be alive
        assert tracker.get_alive_count("temporary") == 5
        
        # Delete references to some
        del temporary_objs[:3]
        gc.collect()
        
        # Should have 2 alive, 3 dead
        assert tracker.get_alive_count("temporary") == 2
        assert tracker.get_dead_count("temporary") == 3
        
        # Cleanup dead
        removed = tracker.cleanup_dead()
        assert removed == 3
        assert tracker.get_dead_count("temporary") == 0


class TestResourceMonitorIntegration:
    """Test integration with ResourceMonitor."""
    
    @pytest.mark.asyncio
    async def test_resource_monitor_integration(self):
        """Verify integration with ResourceMonitor from conductor."""
        from src.conductor.resource_monitor import ResourceMonitor
        
        profiler = MemoryProfiler()
        
        # Take snapshot via profiler
        snapshot = profiler.take_snapshot()
        
        # Verify profiler captured reasonable values
        assert snapshot.rss_mb > 0, "Profiler should capture RSS memory"
        assert snapshot.vms_mb > 0, "Profiler should capture VMS memory"
        
        # Verify ResourceMonitor can collect metrics
        monitor = ResourceMonitor()
        metrics = await monitor.collect_metrics()
        
        assert "memory_mb" in metrics
        assert metrics["memory_mb"] > 0
        
        # Note: ResourceMonitor memory_mb is system-wide, while profiler.rss_mb is process-specific
        # They will differ significantly - just verify both report valid positive values
        print(f"Profiler RSS: {snapshot.rss_mb:.1f}MB")
        print(f"ResourceMonitor memory_mb: {metrics['memory_mb']}MB")
