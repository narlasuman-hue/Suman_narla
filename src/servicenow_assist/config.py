"""Configuration for the ServiceNow connection, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ServiceNowConfig:
    """Connection settings for a ServiceNow instance.

    Authenticate either with basic auth (``username`` + ``password``) or with an
    OAuth bearer ``token``. Secrets are read from the environment, never hardcoded.
    """

    instance_url: str
    username: str | None = None
    password: str | None = None
    token: str | None = None
    timeout: float = 30.0
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        if not self.instance_url.startswith("https://"):
            raise ValueError("instance_url must start with https://")
        if not self.token and not (self.username and self.password):
            raise ValueError(
                "Provide SERVICENOW_TOKEN, or SERVICENOW_USERNAME and SERVICENOW_PASSWORD"
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ServiceNowConfig:
        """Build a config from ``SERVICENOW_*`` environment variables.

        ``SERVICENOW_INSTANCE`` may be a full URL (``https://acme.service-now.com``)
        or just the instance name (``acme``).
        """
        env = os.environ if env is None else env
        instance = env.get("SERVICENOW_INSTANCE", "").strip().rstrip("/")
        if not instance:
            raise ValueError("SERVICENOW_INSTANCE is not set")
        if "://" not in instance:
            instance = f"https://{instance}.service-now.com"
        return cls(
            instance_url=instance,
            username=env.get("SERVICENOW_USERNAME") or None,
            password=env.get("SERVICENOW_PASSWORD") or None,
            token=env.get("SERVICENOW_TOKEN") or None,
            timeout=float(env.get("SERVICENOW_TIMEOUT", "30")),
            verify_ssl=env.get("SERVICENOW_VERIFY_SSL", "true").lower() != "false",
        )
