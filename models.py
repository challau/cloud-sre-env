"""
models.py — Data models for the Cloud SRE MCP Environment.

These models define the action and observation types used by the OpenEnv
integration for the Cloud SRE sandbox server.

Follows the exact same pattern as calendar_env/models.py:
  - Action / Observation base classes from openenv.core.env_server.types
  - SREAction wraps all five SRE verbs
  - SREObservation carries the full structured response
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

# Support both in-repo and standalone imports (mirrors calendar_env pattern)
try:
    from openenv.core.env_server.types import Action, Observation
except ImportError:
    from openenv.core.env_server.types import Action, Observation


# ---------------------------------------------------------------------------
# Action Models
# ---------------------------------------------------------------------------

class SREAction(Action):
    """
    Unified action wrapper for the Cloud SRE environment.

    action_type values:
    - "read_metrics"         : read resource metrics for a service
    - "read_logs"            : read error logs for a service
    - "restart_service"      : restart a crashed / OOM service
    - "scale_up"             : increase resource capacity of a service
    - "rollback_deployment"  : roll back a service to a previous version
    """

    action_type: Literal[
        "read_metrics",
        "read_logs",
        "restart_service",
        "scale_up",
        "rollback_deployment",
    ] = Field(..., description="Type of SRE action to perform")

    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Key-value arguments for the chosen action",
    )


# ---------------------------------------------------------------------------
# Observation Models
# ---------------------------------------------------------------------------

class SREObservation(Observation):
    """
    Observation returned by the Cloud SRE environment after each step.

    success     — whether the action completed without error
    status_code — HTTP-style integer (200, 400, 500)
    message     — human-readable description of what happened
    data        — action-specific payload (metrics, logs, updated state)
    done        — True when the episode is complete
    reward      — dense scalar reward for the step
    """

    success: bool = Field(True, description="Whether the action succeeded")
    error_message: Optional[str] = Field(
        None, description="Error message if action failed"
    )
    status_code: int = Field(200, description="HTTP-style status code")
    message: str = Field("", description="Human-readable step summary")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Action-specific payload"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (step count, etc.)"
    )
    done: bool = Field(False, description="Whether the episode is complete")
    reward: Optional[float] = Field(None, description="Reward for this action")


__all__ = [
    "SREAction",
    "SREObservation",
]
