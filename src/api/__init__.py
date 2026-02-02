from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.auth import router as auth_router
from src.api.websocket import router as websocket_router
from src.api.migrations import run_all_migrations
from src.api.autonomy import get_autonomy_task, create_checkins_table
from src.core.logger import DemiLogger

logger = DemiLogger()


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Demi Android API",
        version="1.0.0",
        description="API for Android client communication with Demi",
    )

    # Add CORS middleware (allow Android client requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Mobile clients from any origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize database
    @app.on_event("startup")
    async def startup():
        run_all_migrations()
        create_checkins_table()
        logger.info("FastAPI started, database migrations complete")

        # Start autonomy task
        autonomy_task = get_autonomy_task()
        await autonomy_task.start()

    # Include auth router
    app.include_router(auth_router)

    # Include websocket router
    app.include_router(websocket_router)

    # Health check
    @app.get("/api/v1/status")
    async def status():
        return {"status": "ok", "service": "demi-android-api", "version": "1.0.0"}

    # Shutdown handler
    @app.on_event("shutdown")
    async def shutdown():
        # Stop autonomy task
        autonomy_task = get_autonomy_task()
        await autonomy_task.stop()

    return app


# Create app instance for deployment
app = create_app()
