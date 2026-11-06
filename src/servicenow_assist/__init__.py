"""ServiceNow incident assistant.

Looks up a user's incident or request in ServiceNow, finds previously resolved
tickets that describe the same problem, and returns the resolution steps that
worked before.
"""

from .assistant import IncidentAssistant, Match, Recommendation
from .client import ServiceNowClient, ServiceNowError
from .config import ServiceNowConfig

__all__ = [
    "IncidentAssistant",
    "Match",
    "Recommendation",
    "ServiceNowClient",
    "ServiceNowConfig",
    "ServiceNowError",
]
