"""
server/sre_environment.py — Cloud SRE Environment Implementation

Mirrors echo_env/server/echo_environment.py exactly.
Uses MCPEnvironment + FastMCP to expose all SRE actions as MCP tools.

Three live cloud incidents are simulated:
  Task 1 (Easy)   — web-app OOM crash
  Task 2 (Medium) — database connection exhaustion  
  Task 3 (Hard)   — bad deployment v2.1 → 500 errors

Example:
    >>> from openenv.core.env_server.mcp_types import CallToolAction
    >>> env = SREEnvironment()
    >>> env.reset()
    >>> obs = env.step(CallToolAction(tool_name="read_logs", arguments={"service": "all"}))
    >>> obs = env.step(CallToolAction(tool_name="restart_service", arguments={"service": "web-app"}))
"""

import copy
import time
from typing import Any, Optional
from uuid import uuid4

try:
    from openenv.core.env_server.mcp_environment import MCPEnvironment
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:
    from openenv.core.env_server.mcp_environment import MCPEnvironment
    from openenv.core.env_server.types import Action, Observation, State

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Canonical initial (broken) state
# ---------------------------------------------------------------------------

_INITIAL_STATE = {
    "web-app": {
        "cpu_usage": 98.5,
        "ram_usage": 99.2,
        "current_version": "v2.1",
        "status": "crashed",
        "error_rate": 0.87,
        "restart_count": 3,
    },
    "database": {
        "active_connections": 1000,
        "max_connections": 1000,
        "status": "degraded",
        "query_latency_ms": 4500,
    },
    "logs": {
        "web-app": [
            "[ERROR] Out of Memory on web-app — heap exhausted (v2.1)",
            "[ERROR] HTTP 500 on /api/checkout — NullPointerException (v2.1)",
            "[WARN]  Excessive GC pressure detected on web-app",
            "[ERROR] web-app process killed by OOM killer (PID 4821)",
        ],
        "database": [
            "[ERROR] Connection timeout on database — max_connections=1000 reached",
            "[WARN]  Connection pool exhausted — clients queuing",
            "[ERROR] Query latency > 4000 ms on database",
        ],
    },
    "incident_resolved": False,
}


class SREEnvironment(MCPEnvironment):
    """
    Cloud SRE Sandbox environment — pure MCP environment.

    Exposes SRE actions as MCP tools via FastMCP.
    Inherits MCP support (ListToolsAction, CallToolAction) from MCPEnvironment.

    All state is scoped to an episode (reset by calling reset()).
    """

    def __init__(self):
        """Initialise the SRE environment with FastMCP and all SRE tools."""
        mcp = FastMCP("cloud_sre_env")
        self._sim = copy.deepcopy(_INITIAL_STATE)

        # ── Tool: read_metrics ──────────────────────────────────────────────

        @mcp.tool
        def read_metrics(service: str = "all") -> dict:
            """
            Read current resource metrics for a service.

            Args:
                service: Target service — 'web-app', 'database', or 'all'

            Returns:
                Dict with CPU, RAM, connections, latency, status for the service(s)
            """
            data = {}
            if service in ("web-app", "all"):
                data["web-app"] = {
                    k: self._sim["web-app"][k]
                    for k in ["cpu_usage", "ram_usage", "current_version",
                              "status", "error_rate"]
                }
            if service in ("database", "all"):
                data["database"] = {
                    k: self._sim["database"][k]
                    for k in ["active_connections", "max_connections",
                              "status", "query_latency_ms"]
                }
            if not data:
                return {"error": f"Unknown service '{service}'. Use web-app, database, or all."}
            return data

        # ── Tool: read_logs ─────────────────────────────────────────────────

        @mcp.tool
        def read_logs(service: str = "all") -> dict:
            """
            Read error and warning logs for a service.

            Args:
                service: Target service — 'web-app', 'database', or 'all'

            Returns:
                Dict mapping service name to list of log lines
            """
            if service == "all":
                return {"logs": dict(self._sim["logs"])}
            elif service in self._sim["logs"]:
                return {"logs": {service: self._sim["logs"][service]}}
            return {"error": f"No logs found for '{service}'."}

        # ── Tool: restart_service ───────────────────────────────────────────

        @mcp.tool
        def restart_service(service: str) -> dict:
            """
            Restart a service to recover from a crash or OOM error.

            Args:
                service: Service to restart — 'web-app' or 'database'

            Returns:
                Updated service state after restart, with any warnings
            """
            if service == "web-app":
                wa = self._sim["web-app"]
                wa["status"] = "running"
                wa["cpu_usage"] = 22.0
                wa["ram_usage"] = 45.0
                wa["restart_count"] += 1
                wa["error_rate"] = 0.85  # v2.1 still deployed
                return {
                    "status": wa["status"],
                    "cpu_usage": wa["cpu_usage"],
                    "ram_usage": wa["ram_usage"],
                    "current_version": wa["current_version"],
                    "warning": "v2.1 still deployed — 500 errors persist. Consider rollback.",
                    "reward": 1.0,
                }
            elif service == "database":
                self._sim["database"]["status"] = "restarting"
                return {
                    "status": "restarting",
                    "note": "Restart initiated. This will NOT fix max_connections limit.",
                    "reward": -0.5,
                }
            return {"error": f"Unknown service '{service}'. Use 'web-app' or 'database'."}

        # ── Tool: scale_up ──────────────────────────────────────────────────

        @mcp.tool
        def scale_up(service: str, max_connections: int) -> dict:
            """
            Increase the resource capacity of a service.

            Args:
                service: Service to scale — 'database'
                max_connections: New max connections limit (must exceed current 1000)

            Returns:
                Updated database state after scaling
            """
            if service != "database":
                return {"error": f"scale_up is only supported for 'database'. Got: '{service}'."}

            old = self._sim["database"]["max_connections"]
            if max_connections <= old:
                return {"error": f"New limit ({max_connections}) must exceed current ({old})."}

            self._sim["database"]["max_connections"] = max_connections
            self._sim["database"]["status"] = "running"
            self._sim["database"]["query_latency_ms"] = 95
            self._sim["incident_resolved"] = True
            return {
                "old_max_connections": old,
                "max_connections": max_connections,
                "status": "running",
                "query_latency_ms": 95,
                "reward": 1.0,
            }

        # ── Tool: rollback_deployment ───────────────────────────────────────

        @mcp.tool
        def rollback_deployment(service: str, version: str) -> dict:
            """
            Roll back a service deployment to a previous known-good version.

            Args:
                service: Service to roll back — 'web-app'
                version: Target version string, e.g. 'v2.0'

            Returns:
                Updated service state after rollback
            """
            if service != "web-app":
                return {"error": f"Rollback only supported for 'web-app'. Got: '{service}'."}

            current = self._sim["web-app"]["current_version"]

            if version != "v2.0":
                return {
                    "error": f"'{version}' is not a known-good version. Hint: check the logs for the last stable version."
                }

            self._sim["web-app"].update({
                "current_version": "v2.0",
                "error_rate": 0.0,
                "status": "running",
                "cpu_usage": 18.0,
                "ram_usage": 40.0,
            })
            self._sim["logs"]["web-app"] = [
                "[INFO] web-app rolled back to v2.0 — all clear",
                "[INFO] HTTP error rate: 0.0%",
            ]
            self._sim["incident_resolved"] = True
            return {
                "previous_version": current,
                "current_version": "v2.0",
                "error_rate": 0.0,
                "status": "running",
                "reward": 1.0,
            }

        # Pass the MCP server to the base class (mirrors echo_env exactly)
        super().__init__(mcp)
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """Reset the environment to its initial broken state."""
        self._sim = copy.deepcopy(_INITIAL_STATE)
        self._state = State(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
        )
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "status": "reset",
                "message": (
                    "Environment reset. Active incidents: "
                    "web-app CRASHED (OOM, v2.1 errors), "
                    "database DEGRADED (connection limit reached)."
                ),
                "web_app_status": self._sim["web-app"]["status"],
                "database_status": self._sim["database"]["status"],
                "active_incidents": [
                    "web-app OOM crash",
                    "database connection exhaustion",
                    "web-app v2.1 500 errors",
                ],
            },
        )

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Execute a step — increments step count, delegates to base class."""
        self._state.step_count += 1
        return super().step(action, timeout_s=timeout_s, **kwargs)

    async def step_async(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Async step used by the WebSocket handler."""
        self._state.step_count += 1
        return await super().step_async(action, timeout_s=timeout_s, **kwargs)

    def _step_impl(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Handle non-MCP actions (returns error)."""
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "error": (
                    f"Unknown action type: {type(action).__name__}. "
                    "Use ListToolsAction or CallToolAction."
                )
            },
        )

    @property
    def state(self) -> State:
        """Return the current episode state."""
        return self._state
