"""
Request routing and load balancing system for Demi's conductor.

Handles request distribution across platform integrations with:
- Content-based routing (Discord commands vs Android API calls)
- Load balancing across multiple plugin instances
- Dead letter queue for failed requests with exponential backoff
- Circuit breaker integration per platform
- Request timeout handling with fallback responses
- Response aggregation and formatting
- Comprehensive metrics for routing performance
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.conductor.metrics import get_metrics
from src.conductor.isolation import get_isolated_runner
from src.plugins.manager import PluginManager

logger = get_logger()


class RequestType(Enum):
    """Types of requests the router can handle."""

    DISCORD = "discord"
    ANDROID = "android"
    TWITCH = "twitch"
    MINECRAFT = "minecraft"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INTERNAL = "internal"


@dataclass
class DeadLetterQueueEntry:
    """Entry in the dead letter queue for retry logic."""

    request_id: str
    plugin_name: str
    request: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    last_attempt: datetime = field(default_factory=datetime.now)
    next_retry: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    def should_retry(self) -> bool:
        """Check if this request should be retried."""
        return self.retry_count < self.max_retries and datetime.now() >= self.next_retry

    def calculate_backoff(self):
        """Calculate exponential backoff for next retry."""
        # Exponential backoff: 1s, 2s, 4s, 8s
        backoff_seconds = min(2**self.retry_count, 30)
        self.next_retry = datetime.now() + timedelta(seconds=backoff_seconds)
        self.retry_count += 1


@dataclass
class RoutingDecision:
    """Result of routing analysis."""

    target_plugin: str
    request_type: RequestType
    is_valid: bool
    error: Optional[str] = None
    priority: int = 0  # Higher = more important
    timeout_seconds: int = 5


class RequestRouter:
    """
    Routes requests to appropriate platform integrations with load balancing and failure handling.
    """

    def __init__(self):
        """Initialize router with plugin manager and configuration."""
        self._config = DemiConfig.load()
        self._plugin_manager = PluginManager()
        self._isolated_runner = get_isolated_runner()

        # Load balancing state
        self._instance_load: Dict[str, int] = defaultdict(int)  # Plugin -> current load
        self._instance_weights: Dict[str, float] = {}  # Plugin -> weight for balancing

        # Dead letter queue
        self._dead_letter_queue: Dict[str, DeadLetterQueueEntry] = {}
        self._dlq_processor_task: Optional[asyncio.Task] = None

        # Routing statistics
        self._routing_stats = {
            "total_requests": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "dlq_entries": 0,
            "dlq_retries": 0,
            "dlq_failures": 0,
        }

        # Platform request counts (for load balancing)
        self._platform_request_counts: Dict[str, int] = defaultdict(int)
        self._platform_success_rates: Dict[str, float] = defaultdict(lambda: 1.0)

        logger.info("RequestRouter initialized")

    async def initialize(self):
        """Initialize router - discover and register plugins."""
        try:
            await self._plugin_manager.discover_and_register()
            logger.info(
                f"Router initialized with {len(self._plugin_manager.registry)} plugins"
            )

            # Start dead letter queue processor
            self._dlq_processor_task = asyncio.create_task(
                self._process_dead_letter_queue()
            )

        except Exception as e:
            logger.error(f"Router initialization failed: {str(e)}")
            raise

    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a request to the appropriate platform integration.

        Args:
            request: Request dict with 'type', 'content', and other parameters

        Returns:
            Response dict with 'status', 'result', and metadata
        """
        request_id = self._generate_request_id()
        start_time = time.time()

        try:
            # Analyze request and determine routing
            routing_decision = self.determine_route(request)

            if not routing_decision.is_valid:
                logger.error(
                    f"Request {request_id} routing failed: {routing_decision.error}"
                )
                return {
                    "status": "error",
                    "error": routing_decision.error,
                    "request_id": request_id,
                }

            # Route to target plugin
            plugin_name = routing_decision.target_plugin
            logger.debug(
                f"Request {request_id} routed to {plugin_name}",
                request_type=routing_decision.request_type.value,
            )

            # Execute request with isolation
            result = await self._execute_with_isolation(
                plugin_name, request, routing_decision.timeout_seconds
            )

            # Record routing statistics
            duration_ms = (time.time() - start_time) * 1000
            self._record_routing_success(plugin_name, duration_ms)

            # Update metrics
            metrics_reg = get_metrics()
            metrics = metrics_reg.get_counter("routing_requests_total")
            if metrics:
                metrics.labels(plugin=plugin_name, status="success").inc()

            return {
                "status": "success",
                "result": result,
                "request_id": request_id,
                "duration_ms": duration_ms,
                "plugin": plugin_name,
            }

        except asyncio.TimeoutError:
            logger.error(
                f"Request {request_id} timeout after {routing_decision.timeout_seconds}s"
            )

            # Add to dead letter queue for retry
            await self._add_to_dead_letter_queue(
                request_id, routing_decision.target_plugin, request
            )

            return {
                "status": "timeout",
                "error": f"Request timeout after {routing_decision.timeout_seconds}s",
                "request_id": request_id,
                "queued_for_retry": True,
            }

        except Exception as e:
            logger.error(f"Request {request_id} routing error: {str(e)}")

            # Add to dead letter queue for retry
            if "plugin_name" in locals():
                await self._add_to_dead_letter_queue(request_id, plugin_name, request)

            return {
                "status": "error",
                "error": str(e),
                "request_id": request_id,
                "queued_for_retry": True,
            }

    def determine_route(self, request: Dict[str, Any]) -> RoutingDecision:
        """Determine which plugin should handle this request."""
        request_type_str = request.get("type", "").lower()

        # Map request type to plugin
        routing_map = {
            "discord": "discord_platform",
            "android": "android_platform",
            "twitch": "twitch_platform",
            "minecraft": "minecraft_platform",
            "tiktok": "tiktok_platform",
            "youtube": "youtube_platform",
            "internal": "internal_platform",
        }

        plugin_name = routing_map.get(request_type_str)

        if not plugin_name:
            return RoutingDecision(
                target_plugin="",
                request_type=RequestType.INTERNAL,
                is_valid=False,
                error=f"Unknown request type: {request_type_str}",
            )

        # Check if plugin is loaded and healthy
        if plugin_name not in self._plugin_manager.registry:
            return RoutingDecision(
                target_plugin="",
                request_type=RequestType.INTERNAL,
                is_valid=False,
                error=f"Plugin not available: {plugin_name}",
            )

        # Determine request priority and timeout based on content
        priority = 0
        timeout = self._config.conductor.get("default_request_timeout", 5)

        if request_type_str == "discord":
            priority = 2  # Discord mention has higher priority
            timeout = 3
        elif request_type_str == "android":
            priority = 2
            timeout = 5
        elif request_type_str == "internal":
            priority = 3  # Internal requests are highest priority
            timeout = 10

        # Select load-balanced instance
        selected_plugin = self._select_balanced_instance(plugin_name)

        request_type_enum = (
            RequestType[request_type_str.upper()]
            if request_type_str.upper() in RequestType.__members__
            else RequestType.INTERNAL
        )

        return RoutingDecision(
            target_plugin=selected_plugin,
            request_type=request_type_enum,
            is_valid=True,
            priority=priority,
            timeout_seconds=timeout,
        )

    def _select_balanced_instance(self, plugin_name: str) -> str:
        """Select a plugin instance using round-robin load balancing."""
        # In current implementation, we have one instance per plugin
        # Future: support multiple instances and actual load balancing

        current_load = self._instance_load.get(plugin_name, 0)
        self._instance_load[plugin_name] = current_load + 1
        self._platform_request_counts[plugin_name] += 1

        return plugin_name

    async def _execute_with_isolation(
        self, plugin_name: str, request: Dict[str, Any], timeout_seconds: int
    ) -> Dict[str, Any]:
        """Execute request in isolated subprocess with timeout."""
        try:
            # Create task with timeout
            execution_task = asyncio.create_task(
                self._isolated_runner.execute_request(plugin_name, request)
            )

            # Wait with timeout
            result = await asyncio.wait_for(execution_task, timeout=timeout_seconds)

            if result.success:
                return result.output or {"status": "ok"}
            else:
                raise RuntimeError(f"Isolated execution failed: {result.error}")

        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"Request execution timeout: {timeout_seconds}s")

    async def _add_to_dead_letter_queue(
        self, request_id: str, plugin_name: str, request: Dict[str, Any]
    ):
        """Add failed request to dead letter queue for retry."""
        entry = DeadLetterQueueEntry(
            request_id=request_id,
            plugin_name=plugin_name,
            request=request,
            max_retries=self._config.conductor.get("dlq_max_retries", 3),
        )

        self._dead_letter_queue[request_id] = entry
        self._routing_stats["dlq_entries"] += 1

        logger.info(
            f"Request {request_id} added to DLQ for plugin {plugin_name}",
            dlq_size=len(self._dead_letter_queue),
        )

        # Update metrics
        metrics_reg = get_metrics()
        metrics = metrics_reg.get_gauge("routing_dlq_size")
        if metrics:
            metrics.set(len(self._dead_letter_queue))

    async def _process_dead_letter_queue(self):
        """Process dead letter queue, retrying failed requests with exponential backoff."""
        logger.info("Dead letter queue processor started")

        while True:
            try:
                await asyncio.sleep(5)  # Check DLQ every 5 seconds

                # Find entries ready for retry
                ready_for_retry = [
                    entry
                    for entry in self._dead_letter_queue.values()
                    if entry.should_retry()
                ]

                if not ready_for_retry:
                    continue

                logger.info(f"Processing {len(ready_for_retry)} DLQ entries")

                for entry in ready_for_retry:
                    try:
                        # Retry the request
                        result = await self._execute_with_isolation(
                            entry.plugin_name, entry.request, timeout_seconds=5
                        )

                        # Success - remove from DLQ
                        del self._dead_letter_queue[entry.request_id]
                        self._routing_stats["dlq_retries"] += 1

                        logger.info(
                            f"DLQ retry successful for {entry.request_id}",
                            plugin=entry.plugin_name,
                        )

                    except Exception as e:
                        # Calculate backoff and retry
                        entry.error = str(e)
                        entry.calculate_backoff()

                        logger.warning(
                            f"DLQ retry attempt {entry.retry_count} for {entry.request_id}",
                            plugin=entry.plugin_name,
                            next_retry_in_seconds=(
                                entry.next_retry - datetime.now()
                            ).total_seconds(),
                        )

                        # If max retries exceeded, permanently fail
                        if entry.retry_count >= entry.max_retries:
                            logger.error(
                                f"DLQ entry {entry.request_id} exhausted retries, removing",
                                plugin=entry.plugin_name,
                            )
                            del self._dead_letter_queue[entry.request_id]
                            self._routing_stats["dlq_failures"] += 1

            except asyncio.CancelledError:
                logger.info("Dead letter queue processor shutting down")
                break

            except Exception as e:
                logger.error(f"Error in DLQ processor: {str(e)}")
                await asyncio.sleep(5)  # Backoff on error

    def _record_routing_success(self, plugin_name: str, duration_ms: float):
        """Record successful routing statistics."""
        self._routing_stats["successful_routes"] += 1
        self._routing_stats["total_requests"] += 1

        # Update success rate
        total = self._routing_stats["total_requests"]
        success_rate = (
            self._routing_stats["successful_routes"] / total if total > 0 else 1.0
        )

        self._platform_success_rates[plugin_name] = success_rate

        # Update metrics
        metrics_reg = get_metrics()
        metrics = metrics_reg.get_histogram("routing_latency_seconds")
        if metrics:
            metrics.labels(plugin=plugin_name).observe(duration_ms / 1000)

    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        import uuid

        return str(uuid.uuid4())[:8]

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get current routing statistics."""
        return {
            **self._routing_stats,
            "dlq_pending": len(self._dead_letter_queue),
            "platform_success_rates": dict(self._platform_success_rates),
            "platform_request_counts": dict(self._platform_request_counts),
        }

    async def shutdown(self):
        """Shutdown router, cleaning up resources."""
        logger.info("Shutting down RequestRouter")

        # Cancel DLQ processor
        if self._dlq_processor_task:
            self._dlq_processor_task.cancel()
            try:
                await self._dlq_processor_task
            except asyncio.CancelledError:
                pass

        # Shutdown isolated runner
        await self._isolated_runner.shutdown()

        logger.info(
            f"RequestRouter shutdown complete, final DLQ size: {len(self._dead_letter_queue)}"
        )
