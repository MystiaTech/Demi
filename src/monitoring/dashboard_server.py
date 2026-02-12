"""Dashboard API server with FastAPI.

Provides REST API and WebSocket endpoints for the health monitoring dashboard.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.logger import get_logger
from src.monitoring.metrics import (
    MetricsCollector,
    get_metrics_collector,
    MetricType,
    get_llm_metrics,
    get_platform_metrics,
    get_conversation_metrics,
    get_emotion_metrics,
    get_discord_metrics,
)
from src.monitoring.alerts import AlertManager, get_alert_manager, AlertLevel

logger = get_logger()
security = HTTPBearer(auto_error=False)


class DashboardServer:
    """FastAPI-based dashboard server for health monitoring."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        update_interval: int = 5,
        api_key: Optional[str] = None,
        static_dir: Optional[str] = None,
    ):
        """Initialize dashboard server.

        Args:
            host: Host to bind to
            port: Port to listen on
            update_interval: Seconds between update broadcasts
            api_key: Optional API key for authentication
            static_dir: Directory containing static files
        """
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.api_key = api_key or os.getenv("DEMI_DASHBOARD_API_KEY")

        # Setup static files directory
        if static_dir:
            self.static_dir = Path(static_dir)
        else:
            self.static_dir = Path(__file__).parent / "dashboard_static"

        # Initialize FastAPI app
        self.app = FastAPI(
            title="Demi Health Dashboard API",
            description="Real-time health monitoring for Demi",
            version="1.0.0",
        )

        # Suppress Uvicorn access logging for dashboard to reduce noise
        import logging
        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        uvicorn_access_logger.setLevel(logging.WARNING)

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # State
        self.websocket_connections: Set[WebSocket] = set()
        self._update_task: Optional[asyncio.Task] = None
        self._running = False

        # Get monitoring components
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()

        # Register routes
        self._setup_routes()

        logger.info("DashboardServer initialized", host=host, port=port)

    def _setup_routes(self):
        """Configure API routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def serve_dashboard():
            """Serve the dashboard HTML."""
            index_file = self.static_dir / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return HTMLResponse(
                content="<h1>Dashboard not built</h1><p>Static files not found.</p>",
                status_code=404,
            )

        @self.app.get("/dashboard_static/{filename}")
        async def serve_static(filename: str):
            """Serve static files (JS, CSS)."""
            file_path = self.static_dir / filename
            # Security check: ensure file is within static_dir
            try:
                file_path.resolve().relative_to(self.static_dir.resolve())
            except ValueError:
                raise HTTPException(status_code=403, detail="Access denied")

            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            raise HTTPException(status_code=404, detail="File not found")

        @self.app.get("/api/health")
        async def get_health():
            """Get overall system health status."""
            try:
                # Collect current metrics
                metrics = await self._get_system_metrics()

                # Determine overall status
                status_value = "healthy"
                memory_percent = metrics.get("memory_percent", 0)
                cpu_percent = metrics.get("cpu_percent", 0)

                if memory_percent > 90 or cpu_percent > 90:
                    status_value = "critical"
                elif memory_percent > 80 or cpu_percent > 80:
                    status_value = "warning"

                return {
                    "status": status_value,
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics,
                    "alerts_count": len(self.alert_manager.get_active_alerts()),
                }
            except Exception as e:
                logger.error("Health endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics/current")
        async def get_current_metrics():
            """Get all current metrics."""
            try:
                metrics = await self._get_system_metrics()
                return {
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics,
                }
            except Exception as e:
                logger.error("Metrics endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/alerts")
        async def get_alerts(active_only: bool = False, level: Optional[str] = None):
            """Get alerts.

            Args:
                active_only: Only return active alerts
                level: Filter by level (info, warning, critical)
            """
            try:
                alert_level = None
                if level:
                    alert_level = AlertLevel(level.lower())

                if active_only:
                    alerts = self.alert_manager.get_active_alerts(level=alert_level)
                else:
                    alerts = self.alert_manager.get_alert_history()

                return {
                    "alerts": [alert.to_dict() for alert in alerts],
                    "count": len(alerts),
                    "active_count": len(self.alert_manager.get_active_alerts()),
                }
            except Exception as e:
                logger.error("Alerts endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/alerts/{alert_id}/ack")
        async def acknowledge_alert(alert_id: str):
            """Acknowledge an alert."""
            try:
                success = self.alert_manager.acknowledge_alert(alert_id)
                if not success:
                    raise HTTPException(status_code=404, detail="Alert not found")
                return {"status": "acknowledged", "alert_id": alert_id}
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Acknowledge alert error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/alerts/{alert_id}/resolve")
        async def resolve_alert(alert_id: str):
            """Manually resolve an alert."""
            try:
                success = self.alert_manager.resolve_alert(alert_id)
                if not success:
                    raise HTTPException(status_code=404, detail="Alert not found")
                return {"status": "resolved", "alert_id": alert_id}
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Resolve alert error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/emotions")
        async def get_emotions():
            """Get current emotional state."""
            try:
                emotions = await self._get_emotional_state()
                if emotions is None:
                    raise HTTPException(
                        status_code=404, detail="No emotional state available"
                    )
                return emotions
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Emotions endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/emotions/history")
        async def get_emotions_history(hours: int = 24):
            """Get emotional state history.

            Args:
                hours: Hours of history to retrieve
            """
            try:
                # Query emotion metrics from collector
                from datetime import timedelta

                emotions_data = {}
                emotion_names = [
                    "loneliness",
                    "excitement",
                    "frustration",
                    "jealousy",
                    "vulnerability",
                    "confidence",
                    "curiosity",
                    "affection",
                    "defensiveness",
                ]

                for emotion in emotion_names:
                    metrics = self.metrics_collector.get_metric(
                        f"emotion_{emotion}", timedelta(hours=hours)
                    )
                    if metrics:
                        emotions_data[emotion] = [
                            {"timestamp": m.timestamp, "value": m.value}
                            for m in metrics
                        ]

                return {
                    "hours": hours,
                    "emotions": emotions_data,
                }
            except Exception as e:
                logger.error("Emotions history error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/platforms")
        async def get_platforms():
            """Get platform status."""
            try:
                # Try to get from conductor health monitor
                try:
                    from src.conductor.health import get_health_monitor

                    health_monitor = get_health_monitor()
                    statuses = health_monitor.get_all_statuses()

                    platforms = {}
                    for name, result in statuses.items():
                        platforms[name] = {
                            "status": result.status.value,
                            "duration_ms": result.duration * 1000,
                            "error": result.error,
                            "last_check": datetime.fromtimestamp(
                                result.timestamp
                            ).isoformat(),
                        }

                    return {"platforms": platforms, "count": len(platforms)}

                except Exception as e:
                    logger.debug("Could not get platform status from health monitor", error=str(e))
                    return {"platforms": {}, "count": 0, "error": str(e)}

            except Exception as e:
                logger.error("Platforms endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics/llm")
        async def get_llm_metrics_endpoint():
            """Get LLM performance metrics."""
            try:
                from datetime import timedelta
                from src.monitoring.metrics import get_llm_metrics

                llm_metrics = get_llm_metrics()

                # Get recent metrics
                response_times = self.metrics_collector.get_metric(
                    "llm_response_time_ms", timedelta(hours=1), limit=100
                )
                tokens = self.metrics_collector.get_metric(
                    "llm_tokens_generated", timedelta(hours=1), limit=100
                )
                latencies = self.metrics_collector.get_metric(
                    "llm_inference_latency_ms", timedelta(hours=1), limit=100
                )

                return {
                    "response_times": [
                        {
                            "timestamp": m.timestamp,
                            "value": round(m.value, 2),
                        }
                        for m in response_times
                    ],
                    "tokens_generated": [
                        {
                            "timestamp": m.timestamp,
                            "value": m.value,
                        }
                        for m in tokens
                    ],
                    "latencies": [
                        {
                            "timestamp": m.timestamp,
                            "value": round(m.value, 2),
                        }
                        for m in latencies
                    ],
                    "stats": {
                        "avg_response_time": round(
                            self.metrics_collector.aggregate(
                                "llm_response_time_ms", "avg", timedelta(hours=1)
                            ) or 0,
                            2,
                        ),
                        "max_response_time": round(
                            self.metrics_collector.aggregate(
                                "llm_response_time_ms", "max", timedelta(hours=1)
                            ) or 0,
                            2,
                        ),
                        "total_tokens": int(
                            self.metrics_collector.aggregate(
                                "llm_tokens_generated", "sum", timedelta(hours=1)
                            ) or 0
                        ),
                    },
                }
            except Exception as e:
                logger.error("LLM metrics endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/processing")
        async def get_processing_state():
            """Get current processing state (active requests, etc)."""
            try:
                # Get active requests from LLM inference
                active_requests = 0
                total_requests = 0
                try:
                    from src.conductor.orchestrator import get_conductor_instance
                    conductor = get_conductor_instance()
                    if conductor and conductor.llm:
                        active_requests = conductor.llm.get_active_requests()
                        total_requests = conductor.llm.get_total_requests()
                except Exception:
                    pass  # Conductor might not be initialized yet
                
                return {
                    "active_requests": active_requests,
                    "total_requests": total_requests,
                    "is_processing": active_requests > 0,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error("Processing state endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/system/uptime")
        async def get_system_uptime():
            """Get actual system uptime from conductor/orchestrator."""
            try:
                uptime_seconds = 0
                start_time_iso = None
                
                # Try to get from conductor
                try:
                    from src.conductor.orchestrator import get_conductor_instance
                    conductor = get_conductor_instance()
                    if conductor:
                        uptime_seconds = conductor.get_uptime()
                        if hasattr(conductor, '_startup_time') and conductor._startup_time:
                            start_time_iso = datetime.fromtimestamp(conductor._startup_time).isoformat()
                except Exception as e:
                    logger.debug("Could not get uptime from conductor", error=str(e))
                
                # Fallback to dashboard uptime if conductor not available
                if uptime_seconds == 0:
                    from src.monitoring.dashboard import Dashboard
                    # The dashboard instance might be tracked elsewhere
                    # For now, return 0 if conductor not available
                    pass
                
                return {
                    "uptime_seconds": uptime_seconds,
                    "start_time": start_time_iso,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error("Uptime endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/system/rambles")
        async def get_recent_rambles(hours: int = 24):
            """Get recent ramble/thought history."""
            try:
                from src.models.rambles import RambleStore
                from src.core.database import get_db_path
                
                db_path = get_db_path()
                store = RambleStore(db_path)
                
                rambles = await store.get_recent_rambles(hours)
                
                return {
                    "rambles": [
                        {
                            "id": r.ramble_id,
                            "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                            "trigger": r.trigger,
                            "created_at": r.created_at.isoformat(),
                            "emotion_state": r.emotion_state,
                        }
                        for r in rambles
                    ],
                    "count": len(rambles),
                    "hours": hours,
                }
            except Exception as e:
                logger.debug("Could not get rambles", error=str(e))
                return {"rambles": [], "count": 0, "hours": hours, "error": str(e)}

        @self.app.get("/api/system/self-improvement")
        async def get_self_improvement_status():
            """Get self-improvement system status and recent attempts."""
            try:
                # Try to get from autonomy coordinator
                try:
                    from src.conductor.orchestrator import get_conductor_instance
                    conductor = get_conductor_instance()
                    if conductor and hasattr(conductor, 'autonomy_coordinator'):
                        coordinator = conductor.autonomy_coordinator
                        if coordinator and hasattr(coordinator, 'self_improvement'):
                            si = coordinator.self_improvement
                            status = si.get_status()
                            
                            # Get recent suggestions
                            recent = si.get_suggestion_history(limit=10)
                            
                            return {
                                "enabled": status.get("enabled", False),
                                "total_suggestions": status.get("total_suggestions", 0),
                                "pending_approval": status.get("pending_approval", 0),
                                "by_status": status.get("by_status", {}),
                                "recent_suggestions": [
                                    {
                                        "id": s.suggestion_id,
                                        "file_path": s.file_path,
                                        "description": s.description[:100] + "..." if len(s.description) > 100 else s.description,
                                        "priority": s.priority,
                                        "status": s.status.value,
                                        "confidence": s.confidence,
                                        "created_at": s.created_at.isoformat() if s.created_at else None,
                                        "applied_at": s.applied_at.isoformat() if s.applied_at else None,
                                        "error_message": s.error_message,
                                    }
                                    for s in recent
                                ],
                                "safety_level": status.get("safety_level", "normal"),
                                "git_available": status.get("git_available", False),
                            }
                except Exception as e:
                    logger.debug("Could not get self-improvement status", error=str(e))
                
                return {
                    "enabled": False,
                    "message": "Self-improvement system not available",
                    "recent_suggestions": [],
                }
            except Exception as e:
                logger.error("Self-improvement endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics/platforms")
        async def get_platforms_metrics():
            """Get platform interaction statistics."""
            try:
                from datetime import timedelta
                from src.monitoring.metrics import get_platform_metrics

                platform_metrics = get_platform_metrics()
                stats = platform_metrics.get_platform_stats(timedelta(hours=1))

                return {
                    "platforms": stats,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error("Platform metrics endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics/conversation")
        async def get_conversation_metrics_endpoint():
            """Get conversation quality metrics."""
            try:
                from datetime import timedelta
                from src.monitoring.metrics import get_conversation_metrics

                conv_metrics = get_conversation_metrics()
                quality = conv_metrics.get_quality_metrics(timedelta(hours=1))

                # Get recent messages for context
                recent_turns = self.metrics_collector.get_metric(
                    "conversation_turn_number", timedelta(hours=1), limit=20
                )

                return {
                    "quality": quality,
                    "recent_turns": [
                        {
                            "timestamp": m.timestamp,
                            "turn": int(m.value),
                        }
                        for m in recent_turns
                    ],
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error("Conversation metrics endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics/emotions/history")
        async def get_emotions_history_endpoint(hours: int = 1, limit: int = 100):
            """Get emotion history data.

            Args:
                hours: Hours of history to retrieve
                limit: Maximum points per emotion
            """
            try:
                from src.monitoring.metrics import get_emotion_metrics

                emotion_metrics = get_emotion_metrics()
                emotions_data = {}

                for emotion in emotion_metrics.EMOTION_NAMES:
                    history = emotion_metrics.get_emotion_history(emotion, limit)
                    if history:
                        emotions_data[emotion] = history

                return {
                    "emotions": emotions_data,
                    "hours": hours,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error("Emotion history endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics/discord")
        async def get_discord_metrics_endpoint():
            """Get Discord bot status metrics."""
            try:
                from src.monitoring.metrics import get_discord_metrics

                discord_metrics = get_discord_metrics()
                status = discord_metrics.get_bot_status()

                return {
                    "bot_status": status,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error("Discord metrics endpoint error", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics/voice/tts")
        async def get_tts_metrics_endpoint():
            """Get Text-to-Speech metrics and status."""
            try:
                from src.voice.tts import TextToSpeech

                # Try to get TTS instance from conductor or create new one
                tts_stats = {
                    "backend": "not_initialized",
                    "total_utterances": 0,
                    "avg_latency_ms": 0,
                    "cache_hit_rate": 0,
                    "preferred_voice": None,
                }

                # Try to get from Discord voice if available
                try:
                    from src.integrations.discord_voice import DiscordVoiceClient
                    # This is a static attempt - in production, would get from active client
                    tts = TextToSpeech()
                    if tts.get_backend():
                        tts_stats = tts.get_stats()
                except Exception:
                    pass

                return {
                    "tts": tts_stats,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.debug(f"TTS metrics endpoint: {e}")
                return {
                    "tts": {
                        "backend": "not_available",
                        "total_utterances": 0,
                        "avg_latency_ms": 0,
                        "cache_hit_rate": 0,
                    },
                    "timestamp": datetime.now().isoformat(),
                }

        @self.app.get("/api/metrics/voice/stt")
        async def get_stt_metrics_endpoint():
            """Get Speech-to-Text metrics and status."""
            try:
                from src.voice.stt import FasterWhisperSTT

                # Try to get STT instance from conductor or create new one
                stt_stats = {
                    "backend": "not_initialized",
                    "model_size": "unknown",
                    "total_transcriptions": 0,
                    "avg_latency_ms": 0,
                    "avg_confidence": 0,
                    "errors": 0,
                    "model_loaded": False,
                }

                # Try to get from Discord voice if available
                try:
                    from src.integrations.discord_voice import DiscordVoiceClient
                    # This is a static attempt - in production, would get from active client
                    stt = FasterWhisperSTT.for_rtx3060()
                    if stt.is_model_loaded():
                        stt_stats = stt.get_stats()
                except Exception:
                    pass

                return {
                    "stt": stt_stats,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.debug(f"STT metrics endpoint: {e}")
                return {
                    "stt": {
                        "backend": "not_available",
                        "model_size": "unknown",
                        "total_transcriptions": 0,
                        "avg_latency_ms": 0,
                        "avg_confidence": 0,
                        "errors": 0,
                        "model_loaded": False,
                    },
                    "timestamp": datetime.now().isoformat(),
                }

        @self.app.get("/api/metrics/{name}")
        async def get_metric_history(
            name: str,
            hours: int = 24,
            aggregate: Optional[str] = None,
        ):
            """Get metric history (generic endpoint for any metric name).

            Note: This should be the last metric endpoint to avoid shadowing
            more specific routes like /api/metrics/llm, /api/metrics/conversation, etc.

            Args:
                name: Metric name
                hours: Hours of history to retrieve
                aggregate: Optional aggregation ('avg', 'min', 'max')
            """
            try:
                from datetime import timedelta

                time_range = timedelta(hours=hours)

                if aggregate:
                    value = self.metrics_collector.aggregate(name, aggregate, time_range)
                    return {
                        "name": name,
                        "aggregate": aggregate,
                        "value": value,
                        "hours": hours,
                    }
                else:
                    metrics = self.metrics_collector.get_metric(name, time_range)
                    return {
                        "name": name,
                        "data": [m.to_dict() for m in metrics],
                        "count": len(metrics),
                        "hours": hours,
                    }
            except Exception as e:
                logger.error("Metric history error", error=str(e), name=name)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time dashboard updates."""
            await websocket.accept()
            self.websocket_connections.add(websocket)
            logger.debug(f"WebSocket connected, total: {len(self.websocket_connections)}")

            try:
                # Send initial data
                await self._send_update(websocket)

                # Keep connection alive and handle client messages
                while True:
                    try:
                        data = await asyncio.wait_for(
                            websocket.receive_json(), timeout=30.0
                        )

                        # Handle ping
                        if data.get("action") == "ping":
                            await websocket.send_json({"type": "pong"})

                    except asyncio.TimeoutError:
                        # Send keepalive ping
                        try:
                            await websocket.send_json({"type": "ping"})
                        except Exception:
                            break

            except WebSocketDisconnect:
                pass
            except Exception as e:
                logger.debug(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.discard(websocket)
                logger.debug(
                    f"WebSocket disconnected, total: {len(self.websocket_connections)}"
                )

    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            disk = psutil.disk_usage("/")

            # Get response time metrics if available
            response_time_p90 = 0.0
            try:
                latest = self.metrics_collector.get_latest("response_time_p90")
                if latest:
                    response_time_p90 = latest.value
            except Exception:
                pass

            return {
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "cpu_percent": cpu,
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "response_time_p90": response_time_p90,
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            logger.error("Failed to get system metrics", error=str(e))
            return {"error": str(e)}

    async def _get_emotional_state(self) -> Optional[Dict[str, Any]]:
        """Fetch current emotional state."""
        try:
            # Try to get from emotion system
            try:
                from src.emotion.persistence import EmotionPersistence

                persistence = EmotionPersistence()
                state = persistence.load_latest_state()
                if state:
                    return {
                        "loneliness": state.loneliness,
                        "excitement": state.excitement,
                        "frustration": state.frustration,
                        "jealousy": state.jealousy,
                        "vulnerability": state.vulnerability,
                        "confidence": state.confidence,
                        "curiosity": state.curiosity,
                        "affection": state.affection,
                        "defensiveness": state.defensiveness,
                        "last_updated": state.last_updated.isoformat(),
                    }
            except Exception as e:
                logger.debug("Could not load from emotion persistence", error=str(e))

            # Fallback: try to get from metrics
            emotions = {}
            emotion_names = [
                "loneliness",
                "excitement",
                "frustration",
                "jealousy",
                "vulnerability",
                "confidence",
                "curiosity",
                "affection",
                "defensiveness",
            ]

            for emotion in emotion_names:
                metric = self.metrics_collector.get_latest(f"emotion_{emotion}")
                emotions[emotion] = metric.value if metric else 0.5

            emotions["last_updated"] = datetime.now().isoformat()
            return emotions

        except Exception as e:
            logger.error("Failed to get emotional state", error=str(e))
            return None

    async def _send_update(self, websocket: WebSocket):
        """Send current data to a specific websocket."""
        try:
            metrics = await self._get_system_metrics()
            emotions = await self._get_emotional_state()
            alerts = self.alert_manager.get_active_alerts()

            await websocket.send_json(
                {
                    "type": "update",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics,
                    "emotions": emotions,
                    "alerts": [a.to_dict() for a in alerts[:5]],
                }
            )
        except Exception as e:
            logger.debug(f"Failed to send update: {e}")

    async def _broadcast_update(self):
        """Broadcast update to all connected WebSocket clients."""
        if not self.websocket_connections:
            return

        try:
            metrics = await self._get_system_metrics()
            emotions = await self._get_emotional_state()
            alerts = self.alert_manager.get_active_alerts()

            message = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "emotions": emotions,
                "alerts": [a.to_dict() for a in alerts[:5]],
            }

            disconnected = set()
            for ws in self.websocket_connections:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.debug(f"Failed to send to websocket: {e}")
                    disconnected.add(ws)

            # Clean up disconnected clients
            if disconnected:
                self.websocket_connections -= disconnected
                logger.debug(f"Cleaned up {len(disconnected)} disconnected WebSocket clients")

            # Log successful broadcast
            if self.websocket_connections:
                logger.debug(f"Broadcasted update to {len(self.websocket_connections)} clients")

        except Exception as e:
            logger.error("Broadcast update error", error=str(e))

    async def _update_loop(self):
        """Background loop to push updates to clients."""
        while self._running:
            try:
                await self._broadcast_update()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Update loop error", error=str(e))
                await asyncio.sleep(self.update_interval)

    async def start(self):
        """Start the dashboard server."""
        import uvicorn

        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        logger.info(f"Dashboard server starting at http://{self.host}:{self.port}")
        await server.serve()

    async def stop(self):
        """Stop the dashboard server."""
        self._running = False

        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        # Close all WebSocket connections
        for ws in list(self.websocket_connections):
            try:
                await ws.close()
            except Exception:
                pass
        self.websocket_connections.clear()

        logger.info("Dashboard server stopped")

    def get_url(self) -> str:
        """Get dashboard URL."""
        return f"http://{self.host}:{self.port}"
