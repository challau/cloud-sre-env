"""
server/main.py — FastAPI Application for Cloud SRE Sandbox
===========================================================
Mirrors calendar_env/server/main.py exactly:

  • Creates the FastAPI app
  • Uses openenv-core's MCPHTTPEnvServer (if available) to auto-register
    /reset, /step, /state OpenEnv routes
  • Falls back to manual FastAPI routes if openenv-core is not installed
  • Adds /health, /grade, and /docs

The environment factory pattern is identical to calendar_env:
  create_sre_environment() is passed as a callable (not called immediately)
  so each session gets an isolated SREEnvironment instance.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

load_dotenv()

# ── local imports ────────────────────────────────────────────────────────────
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from server.sre_environment import SREEnvironment  # noqa: E402
from models import SREAction, SREObservation  # noqa: E402
from tasks import grade_all  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Try to import openenv-core (same try/except pattern as calendar_env) ──────
try:
    from openenv.core.env_server.http_server import MCPHTTPEnvServer  # type: ignore

    OPENENV_AVAILABLE = True
    logger.info("openenv-core available — OpenEnv routes will be registered automatically")
except ImportError as _e:
    logger.warning(f"openenv-core not available ({_e}) — using manual route registration")
    OPENENV_AVAILABLE = False


# ---------------------------------------------------------------------------
# Environment factory  (passed as callable, not called immediately)
# ---------------------------------------------------------------------------

def create_sre_environment() -> SREEnvironment:
    """Factory function for creating an SREEnvironment per session."""
    session_id = os.getenv("SESSION_ID", "default")
    return SREEnvironment(session_id=session_id)


# ---------------------------------------------------------------------------
# Singleton in-process environment (used by manual routes)
# ---------------------------------------------------------------------------

_env = SREEnvironment()


# ---------------------------------------------------------------------------
# Lifespan — identical structure to calendar_env
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook following calendar_env's lifespan pattern."""
    logger.info("Starting Cloud SRE Sandbox server...")

    if OPENENV_AVAILABLE:
        logger.info("Initialising Cloud SRE OpenEnv environment...")
        try:
            http_server = MCPHTTPEnvServer(
                env=create_sre_environment,   # pass the factory, not an instance
                action_cls=SREAction,
                observation_cls=SREObservation,
            )
            http_server.register_routes(app)
            logger.info("Cloud SRE OpenEnv environment initialised successfully")
        except Exception as exc:
            logger.error(f"Failed to initialise OpenEnv: {exc}", exc_info=True)
    else:
        logger.warning(
            "OpenEnv routes not registered via openenv-core — "
            "manual /reset, /step, /state routes are active instead"
        )

    yield

    logger.info("Shutting down Cloud SRE Sandbox server...")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    lifespan=lifespan,
    title="Cloud SRE Sandbox",
    description="""
## Cloud SRE Sandbox — OpenEnv Environment

A headless, production-grade **Site Reliability Engineering** simulation for
benchmarking AI agents in the Meta OpenEnv Hackathon.

### Available Actions

| action_type | Key Parameters |
|---|---|
| `read_metrics` | `service`: web-app \\| database \\| all |
| `read_logs` | `service`: web-app \\| database \\| all |
| `restart_service` | `service`: web-app \\| database |
| `scale_up` | `service`: database, `max_connections`: int |
| `rollback_deployment` | `service`: web-app, `version`: str |

### Tasks

| Task | Difficulty | Incident | Correct Actions |
|---|---|---|---|
| 1 | Easy | web-app OOM crash | read_logs → restart_service |
| 2 | Medium | DB connection exhaustion | read_metrics → scale_up |
| 3 | Hard | Bad deploy v2.1→500s | read_logs → rollback_deployment |
    """,
    version="1.0.0",
    contact={"name": "Cloud SRE Sandbox"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Manual OpenEnv routes (active when openenv-core is not installed)
# These mirror exactly what MCPHTTPEnvServer.register_routes() would add.
# ---------------------------------------------------------------------------

class StepRequest(BaseModel):
    """Request body for /step."""
    action_type: str
    parameters: dict = {}


@app.get("/health", tags=["OpenEnv"])
async def health():
    """Liveness probe — returns 200 when the server is running."""
    return {"status": "healthy", "service": "cloud-sre-env"}


@app.post("/reset", tags=["OpenEnv"])
async def reset():
    """Reset the environment to its initial broken state."""
    global _env
    _env = SREEnvironment()
    obs = _env.reset()
    return obs.model_dump()


@app.post("/step", tags=["OpenEnv"])
async def step(request: StepRequest):
    """Execute one action and return (observation, done)."""
    try:
        action = SREAction(
            action_type=request.action_type,  # type: ignore[arg-type]
            parameters=request.parameters,
        )
    except Exception as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    obs, done = _env.step(action)
    return {
        "observation": obs.model_dump(),
        "done": done,
        "reward": obs.reward,
        "info": obs.metadata,
    }


@app.get("/state", tags=["OpenEnv"])
async def state():
    """Return a read-only snapshot of the current environment state."""
    return _env.state()


@app.get("/grade", tags=["OpenEnv"])
async def grade():
    """Run all task graders on the current state and return scores."""
    return grade_all(_env.state())


# ---------------------------------------------------------------------------
# Root redirect → Swagger docs
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)},
    )
