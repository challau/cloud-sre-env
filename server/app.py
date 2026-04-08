"""
server/app.py — FastAPI Application for Cloud SRE Sandbox

Mirrors echo_env/server/app.py exactly.
Uses create_app() from openenv-core to create the full server
with WebSocket, HTTP, and optional web interface endpoints.

Usage:
    # Development:
    uvicorn server.app:app --reload --host 0.0.0.0 --port 7860

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 7860 --workers 4

    # Via pyproject.toml script:
    uv run --project . server
"""

import os

# Support both in-repo and standalone imports (mirrors echo_env pattern)
try:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from .sre_environment import SREEnvironment
except ImportError:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from server.sre_environment import SREEnvironment

# Create the app — pass class (factory) not instance for WebSocket session support
# Mirrors: create_app(EchoEnvironment, CallToolAction, CallToolObservation, env_name="echo_env")
app = create_app(
    SREEnvironment,
    CallToolAction,
    CallToolObservation,
    env_name="cloud_sre_env",
)


def main():
    """
    Entry point for direct execution.

    Enables running the server without Docker:
        uv run --project . server
        python -m sre_env.server.app
    """
    import uvicorn

    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
