---
title: Cloud SRE Env
emoji: 🔧
colorFrom: blue
colorTo: cyan
sdk: docker
pinned: false
license: mit
short_description: OpenEnv MCP Cloud SRE Sandbox for AI agent benchmarking
---

# Cloud SRE Sandbox — OpenEnv MCP Environment

An OpenEnv-compliant Cloud SRE simulation built **exactly** following the
[echo_env](https://github.com/meta-pytorch/OpenEnv/tree/main/envs/echo_env) pattern.

## Structure

```
cloud-sre-env/
├── .dockerignore
├── __init__.py           ← exports SREEnv, CallToolAction, ListToolsAction
├── client.py             ← SREEnv(MCPToolClient)
├── models.py             ← SREAction, SREObservation (legacy REST)
├── openenv.yaml          ← spec_version: 1, runtime: fastapi, port: 7860
├── pyproject.toml        ← openenv-core[core]>=0.2.2, fastmcp>=2.0.0
├── inference.py          ← hackathon [START]/[STEP]/[END] agent loop
├── outputs/logs/
├── outputs/evals/
└── server/
    ├── sre_environment.py  ← SREEnvironment(MCPEnvironment) + FastMCP tools
    ├── app.py              ← create_app(SREEnvironment, ...)
    ├── requirements.txt
    └── Dockerfile
```

## MCP Tools (SRE Actions)

| Tool | Arguments | Description |
|---|---|---|
| `read_metrics` | `service` | Get CPU, RAM, connections, latency |
| `read_logs` | `service` | Get error/warning logs |
| `restart_service` | `service` | Restart a crashed service |
| `scale_up` | `service`, `max_connections` | Increase DB connection limit |
| `rollback_deployment` | `service`, `version` | Roll back a bad deploy |

## Tasks

| Task | Difficulty | Incident | Solution |
|---|---|---|---|
| 1 | Easy | web-app OOM crash | read_logs → restart_service |
| 2 | Medium | DB connection exhaustion | read_metrics → scale_up |
| 3 | Hard | v2.1 → 500 errors | read_logs → rollback_deployment |

## Quick Start

```python
from sre_env import SREEnv

with SREEnv(base_url="https://challaudaykumar-cloud-sre-env.hf.space").sync() as env:
    env.reset()
    tools = env.list_tools()
    logs = env.call_tool("read_logs", service="all")
    result = env.call_tool("restart_service", service="web-app")
```

## Run Locally

```bash
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Run Agent

```bash
export HF_TOKEN=<your-token>
export API_BASE_URL=https://api-inference.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py
```
