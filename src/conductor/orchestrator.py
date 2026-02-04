"""
Main conductor orchestrator for Demi.

Coordinates all subsystems into a cohesive system:
- Plugin lifecycle management
- Health monitoring
- Resource auto-scaling
- Request routing
- Graceful startup/shutdown

This is the central nervous system that brings all components together.
"""

import asyncio
import signal
import time
import webbrowser
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.core.database import DatabaseManager
from src.plugins.manager import PluginManager
from src.conductor.health import get_health_monitor, HealthMonitor, HealthStatus
from src.conductor.scaler import PredictiveScaler
from src.conductor.router import RequestRouter
from src.conductor.metrics import get_metrics
from src.conductor.circuit_breaker import get_circuit_breaker_manager
from src.llm import (
    OllamaInference,
    LLMConfig,
    InferenceError,
    CodebaseReader,
    PromptBuilder,
    ConversationHistory,
    ResponseProcessor,
)
from src.emotion.persistence import EmotionPersistence
from src.emotion.modulation import PersonalityModulator
from src.emotion.interactions import InteractionHandler
from src.monitoring.dashboard_server import DashboardServer
from src.mobile.api import MobileAPIServer

logger = get_logger()


@dataclass
class SystemStatus:
    """Overall system health status."""

    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    component_statuses: Dict[str, str] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    active_plugins: int = 0
    total_requests: int = 0
    failed_requests: int = 0


class Conductor:
    """
    Main orchestrator managing all Demi subsystems.

    Coordinates:
    - Plugin lifecycle (discovery, loading, unloading)
    - Health monitoring (platform health, resource usage)
    - Auto-scaling (predictive resource management)
    - Request routing (content-based, load balancing)
    - Graceful shutdown (cleanup, resource release)
    """

    def __init__(self, config: Optional[DemiConfig] = None):
        """
        Initialize conductor with all subsystems.

        Args:
            config: Configuration object, loads default if None
        """
        self._config = config or DemiConfig.load()
        self._logger = logger

        # Initialize subsystems
        self._plugin_manager = PluginManager()
        self._health_monitor = get_health_monitor()
        self._scaler = PredictiveScaler()
        self._router = RequestRouter()
        self._metrics = get_metrics()
        self._circuit_breaker_manager = get_circuit_breaker_manager()

        # Database
        self._db_manager = DatabaseManager(self._config)

        # Codebase reader for self-awareness
        self.codebase_reader = CodebaseReader(logger=self._logger)

        # LLM inference engine with codebase context
        self.llm = OllamaInference(
            config=LLMConfig.from_global_config(self._config),
            logger=self._logger,
            codebase_reader=self.codebase_reader,
        )
        self.llm_available = False

        # Emotion and personality systems
        self.emotion_persistence = EmotionPersistence(
            db_manager=self._db_manager, logger=self._logger
        )
        self.personality_modulator = PersonalityModulator(logger=self._logger)

        # Prompt builder with codebase context
        self.prompt_builder = PromptBuilder(
            logger=self._logger,
            token_counter=self.llm._count_tokens,
            codebase_reader=self.codebase_reader,
        )

        # Conversation history manager
        self.conversation_history = ConversationHistory(logger=self._logger)

        # Response processor
        db_session = self._db_manager.get_session()
        interaction_handler = InteractionHandler()
        self.response_processor = ResponseProcessor(
            logger=self._logger,
            db_session=db_session,
            interaction_handler=interaction_handler,
        )

        # Autonomy coordinator (initialized after other systems are ready)
        self.autonomy_coordinator = None

        # Dashboard server (initialized if enabled)
        self._dashboard: Optional[DashboardServer] = None

        # Mobile API server (initialized if enabled)
        self._mobile_api: Optional[MobileAPIServer] = None

        # State tracking
        self._running = False
        self._startup_time: Optional[float] = None
        self._shutdown_event = asyncio.Event()
        self._background_tasks: List[asyncio.Task] = []
        self._request_count = 0
        self._failed_request_count = 0
        self._inference_latency_sec: float = 0.0

        # Signal handlers
        self._signal_handlers_registered = False

        self._logger.info("conductor_initialized", config_path="defaults.yaml")

    async def startup(self) -> bool:
        """
        Execute full startup sequence in correct order.

        Sequence:
        1. Load configuration and initialize logging
        2. Initialize database connection and run migrations
        3. Discover and register plugins
        4. Start health monitoring loop
        5. Initialize predictive scaler
        6. Start request router
        7. Enable all registered plugins
        8. Register signal handlers for graceful shutdown

        Returns:
            True if startup successful, False otherwise
        """
        try:
            self._startup_time = time.time()
            self._logger.info("=" * 60)
            self._logger.info("CONDUCTOR STARTUP SEQUENCE INITIATED")
            self._logger.info("=" * 60)

            # Step 1: Configuration and logging (already done in __init__)
            self._logger.info("Configuration loaded")

            # Step 2: Database initialization
            self._logger.info("Initializing database...")
            try:
                # Initialize database tables
                self._db_manager.create_tables()
                self._logger.info("Database initialized")
            except Exception as e:
                self._logger.error(f"database_initialization_failed: {str(e)}")
                return False

            # Step 3: Plugin discovery and registration
            self._logger.info("Discovering plugins...")
            try:
                await self._plugin_manager.discover_and_register()
                plugin_count = len(self._plugin_manager.registry)
                self._logger.info(f"Plugin discovery complete: {plugin_count} plugins")
            except Exception as e:
                self._logger.error(f"plugin_discovery_failed: {str(e)}")
                return False

            # Step 4: Start health monitoring loop
            self._logger.info("Starting health monitor...")
            try:
                platforms = [p.name for p in self._plugin_manager.list_plugins()]
                health_task = asyncio.create_task(
                    self._health_monitor.health_check_loop(
                        platforms, health_check_fn=None
                    )
                )
                self._background_tasks.append(health_task)
                self._logger.info("Health monitor started")
            except Exception as e:
                self._logger.error(f"health_monitor_startup_failed: {str(e)}")
                return False

            # Step 4.5: Initialize LLM and check Ollama health
            self._logger.info("Checking LLM (Ollama) availability...")
            ollama_url = self._config.lm.get("ollama", {}).get("base_url", "http://localhost:11434")
            try:
                llm_health = await self.llm.health_check()
                if llm_health:
                    self.llm_available = True
                    self._logger.info(f"✅ LLM: Ollama online at {ollama_url}")
                    print(f"✅ Ollama is reachable at {ollama_url}")
                else:
                    self.llm_available = False
                    self._logger.warning(
                        f"❌ LLM: Ollama not responding at {ollama_url}\n"
                        f"   Make sure Ollama is running and accessible.\n"
                        f"   Set OLLAMA_BASE_URL environment variable if using different address."
                    )
                    print(f"\n{'='*70}")
                    print(f"❌ OLLAMA NOT REACHABLE")
                    print(f"   URL: {ollama_url}")
                    print(f"   Demi can respond but WITHOUT intelligence (fallback mode)")
                    print(f"   To fix:")
                    print(f"   1. Start Ollama: ollama serve")
                    print(f"   2. For Windows: Set OLLAMA_HOST=0.0.0.0:11434")
                    print(f"   3. Update .env if using different IP/port")
                    print(f"{'='*70}\n")
            except Exception as e:
                self.llm_available = False
                self._logger.warning(f"LLM health check error: {str(e)}")
                print(f"\n{'='*70}")
                print(f"❌ OLLAMA CONNECTION ERROR")
                print(f"   URL: {ollama_url}")
                print(f"   Error: {str(e)}")
                print(f"   Demi can respond but WITHOUT intelligence (fallback mode)")
                print(f"{'='*70}\n")

            # Step 5: Initialize predictive scaler
            self._logger.info("Initializing scaler...")
            try:
                # Scaler is stateless and operates on-demand during health checks
                self._logger.info("Scaler initialized")
            except Exception as e:
                self._logger.error(f"scaler_initialization_failed: {str(e)}")
                return False

            # Step 6: Start request router
            self._logger.info("Starting request router...")
            try:
                # Router is stateless, just initialize it
                self._logger.info("Request router ready")
            except Exception as e:
                self._logger.error(f"router_startup_failed: {str(e)}")
                return False

            # Step 7: Enable registered plugins
            self._logger.info("Loading plugins...")
            try:
                loaded_count = 0
                for metadata in self._plugin_manager.list_plugins():
                    try:
                        plugin = await self._plugin_manager.load_plugin(metadata.name)
                        if plugin:
                            loaded_count += 1
                            self._logger.info(f"Plugin loaded: {metadata.name}")

                            # Special setup for Discord plugin
                            if metadata.name == "discord" and hasattr(plugin, "setup"):
                                self._logger.info("Setting up Discord plugin with conductor...")
                                try:
                                    plugin.setup(self)
                                    self._logger.info("Discord plugin setup complete")
                                except Exception as e:
                                    self._logger.warning(f"Discord plugin setup failed: {str(e)}")
                    except Exception as e:
                        self._logger.warning(
                            f"plugin_load_failed {metadata.name}: {str(e)}"
                        )
                        # Continue with other plugins even if one fails
                        continue

                self._logger.info(f"Plugins loaded: {loaded_count}")
            except Exception as e:
                self._logger.error(f"plugin_loading_failed: {str(e)}")
                return False

            # Step 8: Initialize autonomy system
            self._logger.info("Initializing autonomy system...")
            try:
                if not await self._start_autonomy_system():
                    return False
                self._logger.info("Autonomy system initialized")
            except Exception as e:
                self._logger.error(f"autonomy_system_initialization_failed: {str(e)}")
                return False

            # Step 8.5: Start dashboard server (if enabled)
            if self._config.dashboard.get("enabled", True):
                self._logger.info("Starting dashboard server...")
                try:
                    if not await self._start_dashboard_server():
                        self._logger.warning("Dashboard server failed to start, continuing without it")
                    else:
                        self._logger.info("Dashboard server started")
                except Exception as e:
                    self._logger.warning(f"dashboard_server_startup_failed: {str(e)}")

            # Step 8.6: Start mobile API server (if enabled)
            if self._config.mobile.get("enabled", True):
                self._logger.info("Starting mobile API server...")
                try:
                    if not await self._start_mobile_api():
                        self._logger.warning("Mobile API server failed to start, continuing without it")
                    else:
                        self._logger.info("Mobile API server started")
                except Exception as e:
                    self._logger.warning(f"mobile_api_server_startup_failed: {str(e)}")

            # Step 9: Register signal handlers
            self._logger.info("Registering signal handlers...")
            try:
                self._register_signal_handlers()
                self._logger.info("Signal handlers registered")
            except Exception as e:
                self._logger.error(f"signal_handler_registration_failed: {str(e)}")
                return False

            self._running = True
            startup_time_sec = time.time() - self._startup_time
            self._logger.info("=" * 60)
            self._logger.info(f"✓ CONDUCTOR STARTUP COMPLETE ({startup_time_sec:.2f}s)")
            self._logger.info("=" * 60)

            return True

        except Exception as e:
            self._logger.exception(f"conductor_startup_failed: {str(e)}")
            return False

            # Step 3: Plugin discovery and registration
            self._logger.info("step_3_start", message="Discovering plugins...")
            try:
                await self._plugin_manager.discover_and_register()
                plugin_count = len(self._plugin_manager.registry)
                self._logger.info("step_3_complete", plugins_discovered=plugin_count)
            except Exception as e:
                self._logger.error("plugin_discovery_failed", error=str(e))
                return False

            # Step 4: Start health monitoring loop
            self._logger.info("step_4_start", message="Starting health monitor...")
            try:
                platforms = [p.name for p in self._plugin_manager.list_plugins()]
                health_task = asyncio.create_task(
                    self._health_monitor.health_check_loop(
                        platforms, health_check_fn=None
                    )
                )
                self._background_tasks.append(health_task)
                self._logger.info("step_4_complete", message="Health monitor started")
            except Exception as e:
                self._logger.error("health_monitor_startup_failed", error=str(e))
                return False

            # Step 5: Initialize predictive scaler
            self._logger.info("step_5_start", message="Initializing scaler...")
            try:
                scaler_task = asyncio.create_task(
                    self._scaler.scaling_loop(
                        self._plugin_manager, self._config.conductor
                    )
                )
                self._background_tasks.append(scaler_task)
                self._logger.info("step_5_complete", message="Scaler initialized")
            except Exception as e:
                self._logger.error("scaler_initialization_failed", error=str(e))
                return False

            # Step 6: Start request router
            self._logger.info("step_6_start", message="Starting request router...")
            try:
                # Router is stateless, just initialize it
                self._logger.info("step_6_complete", message="Request router ready")
            except Exception as e:
                self._logger.error("router_startup_failed", error=str(e))
                return False

            # Step 7: Enable registered plugins
            self._logger.info("step_7_start", message="Loading plugins...")
            try:
                loaded_count = 0
                for metadata in self._plugin_manager.list_plugins():
                    try:
                        plugin = await self._plugin_manager.load_plugin(metadata.name)
                        if plugin:
                            loaded_count += 1
                            self._logger.info(f"plugin_loaded", name=metadata.name)
                    except Exception as e:
                        self._logger.warning(
                            f"plugin_load_failed", name=metadata.name, error=str(e)
                        )
                        # Continue with other plugins even if one fails
                        continue

                self._logger.info("step_7_complete", plugins_loaded=loaded_count)
            except Exception as e:
                self._logger.error("plugin_loading_failed", error=str(e))
                return False

            # Step 8: Register signal handlers
            self._logger.info("step_8_start", message="Registering signal handlers...")
            try:
                self._register_signal_handlers()
                self._logger.info(
                    "step_8_complete", message="Signal handlers registered"
                )
            except Exception as e:
                self._logger.error("signal_handler_registration_failed", error=str(e))
                return False

            self._running = True
            startup_time_sec = time.time() - self._startup_time
            self._logger.info("=" * 60)
            self._logger.info(f"✓ CONDUCTOR STARTUP COMPLETE ({startup_time_sec:.2f}s)")
            self._logger.info("=" * 60)

            return True

        except Exception as e:
            self._logger.error("conductor_startup_failed", error=str(e), exc_info=True)
            return False

    async def request_inference(self, messages: List[Dict[str, str]]) -> str:
        """
        Request inference from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Response text from LLM, or fallback message if unavailable
        """
        if not self.llm_available:
            self._logger.warning("LLM inference requested but Ollama unavailable")
            return "I'm not ready to talk right now... wait a sec?"

        try:
            # Record start time for latency tracking
            start_time = time.time()

            # Call inference
            response = await self.llm.chat(messages)

            # Record latency
            latency = time.time() - start_time
            self._inference_latency_sec = latency
            self._logger.debug(f"Inference latency: {latency:.2f}s")

            return response

        except InferenceError as e:
            self._logger.error(f"Inference error: {str(e)}")
            return "I'm not ready to talk right now... wait a sec?"
        except Exception as e:
            self._logger.exception(f"Unexpected error during inference: {str(e)}")
            return "I'm not ready to talk right now... wait a sec?"

    async def request_inference_for_platform(
        self,
        platform: str,
        user_id: str,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Request inference from LLM for platform-specific message.
        This method handles the full pipeline including emotion state and processing.

        Args:
            platform: Platform identifier (e.g., "android", "discord")
            user_id: User identifier for emotion state lookup
            content: User's message content
            context: Additional context dict

        Returns:
            Response dict with content, emotion_state, and metadata
        """
        if not self.llm_available:
            self._logger.warning("LLM inference requested but Ollama unavailable")
            return {
                "content": "I'm not ready to talk right now... wait a sec?",
                "emotion_state": {},
                "platform": platform,
                "error": "LLM unavailable",
            }

        try:
            # Load user's emotional state
            emotion_state = await self.emotion_persistence.load_state(user_id)

            # Build conversation history with current message
            messages = [{"role": "user", "content": content}]

            # Add system prompt with emotion state
            system_prompt = self.prompt_builder.build(
                emotional_state=emotion_state, codebase_reader=self.codebase_reader
            )

            # Prepend system prompt to messages
            messages.insert(0, {"role": "system", "content": system_prompt})

            # Call inference with emotion state
            response_content = await self.llm.chat(
                messages=messages, emotional_state_before=emotion_state.to_dict()
            )

            # Process response and update emotions
            if hasattr(self.llm, "response_processor") and self.llm.response_processor:
                processed = self.llm.response_processor.process_response(
                    response=response_content,
                    emotional_state_before=emotion_state,
                    user_message=content,
                )
                emotion_state_after = processed.emotional_state_after
                response_content = processed.cleaned_text
            else:
                # Fallback: just get default emotion state
                emotion_state_after = emotion_state.to_dict()

            # Persist updated emotion state
            await self.emotion_persistence.save_state(user_id, emotion_state)

            return {
                "content": response_content,
                "emotion_state": emotion_state_after,
                "platform": platform,
                "context": context or {},
            }

        except Exception as e:
            self._logger.exception(f"Error during platform inference: {str(e)}")
            return {
                "content": "I'm having trouble thinking right now... can you try again?",
                "emotion_state": emotion_state.to_dict()
                if "emotion_state" in locals()
                else {},
                "platform": platform,
                "error": str(e),
            }

    async def shutdown(self) -> None:
        """
        Execute graceful shutdown sequence in reverse order.

        Sequence:
        1. Stop accepting new requests
        2. Disable all plugins
        3. Stop background loops (health, scaling)
        4. Close database connections
        5. Cleanup remaining resources
        """
        try:
            self._logger.info("=" * 60)
            self._logger.info("CONDUCTOR SHUTDOWN SEQUENCE INITIATED")
            self._logger.info("=" * 60)

            # Step 1: Stop accepting new requests
            self._logger.info("Stopping request acceptance...")
            self._running = False
            self._logger.info("Request acceptance stopped")

            # Step 2: Disable all plugins
            self._logger.info("Disabling plugins...")
            try:
                await self._plugin_manager.shutdown_all()
                self._logger.info("All plugins disabled")
            except Exception as e:
                self._logger.error(f"plugin_shutdown_failed: {str(e)}")

            # Step 3: Stop autonomy system
            self._logger.info("Stopping autonomy system...")
            try:
                await self._stop_autonomy_system()
            except Exception as e:
                self._logger.error(f"autonomy_system_shutdown_failed: {str(e)}")

            # Step 3.5: Stop dashboard server
            self._logger.info("Stopping dashboard server...")
            try:
                await self._stop_dashboard_server()
            except Exception as e:
                self._logger.error(f"dashboard_server_shutdown_failed: {str(e)}")

            # Step 3.6: Stop mobile API server
            self._logger.info("Stopping mobile API server...")
            try:
                await self._stop_mobile_api()
            except Exception as e:
                self._logger.error(f"mobile_api_server_shutdown_failed: {str(e)}")

            # Step 4: Stop background loops
            self._logger.info("Stopping background tasks...")
            try:
                self._health_monitor.stop()

                # Cancel all background tasks
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()

                # Wait for tasks to complete
                if self._background_tasks:
                    await asyncio.gather(
                        *self._background_tasks, return_exceptions=True
                    )

                self._logger.info("Background tasks stopped")
            except Exception as e:
                self._logger.error(f"background_task_shutdown_failed: {str(e)}")

            # Step 4: Close database connections
            self._logger.info("Closing database...")
            try:
                self._db_manager.close()
                self._logger.info("Database closed")
            except Exception as e:
                self._logger.error(f"database_shutdown_failed: {str(e)}")

            # Step 5: Record final metrics
            self._logger.info("Recording final metrics...")
            try:
                # Final metrics recording happens automatically
                self._logger.info("Final metrics recorded")
            except Exception as e:
                self._logger.error(f"metrics_recording_failed: {str(e)}")

            self._logger.info("=" * 60)
            self._logger.info("✓ CONDUCTOR SHUTDOWN COMPLETE")
            self._logger.info("=" * 60)

        except Exception as e:
            self._logger.exception(f"conductor_shutdown_failed: {str(e)}")

    def _register_signal_handlers(self) -> None:
        """Register handlers for SIGINT and SIGTERM for graceful shutdown."""
        if self._signal_handlers_registered:
            return

        def handle_signal(signum, frame):
            self._logger.info(f"signal_received", signal=signum)
            asyncio.create_task(self.shutdown())

        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
            self._signal_handlers_registered = True
        except Exception as e:
            self._logger.warning("signal_handler_registration_failed", error=str(e))

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for external requests.

        Routes request through:
        1. Request router (content-based routing)
        2. Plugin execution (isolated subprocess)
        3. Response aggregation

        Args:
            request: Request dictionary with platform, action, args

        Returns:
            Response dictionary with status, data, metrics
        """
        if not self._running:
            return {
                "status": "error",
                "error": "Conductor not running",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            self._request_count += 1
            request_start = time.time()

            # Route the request
            response = await self._router.route_request(request)

            if response.get("status") == "error":
                self._failed_request_count += 1

            # Add metrics
            response["conductor_metrics"] = {
                "total_requests": self._request_count,
                "failed_requests": self._failed_request_count,
                "processing_time_ms": (time.time() - request_start) * 1000,
                "uptime_seconds": time.time() - (self._startup_time or time.time()),
            }

            return response

        except Exception as e:
            self._failed_request_count += 1
            self._logger.error("request_handling_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_status(self) -> SystemStatus:
        """
        Get overall system health and status.

        Returns:
            SystemStatus with component statuses and metrics
        """
        try:
            # Get component statuses
            health_results = self._health_monitor.get_all_statuses()
            component_statuses = {
                name: result.status.value for name, result in health_results.items()
            }

            # Get resource metrics
            resource_metrics = self._health_monitor.get_resource_metrics()
            resource_usage = {}
            if resource_metrics:
                resource_usage = {
                    "ram_percent": resource_metrics.ram_percent,
                    "cpu_percent": resource_metrics.cpu_percent,
                    "disk_percent": resource_metrics.disk_percent,
                }

            # Count active plugins
            active_plugins = sum(
                1 for p in self._plugin_manager.list_plugins() if p.is_loaded()
            )

            # Add autonomy system status
            if self.autonomy_coordinator:
                autonomy_status = self.autonomy_coordinator.get_autonomy_status()
                component_statuses["autonomy"] = (
                    "healthy" if autonomy_status.active else "inactive"
                )
                resource_usage["autonomy_tasks"] = autonomy_status.tasks_running

            # Determine overall status
            if not component_statuses:
                overall_status = "initializing"
            elif all(s == "healthy" for s in component_statuses.values()):
                overall_status = "healthy"
            elif any(s == "unhealthy" for s in component_statuses.values()):
                overall_status = "unhealthy"
            else:
                overall_status = "degraded"

            # Add degraded flag from health monitor
            if self._health_monitor.is_degraded():
                overall_status = "degraded"

            uptime = time.time() - self._startup_time if self._startup_time else 0

            return SystemStatus(
                status=overall_status,
                uptime_seconds=uptime,
                component_statuses=component_statuses,
                resource_usage=resource_usage,
                active_plugins=active_plugins,
                total_requests=self._request_count,
                failed_requests=self._failed_request_count,
            )

        except Exception as e:
            self._logger.error("get_status_failed", error=str(e))
            return SystemStatus(
                status="error",
                uptime_seconds=0,
                component_statuses={"error": str(e)},
            )

    def is_running(self) -> bool:
        """Check if conductor is running."""
        return self._running

    def get_request_count(self) -> int:
        """Get total request count."""
        return self._request_count

    def get_failed_request_count(self) -> int:
        """Get failed request count."""
        return self._failed_request_count

    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        if self._startup_time is None:
            return 0
        return time.time() - self._startup_time

    async def _start_autonomy_system(self) -> bool:
        """
        Start the unified autonomy system.

        Returns:
            True if autonomy system started successfully
        """
        try:
            from src.autonomy.coordinator import AutonomyCoordinator

            # Initialize autonomy coordinator
            self.autonomy_coordinator = AutonomyCoordinator(
                conductor=self, logger=self._logger
            )

            # Start autonomy background tasks
            if self.autonomy_coordinator.start_autonomy():
                self._logger.info("Autonomy system started successfully")
                return True
            else:
                self._logger.error("Failed to start autonomy system")
                return False

        except Exception as e:
            self._logger.error(f"Error starting autonomy system: {e}")
            return False

    async def _stop_autonomy_system(self) -> None:
        """Stop the unified autonomy system."""
        try:
            if self.autonomy_coordinator:
                if self.autonomy_coordinator.stop_autonomy():
                    self._logger.info("Autonomy system stopped successfully")
                else:
                    self._logger.warning("Failed to stop autonomy system gracefully")
        except Exception as e:
            self._logger.error(f"Error stopping autonomy system: {e}")

    async def _start_dashboard_server(self) -> bool:
        """
        Start the dashboard server.

        Returns:
            True if dashboard started successfully
        """
        try:
            dashboard_config = self._config.dashboard
            host = dashboard_config.get("host", "0.0.0.0")
            port = dashboard_config.get("port", 8080)
            update_interval = dashboard_config.get("update_interval_sec", 5)

            # Initialize dashboard server
            self._dashboard = DashboardServer(
                host=host,
                port=port,
                update_interval=update_interval,
            )

            self._logger.info(
                f"Dashboard server initialized on {host}:{port} "
                f"(update interval: {update_interval}s)"
            )

            # Start dashboard server as background task
            dashboard_task = asyncio.create_task(self._dashboard.start())
            self._background_tasks.append(dashboard_task)

            # Give the server a moment to start
            await asyncio.sleep(0.5)

            # Launch browser if configured
            if dashboard_config.get("auto_launch_browser", True):
                self._launch_dashboard_browser(host, port)

            self._logger.info(f"Dashboard server started successfully")
            return True
        except Exception as e:
            self._logger.error(f"Failed to start dashboard server: {e}")
            return False

    def _launch_dashboard_browser(self, host: str, port: int) -> None:
        """
        Launch dashboard in default browser in a separate thread.

        Args:
            host: Dashboard host
            port: Dashboard port
        """
        def open_browser():
            try:
                # Convert 0.0.0.0 to localhost for browser access
                browser_host = "localhost" if host == "0.0.0.0" else host
                url = f"http://{browser_host}:{port}"
                self._logger.info(f"Opening dashboard in browser: {url}")
                webbrowser.open(url)
            except Exception as e:
                self._logger.warning(f"Failed to open browser: {e}")
                self._logger.info(
                    f"Access dashboard manually at "
                    f"http://{'localhost' if host == '0.0.0.0' else host}:{port}"
                )

        # Launch browser in separate thread to avoid blocking
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

    async def _stop_dashboard_server(self) -> None:
        """Stop the dashboard server."""
        try:
            if self._dashboard:
                self._logger.info("Stopping dashboard server...")
                await self._dashboard.stop()
                self._dashboard = None
                self._logger.info("Dashboard server stopped")
        except Exception as e:
            self._logger.error(f"Error stopping dashboard server: {e}")

    async def _start_mobile_api(self) -> bool:
        """
        Start the mobile API server.

        Returns:
            True if mobile API started successfully
        """
        try:
            mobile_config = self._config.mobile
            host = mobile_config.get("host", "0.0.0.0")
            port = mobile_config.get("port", 8081)

            # Initialize mobile API server
            self._mobile_api = MobileAPIServer(host=host, port=port)

            self._logger.info(f"Mobile API server initialized on {host}:{port}")

            # Start mobile API server as background task
            mobile_task = asyncio.create_task(self._mobile_api.start(self))
            self._background_tasks.append(mobile_task)

            # Give the server a moment to start
            await asyncio.sleep(0.5)

            self._logger.info("Mobile API server started successfully")
            return True
        except Exception as e:
            self._logger.error(f"Failed to start mobile API server: {e}")
            return False

    async def _stop_mobile_api(self) -> None:
        """Stop the mobile API server."""
        try:
            if self._mobile_api:
                self._logger.info("Stopping mobile API server...")
                await self._mobile_api.stop()
                self._mobile_api = None
                self._logger.info("Mobile API server stopped")
        except Exception as e:
            self._logger.error(f"Error stopping mobile API server: {e}")

    def send_discord_message(self, content: str, channel_id: str) -> bool:
        """
        Send message through Discord platform.

        Args:
            content: Message content to send
            channel_id: Discord channel ID

        Returns:
            True if message sent successfully
        """
        try:
            # Get Discord plugin from plugin manager
            discord_plugin = self._plugin_manager.get_loaded_plugin("discord")
            if discord_plugin and hasattr(discord_plugin, "send_message"):
                return discord_plugin.send_message(content, channel_id)
            return False
        except Exception as e:
            self._logger.error(f"Failed to send Discord message: {e}")
            return False

    def send_android_websocket_message(self, content: str, device_id: str) -> bool:
        """
        Send message through Android WebSocket platform.

        Args:
            content: Message content to send
            device_id: Android device ID

        Returns:
            True if message sent successfully
        """
        try:
            # Get Android plugin from plugin manager
            android_plugin = self._plugin_manager.get_loaded_plugin("android")
            if android_plugin and hasattr(android_plugin, "send_websocket_message"):
                return android_plugin.send_websocket_message(content, device_id)
            return False
        except Exception as e:
            self._logger.error(f"Failed to send Android WebSocket message: {e}")
            return False


# Global conductor instance
_conductor_instance: Optional[Conductor] = None


def get_conductor(config: Optional[DemiConfig] = None) -> Conductor:
    """Get or create global conductor instance."""
    global _conductor_instance
    if _conductor_instance is None:
        _conductor_instance = Conductor(config)
    return _conductor_instance


def get_conductor_instance() -> Conductor:
    """Get existing global conductor instance."""
    global _conductor_instance
    if _conductor_instance is None:
        raise RuntimeError("Conductor not initialized. Call get_conductor() first.")
    return _conductor_instance
