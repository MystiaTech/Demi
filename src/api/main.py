import uvicorn
import os
from src.api import create_app

if __name__ == "__main__":
    app = create_app()

    host = os.getenv("ANDROID_API_HOST", "0.0.0.0")
    port = int(os.getenv("ANDROID_API_PORT", "8000"))

    print(f"Starting Demi Android API on {host}:{port}")
    print("Endpoints:")
    print("  POST /api/v1/auth/login")
    print("  POST /api/v1/auth/refresh")
    print("  GET  /api/v1/auth/sessions")
    print("  DELETE /api/v1/auth/sessions/{id}")
    print("  GET  /api/v1/status")

    uvicorn.run(app, host=host, port=port, log_level="info")
