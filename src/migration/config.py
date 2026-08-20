"""Configuration management for migration tasks."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


class MigrationConfig:
    """Load and manage migration configuration."""

    def __init__(self, config_file: str):
        """Initialize config from file and environment variables.

        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML and substitute env variables."""
        with open(self.config_file) as f:
            config = yaml.safe_load(f)

        self._substitute_env_vars(config)
        return config

    def _substitute_env_vars(self, obj: Any) -> None:
        """Recursively substitute ${VAR} with environment variable values."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    obj[key] = os.getenv(env_var, value)
                else:
                    self._substitute_env_vars(value)
        elif isinstance(obj, list):
            for item in obj:
                self._substitute_env_vars(item)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dotted path."""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def teradata_config(self) -> Dict[str, Any]:
        """Get Teradata connection configuration."""
        return self.config.get("teradata", {})

    @property
    def aws_config(self) -> Dict[str, Any]:
        """Get AWS configuration."""
        return self.config.get("aws", {})

    @property
    def migration_config(self) -> Dict[str, Any]:
        """Get migration settings."""
        return self.config.get("migration", {})

    @property
    def tables(self) -> list:
        """Get list of tables to migrate."""
        return self.config.get("tables", [])
