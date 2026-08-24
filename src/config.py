"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # App config
    app_name: str = "Database Metadata Catalog"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Catalog database
    catalog_db_host: str = "localhost"
    catalog_db_port: int = 5432
    catalog_db_name: str = "metadata_catalog"
    catalog_db_user: str = "catalog_user"
    catalog_db_password: str = "password"
    database_url: Optional[str] = None

    # Teradata connection
    teradata_host: str = "localhost"
    teradata_port: int = 1025
    teradata_user: str = "user"
    teradata_password: str = "password"
    teradata_database: str = "default"

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # Scheduler settings
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"
    metadata_sync_interval: int = 3600  # seconds
    usage_stats_interval: int = 1800

    # Elasticsearch
    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_enabled: bool = False

    # Logging
    log_file: str = "logs/app.log"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_database_url(self) -> str:
        """Get the database URL."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.catalog_db_user}:{self.catalog_db_password}@"
            f"{self.catalog_db_host}:{self.catalog_db_port}/{self.catalog_db_name}"
        )

    def get_teradata_dsn(self) -> str:
        """Get Teradata DSN string."""
        return (
            f"DSN=Teradata;HOST={self.teradata_host};PORT={self.teradata_port};"
            f"USER={self.teradata_user};PASSWORD={self.teradata_password};"
            f"DATABASE={self.teradata_database}"
        )


# Create global settings instance
settings = Settings()
