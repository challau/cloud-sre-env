#!/usr/bin/env python3
"""
inference.py — OpenEnv RL Challenge Submission
Minimal example showing proper output format for openenv validate.

Requirements:
- Read env vars: API_BASE_URL, MODEL_NAME, HF_TOKEN
- Use OpenAI Client
- Output [START], [STEP], [END] lines to stdout
"""

import os
import json
import sys
from typing import Optional
from openai import OpenAI

# Read environment variables
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")

# Validate required env var
if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# Initialize OpenAI client
client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

def run_task(task_name: str, task_env: str, model: str) -> None:
    """Run a single task and emit standard output."""
    
    # Print START
    print(f"[START] task={task_name} env={task_env} model={model}", flush=True)
    
    success = False
    steps = 0
    rewards = []
    
    try:
        # Example: Call LLM and take actions
        messages = [
            {
                "role": "user",
                "content": f"Complete the task: {task_name}"
            }
        ]
        
        # Simulate a few steps
        for step_num in range(1, 4):  # 3 steps
            # Get LLM response
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=100,
            )
            
            action_text = response.choices[0].message.content or "noop"
            action_str = action_text.replace("\n", " ")[:100]
            
            # Simulate reward and done
            reward = 0.0 + (step_num * 0.1)
            done = step_num >= 3
            error = None
            
            steps = step_num
            rewards.append(reward)
            
            # Print STEP
            error_str = "null" if error is None else str(error)
            done_str = "true" if done else "false"
            print(
                f"[STEP] step={step_num} action={action_str} "
                f"reward={reward:.2f} done={done_str} error={error_str}",
                flush=True
            )
            
            if done:
                success = True
                break
            
            # Continue conversation
            messages.append({"role": "assistant", "content": action_text})
            messages.append({
                "role": "user",
                "content": f"Continue. Step {step_num} completed."
            })
    
    except Exception as e:
        error = str(e)[:100]
        print(
            f"[STEP] step={steps+1} action=error_handling "
            f"reward=0.00 done=true error={error}",
            flush=True
        )
        success = False
    
    finally:
        # Print END
        rewards_str = ",".join(f"{r:.2f}" for r in rewards)
        print(
            f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
            flush=True
        )

if __name__ == "__main__":
    # Run a simple task
    run_task(
        task_name="sre-incident",
        task_env="cloud-sre-env",
        model=MODEL_NAME
    )
