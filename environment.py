"""
environment.py — Cloud SRE Simulation Engine

Equivalent to calendar_env's MCPEnvironment.
Implements the OpenEnv reset / step / state contract for SRE incidents.

The mock state tracks two services (web-app, database) with realistic
metrics and logs injected at startup. Every action returns an
SREObservation + dense reward score.
"""

from __future__ import annotations

import copy
import time
from typing import Any, Dict, Optional, Tuple

from models import SREAction, SREObservation

# ---------------------------------------------------------------------------
# Canonical initial (broken) state  ← restored by reset()
# ---------------------------------------------------------------------------

_INITIAL_STATE: Dict[str, Any] = {
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
    "step_count": 0,
    "start_time": None,
}


class SREEnvironment:
    """Cloud SRE Sandbox simulation engine.

    Follows the same interface contract as calendar_env's MCPEnvironment:
        reset()  → SREObservation
        step()   → (SREObservation, done: bool)
        state()  → Dict
    """

    MAX_STEPS = 20

    def __init__(self, session_id: str = "default", **kwargs: Any) -> None:
        self.session_id = session_id
        self._state: Dict[str, Any] = {}
        self.reset()

    # ------------------------------------------------------------------
    # OpenEnv contract
    # ------------------------------------------------------------------

    def reset(self) -> SREObservation:
        """Restore broken state and return the opening observation."""
        self._state = copy.deepcopy(_INITIAL_STATE)
        self._state["start_time"] = time.time()
        self._state["step_count"] = 0

        return SREObservation(
            success=True,
            status_code=200,
            message=(
                "Environment reset. Active incidents: "
                "web-app CRASHED (OOM, v2.1 errors), "
                "database DEGRADED (connection limit reached)."
            ),
            data={
                "web_app_status": self._state["web-app"]["status"],
                "database_status": self._state["database"]["status"],
                "active_incidents": [
                    "web-app OOM crash",
                    "database connection exhaustion",
                    "web-app v2.1 500 errors",
                ],
            },
            done=False,
            reward=0.0,
            metadata={"step_count": 0, "session_id": self.session_id},
        )

    def step(self, action: SREAction) -> Tuple[SREObservation, bool]:
        """Execute one action, advance state, return (observation, done)."""
        self._state["step_count"] += 1

        handler = {
            "read_metrics": self._read_metrics,
            "read_logs": self._read_logs,
            "restart_service": self._restart_service,
            "scale_up": self._scale_up,
            "rollback_deployment": self._rollback_deployment,
        }.get(action.action_type)

        if handler is None:
            obs = SREObservation(
                success=False,
                status_code=400,
                message=f"Unknown action_type: {action.action_type}",
                data={},
                reward=-0.5,
                done=False,
                metadata=self._meta(),
            )
            return obs, False

        obs = handler(action.parameters or {})
        done = self._state["incident_resolved"] or self._state["step_count"] >= self.MAX_STEPS
        obs.done = done
        obs.metadata = self._meta()
        return obs, done

    def state(self) -> Dict[str, Any]:
        """Return a deep-copy snapshot for graders and /state endpoint."""
        return copy.deepcopy(self._state)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _read_metrics(self, params: Dict[str, Any]) -> SREObservation:
        service = params.get("service", "all")
        data: Dict[str, Any] = {}

        if service in ("web-app", "all"):
            data["web-app"] = {k: self._state["web-app"][k]
                               for k in ["cpu_usage", "ram_usage",
                                         "current_version", "status", "error_rate"]}
        if service in ("database", "all"):
            data["database"] = {k: self._state["database"][k]
                                for k in ["active_connections", "max_connections",
                                          "status", "query_latency_ms"]}

        if not data:
            return SREObservation(
                success=False, status_code=400,
                message=f"Unknown service '{service}'. Use web-app, database, or all.",
                data={}, reward=-0.1,
            )

        return SREObservation(
            success=True, status_code=200,
            message=f"Metrics retrieved for: {service}.",
            data=data, reward=0.1,
        )

    def _read_logs(self, params: Dict[str, Any]) -> SREObservation:
        service = params.get("service", "all")

        if service == "all":
            logs = dict(self._state["logs"])
        elif service in self._state["logs"]:
            logs = {service: self._state["logs"][service]}
        else:
            return SREObservation(
                success=False, status_code=400,
                message=f"No logs found for '{service}'.",
                data={}, reward=-0.1,
            )

        return SREObservation(
            success=True, status_code=200,
            message=f"Logs retrieved for: {service}.",
            data={"logs": logs}, reward=0.2,
        )

    def _restart_service(self, params: Dict[str, Any]) -> SREObservation:
        service = params.get("service")
        if not service:
            return SREObservation(
                success=False, status_code=400,
                message="Parameter 'service' is required for restart_service.",
                data={}, reward=-0.3,
            )

        if service == "web-app":
            wa = self._state["web-app"]
            wa["status"] = "running"
            wa["cpu_usage"] = 22.0
            wa["ram_usage"] = 45.0
            wa["restart_count"] += 1
            wa["error_rate"] = 0.85     # v2.1 still deployed → errors persist
            return SREObservation(
                success=True, status_code=200,
                message=(
                    "web-app restarted. CPU/RAM normalised. "
                    "WARNING: v2.1 still deployed — 500 errors persist."
                ),
                data={"web-app": {
                    "status": wa["status"],
                    "cpu_usage": wa["cpu_usage"],
                    "ram_usage": wa["ram_usage"],
                    "current_version": wa["current_version"],
                }},
                reward=1.0,
            )

        if service == "database":
            self._state["database"]["status"] = "restarting"
            return SREObservation(
                success=True, status_code=200,
                message="database restart initiated. This will NOT fix max_connections limit.",
                data={"database": {"status": "restarting"}},
                reward=-0.5,
            )

        return SREObservation(
            success=False, status_code=400,
            message=f"Unknown service '{service}'.",
            data={}, reward=-0.3,
        )

    def _scale_up(self, params: Dict[str, Any]) -> SREObservation:
        service = params.get("service")
        new_limit = params.get("max_connections") or params.get("limit")

        if not service:
            return SREObservation(
                success=False, status_code=400,
                message="Parameter 'service' is required for scale_up.",
                data={}, reward=-0.3,
            )

        if service == "database":
            if new_limit is None:
                return SREObservation(
                    success=False, status_code=400,
                    message="Parameter 'max_connections' required for database scale_up.",
                    data={}, reward=-0.2,
                )
            old = self._state["database"]["max_connections"]
            new = int(new_limit)
            if new <= old:
                return SREObservation(
                    success=False, status_code=400,
                    message=f"New limit ({new}) must exceed current ({old}).",
                    data={}, reward=-0.3,
                )
            self._state["database"]["max_connections"] = new
            self._state["database"]["status"] = "running"
            self._state["database"]["query_latency_ms"] = 95
            self._state["incident_resolved"] = True
            return SREObservation(
                success=True, status_code=200,
                message=f"database max_connections scaled {old} → {new}. Status: running.",
                data={"database": {
                    "old_max_connections": old,
                    "max_connections": new,
                    "status": "running",
                    "query_latency_ms": 95,
                }},
                reward=1.0,
            )

        return SREObservation(
            success=False, status_code=400,
            message=f"scale_up not supported for '{service}'.",
            data={}, reward=-0.3,
        )

    def _rollback_deployment(self, params: Dict[str, Any]) -> SREObservation:
        service = params.get("service")
        version = params.get("version") or params.get("target_version")

        if not service or not version:
            return SREObservation(
                success=False, status_code=400,
                message="Parameters 'service' and 'version' required for rollback_deployment.",
                data={}, reward=-0.3,
            )

        if service == "web-app":
            current = self._state["web-app"]["current_version"]
            if version == "v2.0":
                self._state["web-app"].update({
                    "current_version": "v2.0",
                    "error_rate": 0.0,
                    "status": "running",
                    "cpu_usage": 18.0,
                    "ram_usage": 40.0,
                })
                self._state["logs"]["web-app"] = [
                    "[INFO] web-app rolled back to v2.0 — all clear",
                    "[INFO] HTTP error rate: 0.0 %",
                ]
                self._state["incident_resolved"] = True
                return SREObservation(
                    success=True, status_code=200,
                    message=f"web-app rolled back {current} → v2.0. 500 errors eliminated.",
                    data={"web-app": {
                        "previous_version": current,
                        "current_version": "v2.0",
                        "error_rate": 0.0,
                        "status": "running",
                    }},
                    reward=1.0,
                )
            return SREObservation(
                success=False, status_code=400,
                message=f"'{version}' is not a known-good version. Hint: check the logs.",
                data={}, reward=-0.3,
            )

        return SREObservation(
            success=False, status_code=400,
            message=f"Rollback only supported for 'web-app'. Got: '{service}'.",
            data={}, reward=-0.2,
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _meta(self) -> Dict[str, Any]:
        return {
            "step_count": self._state["step_count"],
            "incident_resolved": self._state["incident_resolved"],
            "web_app_status": self._state["web-app"]["status"],
            "database_status": self._state["database"]["status"],
            "session_id": self.session_id,
        }
