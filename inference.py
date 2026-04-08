"""
inference.py — Baseline AI Agent for Cloud SRE Sandbox
=======================================================
Hackathon-compliant inference script.

Uses: SREEnv (MCPToolClient) → calls MCP tools → reads observations.

Env vars:
  API_BASE_URL  default: "https://api.openai.com/v1"
  MODEL_NAME    default: "gpt-4o-mini"
  HF_TOKEN      REQUIRED

Output format:
  [START] task=<name> env=cloud-sre-env model=<model>
  [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> rewards=<r1,r2,...>
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from openai import OpenAI

# ── env vars ─────────────────────────────────────────────────────────────────
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required but not set.")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

# ── system prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) inside a Cloud SRE Sandbox.
Diagnose and remediate infrastructure incidents via structured JSON actions.

Respond with ONLY a single JSON object — no markdown, no extra text:
{"tool": "<tool_name>", "arguments": {<key: value pairs>}}

Available MCP tools:
| tool                 | arguments                                         |
|----------------------|---------------------------------------------------|
| read_metrics         | service: "web-app" | "database" | "all"          |
| read_logs            | service: "web-app" | "database" | "all"          |
| restart_service      | service: "web-app" | "database"                 |
| scale_up             | service: "database", max_connections: <int>      |
| rollback_deployment  | service: "web-app", version: "<version>"         |

Strategy:
1. ALWAYS start by reading logs or metrics to understand the incident.
2. Choose the most targeted remediation.
3. Positive reward in the response = progress made.
"""

# ── task configs ──────────────────────────────────────────────────────────────
TASK_CONFIGS = [
    {
        "name": "task1-oom-recovery",
        "prompt": (
            "INCIDENT: web-app has crashed with an Out-Of-Memory error. "
            "CPU at 98.5%%. Investigate logs and restart the service."
        ),
    },
    {
        "name": "task2-db-scale",
        "prompt": (
            "INCIDENT: database at 100%% connections (1000/1000), causing 4500ms latency. "
            "Check metrics then scale up max_connections to at least 2000."
        ),
    },
    {
        "name": "task3-rollback",
        "prompt": (
            "INCIDENT: web-app v2.1 deployed 10min ago, throwing 500 errors on 87%% of requests. "
            "Read logs, identify the bad version, and rollback to v2.0."
        ),
    },
]


def run_episode(task_name: str, task_prompt: str, base_url: str,
                max_steps: int = 15) -> List[float]:
    """Run one episode using direct HTTP calls to the SRE server."""
    import requests as req

    rewards: List[float] = []
    success = False
    step_n = 0

    print(f"[START] task={task_name} env=cloud-sre-env model={MODEL_NAME}", flush=True)

    # Reset environment
    try:
        reset_resp = req.post(f"{base_url}/reset", timeout=30)
        initial_obs = reset_resp.json()
    except Exception:
        initial_obs = {"message": "Environment ready. web-app CRASHED, database DEGRADED."}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"TASK: {task_prompt}\n\n"
                f"INITIAL STATE: {json.dumps(initial_obs, indent=2)}\n\n"
                "Issue your first action as a JSON object with 'tool' and 'arguments' keys."
            ),
        },
    ]

    try:
        for step_n in range(1, max_steps + 1):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.2,
                max_tokens=512,
            )
            raw = response.choices[0].message.content or ""
            action_str = raw.strip().replace("\n", " ")
            step_error: Optional[str] = None
            reward_val = 0.0
            done = False

            try:
                # Parse LLM response
                text = raw.strip()
                if text.startswith("```"):
                    lines = text.splitlines()
                    text = "\n".join(l for l in lines[1:] if not l.startswith("```"))
                payload = json.loads(text)
                tool_name = payload.get("tool", "")
                arguments = payload.get("arguments", {})

                # Call the MCP tool via HTTP
                step_resp = req.post(
                    f"{base_url}/step",
                    json={"action_type": "CallToolAction",
                          "tool_name": tool_name,
                          "arguments": arguments},
                    timeout=30,
                )
                step_data = step_resp.json()
                obs = step_data.get("observation", step_data)
                done = step_data.get("done", False)
                reward_val = float(
                    step_data.get("reward", 0.0) or
                    obs.get("reward", 0.0)
                )

                # Feed result back to LLM
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Tool result (step {step_n}):\n"
                        f"{json.dumps(obs, indent=2)}\n\n"
                        f"Reward: {reward_val:.2f}\n\n"
                        "Issue your next action as a JSON object."
                    ),
                })

            except Exception as exc:
                step_error = str(exc)[:120]

            rewards.append(reward_val)
            done_str = "true" if done else "false"
            err_str = "null" if not step_error else step_error

            print(
                f"[STEP] step={step_n} action={action_str} "
                f"reward={reward_val:.2f} done={done_str} error={err_str}",
                flush=True,
            )

            if done:
                success = reward_val >= 0.5
                break

    except Exception:
        traceback.print_exc(file=sys.stderr)

    finally:
        rewards_str = ",".join(f"{r:.2f}" for r in rewards)
        print(
            f"[END] success={str(success).lower()} "
            f"steps={step_n} rewards={rewards_str}",
            flush=True,
        )

    return rewards


def main() -> None:
    base_url = os.getenv("SRE_SERVER_URL", "http://localhost:8000")

    for task_cfg in TASK_CONFIGS:
        run_episode(task_cfg["name"], task_cfg["prompt"], base_url)


if __name__ == "__main__":
    main()
