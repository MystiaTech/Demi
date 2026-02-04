"""
AutonomyCoordinator for unified autonomous behavior management.

Coordinates with Conductor for LLM access and platform integration.
Manages emotional triggers, background tasks, and refusal system integration.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field

from src.core.logger import DemiLogger
from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.autonomy.refusals import RefusalSystem
from src.autonomy.config import AutonomyConfig
from src.autonomy.self_improvement import SelfImprovementSystem


@dataclass
class AutonomyStatus:
    """Current status of autonomy system."""

    active: bool
    tasks_running: int
    last_trigger: Union[datetime, None] = None
    last_autonomous_action: Union[datetime, None] = None
    error_count: int = 0
    uptime_seconds: float = 0.0


@dataclass
class AutonomousAction:
    """An autonomous action to execute."""

    action_type: str
    platform: str
    content: str
    context: Dict[str, Any]
    priority: int = 1
    created_at: Union[datetime, None] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class AutonomyCoordinator:
    """
    Central coordinator for autonomous behavior across platforms.

    Manages background tasks, emotional triggers, and platform-agnostic
    autonomous actions with proper lifecycle management.
    """

    def __init__(self, conductor, logger: Optional[DemiLogger] = None):
        """
        Initialize autonomy coordinator.

        Args:
            conductor: Conductor instance for LLM and platform access
            logger: Optional logger instance
        """
        self.conductor = conductor
        self.logger = logger or DemiLogger()
        self.config = AutonomyConfig()
        self.emotion_persistence = EmotionPersistence()

        # Initialize refusal system
        self.refusal_system = RefusalSystem(self.logger)
        
        # Initialize self-improvement system
        self.self_improvement = SelfImprovementSystem(conductor)
        
        # Load self-improvement config
        self._load_self_improvement_config()

        # Initialize spontaneous initiator (will be created if needed)
        self.spontaneous_initiator = None

        # Task management
        self.background_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self.start_time = None

        # Autonomy state
        self.current_status = AutonomyStatus(active=False, tasks_running=0)
        self.pending_actions: List[AutonomousAction] = []
        self.refused_requests: List[Dict[str, Any]] = []

        # Performance tracking
        self.action_history: List[Dict[str, Any]] = []
        self.max_history_size = 100

        self.logger.info("AutonomyCoordinator initialized with refusal system and self-improvement")
    
    def _load_self_improvement_config(self):
        """Load self-improvement configuration from global config."""
        try:
            from src.core.config import DemiConfig
            config = DemiConfig.load()
            autonomy_config = config.autonomy if hasattr(config, 'autonomy') else {}
            
            si_config = autonomy_config.get('self_improvement', {})
            self.self_improvement.enabled = si_config.get('enabled', True)
            self.code_review_interval = si_config.get('code_review_interval', 1800)
            
            self.logger.info(
                f"Self-improvement config: enabled={self.self_improvement.enabled}, "
                f"interval={self.code_review_interval}s"
            )
        except Exception as e:
            self.logger.warning(f"Could not load self-improvement config: {e}")
            self.self_improvement.enabled = True
            self.code_review_interval = 1800

    def start_autonomy(self) -> bool:
        """
        Start background tasks for autonomous behavior.

        Returns:
            True if started successfully
        """
        try:
            if self.is_running:
                self.logger.warning("Autonomy already running")
                return False

            self.is_running = True
            self.start_time = time.time()

            # Start background monitoring task
            self.background_tasks["monitor"] = asyncio.create_task(
                self._monitor_emotional_state()
            )

            # Start action processor task
            self.background_tasks["processor"] = asyncio.create_task(
                self._process_autonomous_actions()
            )
            
            # Start self-improvement task if enabled
            if self.self_improvement.enabled:
                self.background_tasks["self_improvement"] = asyncio.create_task(
                    self._run_self_improvement()
                )

            self.current_status.active = True
            self.current_status.tasks_running = len(self.background_tasks)

            self.logger.info(
                f"Autonomy started with {len(self.background_tasks)} background tasks"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to start autonomy: {e}")
            self.is_running = False
            return False

    def stop_autonomy(self) -> bool:
        """
        Stop all background tasks gracefully.

        Returns:
            True if stopped successfully
        """
        try:
            if not self.is_running:
                return True

            self.is_running = False

            # Cancel all background tasks
            for task_name, task in self.background_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        asyncio.get_event_loop().run_until_complete(task)
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        self.logger.error(f"Error stopping task {task_name}: {e}")

            self.background_tasks.clear()
            self.current_status.active = False
            self.current_status.tasks_running = 0

            self.logger.info("Autonomy stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop autonomy: {e}")
            return False

    async def _monitor_emotional_state(self):
        """
        Background task to monitor emotional state and trigger autonomous actions.
        """
        while self.is_running:
            try:
                # Load current emotional state
                try:
                    emotion_state = self.emotion_persistence.load_state()
                except AttributeError:
                    # load_state method doesn't exist, create default state
                    from src.emotion.models import EmotionalState

                    emotion_state = EmotionalState()

                if emotion_state:
                    # Check if any triggers should fire
                    await self._evaluate_emotional_triggers(emotion_state)

                # Wait for next check
                await asyncio.sleep(self.config.timing_settings.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in emotional state monitoring: {e}")
                self.current_status.error_count += 1
                await asyncio.sleep(60)  # Back off on error

    async def _evaluate_emotional_triggers(self, emotion_state: EmotionalState):
        """
        Evaluate emotional triggers and create autonomous actions if needed.

        Args:
            emotion_state: Current emotional state
        """
        from src.autonomy.triggers import TriggerManager

        trigger_manager = TriggerManager(self.config, self.logger)
        triggered_actions = trigger_manager.evaluate_triggers(emotion_state)

        # Check for spontaneous initiation opportunities
        await self._check_spontaneous_initiation(emotion_state)

        for action_spec in triggered_actions:
            # Check refusal system before creating action
            refusal_analysis = self.refusal_system.should_refuse(
                action_spec.get("content", ""), action_spec.get("context", {})
            )

            if refusal_analysis.should_refuse:
                # Log refusal and skip action
                self._log_refused_action(action_spec, refusal_analysis)
                continue

            # Create autonomous action
            action = AutonomousAction(
                action_type=action_spec["type"],
                platform=action_spec["platform"],
                content=action_spec["content"],
                context=action_spec.get("context", {}),
                priority=action_spec.get("priority", 1),
            )

            self.pending_actions.append(action)
            self.logger.debug(
                f"Created autonomous action: {action.action_type} on {action.platform}"
            )

    async def _process_autonomous_actions(self):
        """
        Background task to process pending autonomous actions.
        """
        while self.is_running:
            try:
                if self.pending_actions:
                    # Sort by priority
                    self.pending_actions.sort(key=lambda a: a.priority, reverse=True)

                    # Process highest priority action
                    action = self.pending_actions.pop(0)

                    # Check rate limits
                    if self._should_execute_action():
                        await self.execute_autonomous_action(
                            action.action_type, action.context
                        )
                    else:
                        # Re-queue action if rate limited
                        self.pending_actions.append(action)
                        await asyncio.sleep(30)  # Wait before retrying

                # Small delay to prevent busy loop
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing autonomous actions: {e}")
                self.current_status.error_count += 1
                await asyncio.sleep(30)

    async def execute_autonomous_action(
        self, action_type: str, context: Dict[str, Any]
    ) -> bool:
        """
        Execute autonomous action on appropriate platform.

        Args:
            action_type: Type of autonomous action
            context: Action context and parameters

        Returns:
            True if executed successfully
        """
        try:
            # Check refusal system before executing
            request_text = context.get("content", str(context))
            refusal_analysis = self.refusal_system.should_refuse(request_text, context)

            if refusal_analysis.should_refuse:
                self._log_refused_action(context, refusal_analysis)
                return False

            # Execute action based on type and platform
            platform = context.get("platform", "discord")

            if platform == "discord":
                return self._execute_discord_action(action_type, context)
            elif platform == "android":
                return self._execute_android_action(action_type, context)
            elif platform == "telegram":
                return self._execute_telegram_action(action_type, context)
            else:
                self.logger.warning(f"Unknown platform: {platform}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to execute autonomous action {action_type}: {e}")
            self.current_status.error_count += 1
            return False

    def _execute_discord_action(
        self, action_type: str, context: Dict[str, Any]
    ) -> bool:
        """Execute autonomous action on Discord platform."""
        try:
            if hasattr(self.conductor, "send_discord_message"):
                content = context.get("content", "")
                channel_id = context.get("channel_id")

                if channel_id:
                    result = self.conductor.send_discord_message(content, channel_id)
                    if result:
                        self._log_executed_action("discord", action_type, content)
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to execute Discord action: {e}")
            return False

    def _execute_android_action(
        self, action_type: str, context: Dict[str, Any]
    ) -> bool:
        """Execute autonomous action on Android platform."""
        try:
            if hasattr(self.conductor, "send_android_websocket_message"):
                content = context.get("content", "")
                device_id = context.get("device_id", "default")

                result = self.conductor.send_android_websocket_message(
                    content, device_id
                )
                if result:
                    self._log_executed_action("android", action_type, content)
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to execute Android action: {e}")
            return False

    def _execute_telegram_action(
        self, action_type: str, context: Dict[str, Any]
    ) -> bool:
        """Execute autonomous action on Telegram platform."""
        try:
            if hasattr(self.conductor, "send_telegram_message"):
                content = context.get("content", "")
                chat_id = context.get("chat_id")

                if chat_id:
                    result = self.conductor.send_telegram_message(content, chat_id)
                    if result:
                        self._log_executed_action("telegram", action_type, content)
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to execute Telegram action: {e}")
            return False

    def _should_execute_action(self) -> bool:
        """
        Check if we should execute an action based on rate limits.

        Returns:
            True if action should be executed
        """
        # Count actions in the last hour
        one_hour_ago = datetime.now(UTC).timestamp() - 3600
        recent_actions = [
            a for a in self.action_history if a.get("timestamp", 0) > one_hour_ago
        ]

        return len(recent_actions) < self.config.safety_limits.max_autonomous_per_hour

    def _log_executed_action(self, platform: str, action_type: str, content: str):
        """Log successful autonomous action execution."""
        log_entry = {
            "platform": platform,
            "action_type": action_type,
            "content": content[:100] + "..." if len(content) > 100 else content,
            "timestamp": datetime.now(UTC).timestamp(),
            "status": "executed",
        }

        self.action_history.append(log_entry)

        # Trim history if too large
        if len(self.action_history) > self.max_history_size:
            self.action_history = self.action_history[-self.max_history_size :]

        self.current_status.last_autonomous_action = datetime.now(UTC)
        self.logger.info(f"Executed autonomous action: {action_type} on {platform}")

    async def _check_spontaneous_initiation(self, emotion_state: EmotionalState):
        """
        Check for spontaneous initiation opportunities and create actions if appropriate.

        Args:
            emotion_state: Current emotional state
        """
        # Initialize spontaneous initiator if needed
        if self.spontaneous_initiator is None:
            try:
                from src.autonomy.spontaneous import SpontaneousInitiator

                self.spontaneous_initiator = SpontaneousInitiator(
                    self.config, self.logger
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize spontaneous initiator: {e}")
                return

        try:
            # Get conversation history from conductor if available
            conversation_history = []
            user_activity = {}
            last_interaction_time = None

            if hasattr(self.conductor, "get_conversation_history"):
                conversation_history = self.conductor.get_conversation_history()

            # Get user activity patterns (simplified)
            if hasattr(self.conductor, "get_user_activity"):
                user_activity = self.conductor.get_user_activity()

            # Check for initiation opportunity
            opportunity = await self.spontaneous_initiator.should_initiate(
                emotion_state,
                conversation_history,
                last_interaction_time,
                user_activity,
            )

            if opportunity:
                # Generate spontaneous message
                message = await self.spontaneous_initiator.generate_spontaneous_message(
                    opportunity, emotion_state
                )

                # Create autonomous action for spontaneous initiation
                action = AutonomousAction(
                    action_type="spontaneous_initiation",
                    platform=opportunity.suggested_platform,
                    content=message,
                    context={
                        "trigger_type": opportunity.trigger_type.value,
                        "initiation_reason": opportunity.initiation_reason,
                        "confidence": opportunity.confidence,
                        "channel_id": self.config.platform_settings.ramble_channel_id,
                        "device_id": "default",
                    },
                    priority=2,  # High priority but lower than urgent triggers
                )

                self.pending_actions.append(action)
                self.logger.info(
                    f"Created spontaneous initiation action: {opportunity.trigger_type.value} on {opportunity.suggested_platform}"
                )

        except Exception as e:
            self.logger.error(f"Error checking spontaneous initiation: {e}")

    async def initiate_conversation(
        self, platform: str, context: Dict[str, Any]
    ) -> bool:
        """
        Initiate a conversation on the specified platform.

        Args:
            platform: Target platform
            context: Conversation context and parameters

        Returns:
            True if initiation was successful
        """
        try:
            # Use existing action execution system
            return await self.execute_autonomous_action(
                "spontaneous_initiation",
                {
                    "platform": platform,
                    "content": context.get("content", ""),
                    "channel_id": context.get("channel_id"),
                    "device_id": context.get("device_id", "default"),
                },
            )
        except Exception as e:
            self.logger.error(f"Failed to initiate conversation on {platform}: {e}")
            return False

    def track_initiation_outcome(
        self, platform: str, success: bool, outcome_details: Dict[str, Any]
    ):
        """
        Track the outcome of a spontaneous initiation.

        Args:
            platform: Platform where initiation occurred
            success: Whether the initiation was successful
            outcome_details: Additional outcome details
        """
        log_entry = {
            "platform": platform,
            "success": success,
            "outcome_details": outcome_details,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "spontaneous_initiation_outcome",
        }

        # Track in action history
        self.action_history.append(log_entry)

        # Trim history if too large
        if len(self.action_history) > self.max_history_size:
            self.action_history = self.action_history[-self.max_history_size :]

        self.logger.info(
            f"Tracked spontaneous initiation outcome on {platform}: {success}"
        )

    def _log_refused_action(self, context: Dict[str, Any], refusal_analysis):
        """Log refused autonomous action."""
        log_entry = {
            "context": context,
            "refusal_category": refusal_analysis.category.value
            if refusal_analysis.category
            else None,
            "refusal_reason": refusal_analysis.reason,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "refused",
        }

        self.refused_requests.append(log_entry)
        self.logger.info(f"Refused autonomous action: {refusal_analysis.reason}")

    def get_autonomy_status(self) -> AutonomyStatus:
        """
        Get current autonomy system status.

        Returns:
            Current autonomy status
        """
        if self.start_time:
            self.current_status.uptime_seconds = time.time() - self.start_time

        return self.current_status

    def get_refusal_statistics(self) -> Dict[str, Any]:
        """
        Get refusal system statistics.

        Returns:
            Dictionary with refusal statistics
        """
        return {
            "total_refused_requests": len(self.refused_requests),
            "recent_refusals": self.refused_requests[-10:],  # Last 10
            "refusal_system_stats": self.refusal_system.get_statistics(),
            "refusal_rate": len(self.refused_requests)
            / max(1, len(self.action_history) + len(self.refused_requests)),
        }

    def track_refused_requests(self) -> Dict[str, Any]:
        """
        Track and analyze refused request patterns.

        Returns:
            Pattern analysis results
        """
        if not self.refused_requests:
            return {
                "pattern": "no_refusals",
                "message": "No refused requests to analyze",
            }

        # Analyze refusal categories
        categories = {}
        for refusal in self.refused_requests:
            category = refusal.get("refusal_category", "unknown")
            categories[category] = categories.get(category, 0) + 1

        return {
            "total_refusals": len(self.refused_requests),
            "categories": categories,
            "most_common": max(categories.items(), key=lambda x: x[1])
            if categories
            else None,
            "refusal_rate": len(self.refused_requests)
            / max(1, len(self.action_history) + len(self.refused_requests)),
        }


    async def _run_self_improvement(self):
        """
        Background task for self-improvement.
        
        Periodically runs code review and generates improvement suggestions.
        """
        self.logger.info(f"Self-improvement task started (interval: {self.code_review_interval}s)")
        
        while self.is_running:
            try:
                # Check if it's time for a review
                if self.self_improvement.last_review_time is None:
                    should_review = True
                else:
                    time_since_last = (datetime.now(timezone.utc) - self.self_improvement.last_review_time).total_seconds()
                    should_review = time_since_last >= self.code_review_interval
                
                if should_review:
                    self.logger.info("Running scheduled self-code review...")
                    suggestions = await self.self_improvement.run_code_review()
                    
                    if suggestions:
                        self.logger.info(f"Generated {len(suggestions)} improvement suggestions")
                        
                        # Log high priority suggestions
                        high_priority = [s for s in suggestions if s.priority == "high"]
                        if high_priority:
                            self.logger.warning(f"Found {len(high_priority)} high-priority improvements")
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                self.logger.info("Self-improvement task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in self-improvement task: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error

    def get_self_improvement_status(self) -> Dict[str, Any]:
        """
        Get status of self-improvement system.
        
        Returns:
            Status dictionary
        """
        return self.self_improvement.get_status()
