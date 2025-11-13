from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.agentB.agent_b import AgentB
from src.agentA.agent_a import AgentA


def run(task: str, driver_path: Optional[str] = None) -> None:
    """Plan with AgentB and execute with AgentA."""
    load_dotenv()
    planner = AgentB()
    plan = planner.plan(task)
    executor = AgentA(driver_path=driver_path)
    results = executor.execute_plan(plan)
    for r in results:
        status = r["result"].get("status")
        print(f"Step {r['step_index']:02d} {r['action_type'].upper()}: {status}")
        if status not in ("success", "skipped"):
            print(f"  Error: {r['result'].get('error_message')}")


if __name__ == "__main__":
    # Simple CLI: python -m src.orchestrator "Open google and search for Softlight"
    if len(sys.argv) < 2:
        print("Usage: python -m src.orchestrator \"<task description>\"")
        sys.exit(1)
    task_arg = sys.argv[1]
    run(task_arg)




