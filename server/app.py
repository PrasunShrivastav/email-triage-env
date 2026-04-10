# Re-export the FastAPI app for openenv multi-mode deployment
from app.server import app

__all__ = ["app"]
