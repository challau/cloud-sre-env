"""
client.py — Cloud SRE Environment Client

Mirrors echo_env/client.py exactly.
SREEnv extends MCPToolClient to provide MCP tool-calling interactions
with the Cloud SRE Sandbox server.

Example:
    >>> with SREEnv(base_url="http://localhost:7860").sync() as env:
    ...     env.reset()
    ...
    ...     # Discover available SRE tools
    ...     tools = env.list_tools()
    ...     print([t.name for t in tools])
    ...
    ...     # Investigate the incidents
    ...     logs = env.call_tool("read_logs", service="all")
    ...     metrics = env.call_tool("read_metrics", service="web-app")
    ...
    ...     # Remediate
    ...     result = env.call_tool("restart_service", service="web-app")
    ...     result = env.call_tool("scale_up", service="database", max_connections=2000)
    ...     result = env.call_tool("rollback_deployment", service="web-app", version="v2.0")

Example with HuggingFace Space:
    >>> env = SREEnv.from_env("challaudaykumar/cloud-sre-env")
    >>> try:
    ...     env.reset()
    ...     result = env.call_tool("read_logs", service="all")
    ... finally:
    ...     env.close()
"""

from openenv.core.mcp_client import MCPToolClient


class SREEnv(MCPToolClient):
    """
    Client for the Cloud SRE Sandbox Environment.

    Inherits all MCP functionality from MCPToolClient:
      - list_tools()            : Discover available SRE action tools
      - call_tool(name, **args) : Execute an SRE action by name
      - reset(**kwargs)         : Reset the environment to broken state
      - step(action)            : Execute a raw MCP action

    Available tools on the server:
      read_metrics(service)               — get resource metrics
      read_logs(service)                  — get error logs
      restart_service(service)            — restart a crashed service
      scale_up(service, max_connections)  — scale database connections
      rollback_deployment(service, version) — roll back bad deploy
    """

    pass  # MCPToolClient provides all needed functionality
