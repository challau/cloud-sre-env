"""
Cloud SRE Sandbox — OpenEnv MCP Environment

A headless Site Reliability Engineering simulation environment
built exactly following the echo_env pattern from OpenEnv.

All SRE actions are exposed as MCP tools:
  - read_metrics(service)        : Get CPU, RAM, connections, latency
  - read_logs(service)           : Get error/warning logs
  - restart_service(service)     : Restart a crashed service
  - scale_up(service, max_conn)  : Increase database connection limit
  - rollback_deployment(service, version) : Roll back a bad deploy

Example:
    >>> from sre_env import SREEnv
    >>> with SREEnv(base_url="http://localhost:7860").sync() as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("read_logs", service="web-app")
    ...     result = env.call_tool("restart_service", service="web-app")
"""

# Re-export MCP types for convenience (mirrors echo_env/__init__.py)
from openenv.core.env_server.mcp_types import CallToolAction, ListToolsAction

from .client import SREEnv

__all__ = ["SREEnv", "CallToolAction", "ListToolsAction"]
