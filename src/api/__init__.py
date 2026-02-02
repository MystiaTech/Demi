from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.auth import router as auth_router
from src.api.migrations import run_all_migrations
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
        logger.info("FastAPI started, database migrations complete")

    # Include auth router
    app.include_router(auth_router)

    # Health check
    @app.get("/api/v1/status")
    async def status():
        return {"status": "ok", "service": "demi-android-api", "version": "1.0.0"}

    return app


# Create app instance for deployment
app = create_app()
