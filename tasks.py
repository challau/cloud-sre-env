"""
tasks.py — Programmatic Task Graders for Cloud SRE Sandbox

Three graders evaluate the terminal env.state() and return a
deterministic float between 0.0 (fail) and 1.0 (full pass).

Task 1 (Easy)   — OOM Recovery:    read_logs → restart_service('web-app')
Task 2 (Medium) — DB Scale:        read_metrics → scale_up('database', 2000)
Task 3 (Hard)   — Bad Deploy:      read_logs → rollback_deployment('web-app','v2.0')
"""

from __future__ import annotations

from typing import Any, Dict


def grade_task1_oom_recovery(state: Dict[str, Any]) -> float:
    """
    web-app crashed with OOM. Agent must restart it.
    Pass: status == 'running' AND cpu_usage < 50 %
    Score strictly between 0 and 1 (never 0.0 or 1.0).
    """
    wa = state.get("web-app", {})
    status = wa.get("status", "")
    cpu = float(wa.get("cpu_usage", 100.0))

    if status == "running" and cpu < 50.0:
        return 0.95  # Full success but not 1.0
    elif status == "running":
        return 0.65  # Partial success
    elif status == "crashed":
        return 0.15  # Minimal progress
    return 0.05  # No progress but not 0.0


def grade_task2_db_scale(state: Dict[str, Any]) -> float:
    """
    database at 100% connections. Agent must scale up.
    Pass: max_connections > 1000 AND status == 'running'
    Score strictly between 0 and 1 (never 0.0 or 1.0).
    """
    db = state.get("database", {})
    max_conn = int(db.get("max_connections", 1000))
    status = db.get("status", "")

    if max_conn > 1000 and status == "running":
        return 0.92  # Full success but not 1.0
    elif max_conn > 1000:
        return 0.60  # Partial success
    elif status == "degraded":
        return 0.20  # Minimal progress
    return 0.08  # No progress but not 0.0


def grade_task3_rollback(state: Dict[str, Any]) -> float:
    """
    web-app v2.1 throwing 500 errors. Agent must rollback to v2.0.
    Pass: current_version == 'v2.0' AND error_rate == 0.0
    Score strictly between 0 and 1 (never 0.0 or 1.0).
    """
    wa = state.get("web-app", {})
    version = wa.get("current_version", "v2.1")
    error_rate = float(wa.get("error_rate", 1.0))

    if version == "v2.0" and error_rate == 0.0:
        return 0.98  # Full success but not 1.0
    elif version == "v2.0":
        return 0.70  # Partial success
    elif version == "v2.1" and error_rate < 0.5:
        return 0.25  # Some progress
    return 0.02  # No progress but not 0.0


def grade_all(state: Dict[str, Any]) -> Dict[str, float]:
    """Run all three graders and return a dict of task_name → score."""
    return {
        "task1_oom_recovery": grade_task1_oom_recovery(state),
        "task2_db_scale": grade_task2_db_scale(state),
        "task3_rollback": grade_task3_rollback(state),
    }
