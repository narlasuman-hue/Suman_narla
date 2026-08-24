"""Application entry point."""

import sys
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.main import app
from src.scheduler.tasks import collector
from src.config import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.log_file),
    ],
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    import uvicorn

    # Start scheduler
    try:
        collector.start()
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")

    # Run API server
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
