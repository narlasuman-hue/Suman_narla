"""Main FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.config import settings
from src.catalog.database import init_db
from src.api.routes import health, databases, tables, jobs

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Database Metadata Catalog API")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Database Metadata Catalog API")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Database Metadata Catalog - Track database assets and lifecycle",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(databases.router, prefix="/api/v1", tags=["Databases"])
app.include_router(tables.router, prefix="/api/v1", tags=["Tables"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])

# Import routers for Phase 2
from src.api.routes import lifecycle, reports
app.include_router(lifecycle.router, prefix="/api/v1", tags=["Lifecycle"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])

# Import routers for Phase 3
from src.api.routes import lineage, search, query_analysis
app.include_router(lineage.router, prefix="/api/v1", tags=["Lineage"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(query_analysis.router, prefix="/api/v1", tags=["Query Analysis"])

# Mainframe jobs, files, and schedules
from src.api.routes import mainframe
app.include_router(mainframe.router, prefix="/api/v1", tags=["Mainframe"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.debug,
    )
