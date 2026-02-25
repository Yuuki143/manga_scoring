"""FastAPI application entry point for the MMIP platform.

Configures CORS middleware, mounts the versioned API router, and exposes
a simple health check endpoint used by load balancers and orchestrators.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.database import engine, Base

# Register SQLite-compatible date_trunc when using SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _register_sqlite_functions(dbapi_conn, connection_record):
        dbapi_conn.create_function(
            "date_trunc", 2,
            lambda part, val: val[:7] + "-01" if part == "month" and val else val,
        )

# Ensure all tables exist (for SQLite / first-run convenience)
import app.models  # noqa: F401  – register all models
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Cross-platform manga market intelligence for publishers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Return the service liveness status.

    Used by load balancers and container orchestrators to verify the
    application process is responsive.
    """
    return {"status": "healthy", "service": "mmip"}
