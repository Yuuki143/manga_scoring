"""Top-level API router for MMIP v1.

Aggregates all sub-routers under a single ``APIRouter`` instance that is
mounted onto the FastAPI application in ``app.main``.
"""

from fastapi import APIRouter

from app.api.v1 import auth, titles, genres, alerts, predictions, upload

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(titles.router, prefix="/titles", tags=["Titles"])
api_router.include_router(genres.router, prefix="/genres", tags=["Genres"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(predictions.router, prefix="/trends", tags=["Predictions"])
api_router.include_router(upload.router, prefix="/data", tags=["Data Upload"])
