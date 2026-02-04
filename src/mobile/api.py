"""Mobile API server for Flutter app.

Provides REST and WebSocket endpoints for real-time chat,
emotional state updates, and connection management.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.core.logger import get_logger
from src.voice.phoneme_generator import PhonemeGenerator, LipSyncData

logger = get_logger()


class MobileAPIServer:
    """FastAPI server for mobile app connections."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8081):
        """Initialize mobile API server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.conductor = None

        # Initialize FastAPI app
        self.app = FastAPI(
            title="Demi Mobile API",
            description="Real-time API for Demi mobile app",
            version="1.0.0",
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # State management
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Dict] = {}  # user_id -> session data
        self._running = False

        # Audio and phoneme management
        self.phoneme_generator = PhonemeGenerator()
        self.audio_cache: Dict[str, str] = {}  # filename -> path mapping
        self.audio_dir = Path("/tmp/demi_audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        # Setup routes
        self._setup_routes()

        logger.info("MobileAPIServer initialized", host=host, port=port)

    def _setup_routes(self):
        """Configure API routes."""

        @self.app.post("/api/auth/login")
        async def login(user_id: Optional[str] = None):
            """Create or get user session.

            Args:
                user_id: Optional user ID (auto-generated if not provided)

            Returns:
                Session token and user info
            """
            try:
                uid = user_id or str(uuid4())

                session = {
                    "user_id": uid,
                    "session_id": str(uuid4()),
                    "created_at": datetime.now().isoformat(),
                    "last_activity": datetime.now().isoformat(),
                }

                self.user_sessions[uid] = session

                logger.info("Mobile user login", user_id=uid)

                return {
                    "success": True,
                    "user_id": uid,
                    "session_id": session["session_id"],
                    "created_at": session["created_at"],
                }
            except Exception as e:
                logger.error(f"Login failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
            }

        @self.app.get("/api/metrics")
        async def metrics():
            """Get mobile API metrics for dashboard.

            Returns:
                Mobile app statistics and connection info
            """
            return {
                "status": "healthy",
                "active_connections": len(self.websocket_connections),
                "total_sessions": len(self.user_sessions),
                "connections": list(self.websocket_connections.keys()),
                "sessions": list(self.user_sessions.keys()),
                "timestamp": datetime.now().isoformat(),
            }

        @self.app.get("/api/user/emotions")
        async def get_emotions(user_id: str):
            """Get current emotional state for user.

            Args:
                user_id: User ID

            Returns:
                Current emotional state
            """
            try:
                if not self.conductor:
                    return {"emotions": {}, "timestamp": datetime.now().isoformat()}

                # Get emotion state from conductor (global emotion state)
                emotion_state = self.conductor.emotion_persistence.load_latest_state()

                return {
                    "emotions": emotion_state.to_dict() if emotion_state else {},
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error(f"Get emotions failed: {e}")
                return {"emotions": {}, "error": str(e)}

        @self.app.get("/audio/{filename}")
        async def serve_audio(filename: str):
            """Serve audio file for lip sync.

            Args:
                filename: Audio filename

            Returns:
                Audio file content
            """
            try:
                # Validate filename (prevent directory traversal)
                if ".." in filename or "/" in filename:
                    raise HTTPException(status_code=400, detail="Invalid filename")

                file_path = self.audio_dir / filename

                if not file_path.exists():
                    logger.warning(f"Audio file not found: {filename}")
                    raise HTTPException(status_code=404, detail="Audio file not found")

                logger.debug(f"Serving audio: {filename}")

                return FileResponse(
                    path=file_path,
                    media_type="audio/wav",
                    headers={"Content-Disposition": "inline"},
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Audio serving failed: {e}")
                raise HTTPException(status_code=500, detail="Audio serving failed")

        @self.app.websocket("/ws/chat/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: str):
            """WebSocket endpoint for real-time chat.

            Args:
                websocket: WebSocket connection
                user_id: User ID
            """
            await websocket.accept()
            self.websocket_connections[user_id] = websocket

            logger.info("Mobile WebSocket connected", user_id=user_id)

            try:
                # Send connection confirmation
                await websocket.send_json(
                    {
                        "type": "connected",
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                # Listen for messages
                while True:
                    data = await websocket.receive_text()
                    message_data = json.loads(data)

                    # Extract message content
                    content = message_data.get("message", "")
                    if not content:
                        continue

                    logger.info(
                        "Mobile message received",
                        user_id=user_id,
                        content_length=len(content),
                    )

                    try:
                        # Send typing indicator
                        await websocket.send_json(
                            {
                                "type": "typing",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                        # Route through Conductor
                        if self.conductor:
                            messages = [{"role": "user", "content": content}]
                            response = await self.conductor.request_inference(messages)

                            # Send response back
                            response_text = (
                                response
                                if isinstance(response, str)
                                else response.get("content", "Error processing request")
                            )

                            # Prepare message response with audio and lip sync data
                            message_response = {
                                "type": "message",
                                "content": response_text,
                                "timestamp": datetime.now().isoformat(),
                                "from": "demi",
                            }

                            # Attempt to generate TTS audio and lip sync data
                            audio_data = await self._generate_audio_with_lipsync(
                                response_text, user_id
                            )
                            if audio_data:
                                message_response["audioUrl"] = audio_data["audioUrl"]
                                message_response["phonemes"] = audio_data["phonemes"]
                                message_response["duration"] = audio_data["duration"]

                            await websocket.send_json(message_response)

                            # Send emotional state
                            emotion_state = (
                                self.conductor.emotion_persistence.load_latest_state()
                            )
                            if emotion_state:
                                await websocket.send_json(
                                    {
                                        "type": "emotions",
                                        "emotions": emotion_state.to_dict(),
                                        "timestamp": datetime.now().isoformat(),
                                    }
                                )
                        else:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "content": "Conductor not available",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )

                    except Exception as e:
                        logger.error(
                            f"Message processing failed: {e}", user_id=user_id
                        )
                        await websocket.send_json(
                            {
                                "type": "error",
                                "content": "Error processing message",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

            except WebSocketDisconnect:
                logger.info("Mobile WebSocket disconnected", user_id=user_id)
                if user_id in self.websocket_connections:
                    del self.websocket_connections[user_id]
            except Exception as e:
                logger.error(f"WebSocket error: {e}", user_id=user_id)
                if user_id in self.websocket_connections:
                    del self.websocket_connections[user_id]

    async def _generate_audio_with_lipsync(
        self,
        text: str,
        user_id: str,
    ) -> Optional[Dict]:
        """Generate audio and lip sync data for text.

        Args:
            text: Text to synthesize
            user_id: User ID for context

        Returns:
            Dictionary with audioUrl, phonemes, duration or None if generation failed
        """
        try:
            if not self.conductor or not hasattr(self.conductor, "piper_tts"):
                logger.debug("Piper TTS not available, skipping audio generation")
                return None

            # Generate audio file
            audio_path = await self.conductor.piper_tts.speak(
                text,
                save_path=None,
            )

            if not audio_path:
                logger.warning("Audio generation failed")
                return None

            # Create unique filename based on user and timestamp
            filename = f"{user_id}_{int(time.time() * 1000)}.wav"
            dest_path = self.audio_dir / filename

            # Copy audio to audio directory
            import shutil
            shutil.copy2(audio_path, dest_path)

            # Get audio duration
            import wave
            try:
                with wave.open(str(dest_path), 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / rate
            except Exception as e:
                logger.warning(f"Could not determine audio duration: {e}")
                duration = 2.0  # Fallback duration

            # Generate phoneme data
            phonemes = self.phoneme_generator.generate_phonemes(
                text,
                duration,
                speech_rate=1.0,
            )

            # Create audio URL (relative to mobile API base URL)
            audio_url = f"/audio/{filename}"

            # Convert phonemes to dictionaries for JSON serialization
            phoneme_dicts = [p.to_dict() for p in phonemes]

            return {
                "audioUrl": audio_url,
                "phonemes": phoneme_dicts,
                "duration": duration,
            }

        except Exception as e:
            logger.error(f"Audio/lip sync generation failed: {e}")
            return None

    async def start(self, conductor):
        """Start the mobile API server.

        Args:
            conductor: Conductor instance for LLM routing
        """
        import uvicorn

        self.conductor = conductor
        self._running = True

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        logger.info(f"Mobile API starting at http://{self.host}:{self.port}")
        await server.serve()

    async def stop(self):
        """Stop the mobile API server."""
        self._running = False

        # Close all WebSocket connections
        for user_id, websocket in list(self.websocket_connections.items()):
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket for {user_id}: {e}")

        self.websocket_connections.clear()
        logger.info("Mobile API stopped")
