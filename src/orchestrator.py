from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

from src.agentB.agent_b import AgentB
from src.agentA.agent_a import AgentA


def _kill_existing_brave_processes(user_data_dir: Optional[str] = None) -> None:
    """Best-effort kill of Brave processes and stale profile locks on macOS."""
    if platform.system() != "Darwin":
        return

    for name in ["Brave Browser", "Brave Browser Helper", "chrome_crashpad_handler"]:
        try:
            subprocess.run(
                ["killall", "-9", name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    if not user_data_dir:
        return

    for marker in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        marker_path = os.path.join(user_data_dir, marker)
        try:
            if os.path.exists(marker_path):
                os.remove(marker_path)
        except Exception:
            pass


def ensure_brave_remote_debugging(port: int = 9222, profile_directory: str = "Default") -> None:
    """
    Ensure Brave Browser is running with a remote-debugging port so AgentA can attach.
    
    On macOS, this launches Brave headful with the user's default profile.
    """
    if platform.system() != "Darwin":
        # For other platforms we skip automated launch for now.
        return

    brave_executable = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    user_data_dir = os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser")

    if not os.path.exists(brave_executable):
        raise FileNotFoundError(
            "Brave executable not found at /Applications/Brave Browser.app/Contents/MacOS/Brave Browser. "
            "Install Brave or update ensure_brave_remote_debugging() with the correct path."
        )

    # If Brave is already exposing the port, nothing to do.
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1.5):
            print(f"✅ Brave remote debugging endpoint already available on port {port}.")
            return
    except Exception:
        pass

    # Always restart to guarantee a predictable session.
    _kill_existing_brave_processes(user_data_dir=user_data_dir)
    time.sleep(0.5)

    launch_cmd = [
        brave_executable,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_directory}",
    ]

    print(f"🟢 Launching Brave with remote debugging on port {port}...")
    subprocess.Popen(
        launch_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )

    # Wait for CDP endpoint to become reachable (Brave can take a while on first launch).
    deadline = time.time() + 90
    last_error: Optional[Exception] = None
    next_status = time.time()
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1.5):
                print("✅ Brave remote debugging endpoint is ready.")
                return
        except urllib.error.URLError as err:
            last_error = err
        except Exception as err:
            last_error = err
        if time.time() >= next_status:
            print("⏳ Waiting for Brave to expose the CDP endpoint...")
            next_status = time.time() + 5
        time.sleep(0.5)

    raise RuntimeError(
        f"Timed out waiting for Brave remote debugging port {port} to become ready."
        + (f" Last error: {last_error}" if last_error else "")
    )


def run_iterative(
    task: str,
    driver_path: Optional[str] = None,
    max_steps: int = 50,
    use_real_browser: bool = True,
    browser_type: str = "brave",
    debug_port: int = 9222,
) -> List[Dict[str, Any]]:
    """
    Run iterative feedback loop between Agent B (planner) and Agent A (executor).
    
    Flow:
    1. Agent B decides first action based on task
    2. Agent A executes action and captures screenshot
    3. Agent B analyzes screenshot and decides next action
    4. Repeat until task complete or max steps reached
    """
    load_dotenv()
    
    # Set up Brave browser if using real browser
    if use_real_browser and browser_type.lower() == "brave":
        brave_profile_directory = "Default"
        ensure_brave_remote_debugging(
            port=debug_port,
            profile_directory=brave_profile_directory,
        )
    
    # Initialize agents
    planner = AgentB()
    
    # Configure Agent A with browser settings
    executor_kwargs = {
        "driver_path": driver_path,
        "headless": False,  # Show browser for debugging
        "model": "gpt-4o",
    }
    
    if use_real_browser and browser_type.lower() == "brave":
        executor_kwargs.update({
            "use_real_browser": True,
            "browser_type": "brave",
            "cdp_url": f"http://localhost:{debug_port}",
            "user_data_dir": os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser"),
            "profile_directory": "Default",
            "strict_real_browser": True,
            "force_kill_chrome": False,
        })
    
    executor = AgentA(**executor_kwargs)
    executor.current_task_name = task
    # Don't initialize browser here - it will be created on first action
    # executor.initialize_browser()  # Not needed - browser created on first action
    
    execution_history: List[Dict[str, Any]] = []
    step_counter = 0
    current_screenshot_path: Optional[str] = None
    
    print(f"\n{'=' * 70}")
    print(f"🎯 Starting iterative execution: {task}")
    print(f"{'=' * 70}\n")
    
    try:
        while step_counter < max_steps:
            step_counter += 1
            print(f"\n--- Step {step_counter} ---")
            
            # Agent B decides next action
            print("🤔 Agent B: Analyzing current state and deciding next action...")
            try:
                next_action = planner.decide_next_action(
                    task=task,
                    screenshot_path=current_screenshot_path,
                    execution_history=execution_history,
                    current_url=executor.get_current_url(),
                )
                
                print(f"✅ Agent B decided: {next_action.action_type.upper()} - {next_action.target_description}")
                if next_action.reasoning:
                    print(f"   Reasoning: {next_action.reasoning}")
                
                # Check if task is complete
                if next_action.action_type == "evaluate_state":
                    print("\n🔍 Agent B: Evaluating if task is complete...")
                    is_complete = planner.is_task_complete(
                        task=task,
                        screenshot_path=current_screenshot_path,
                        execution_history=execution_history,
                    )
                    if is_complete:
                        print("✅ Task appears to be complete!")
                        break
                
            except Exception as e:
                print(f"❌ Agent B error: {e}")
                import traceback
                traceback.print_exc()
                break
            
            # Agent A executes the action
            print(f"🚀 Agent A: Executing {next_action.action_type}...")
            try:
                result = executor.execute_single_action(
                    action=next_action,
                    step_index=step_counter,
                )
                
                execution_history.append(result)
                current_screenshot_path = result["result"].get("screenshot_path")
                
                status = result["result"].get("status")
                print(f"   Status: {status}")
                
                if status == "error":
                    error_msg = result["result"].get("error_message")
                    print(f"   Error: {error_msg}")
                    # Continue anyway - Agent B can adapt
                
                if current_screenshot_path:
                    print(f"   📸 Screenshot saved: {current_screenshot_path}")
                
            except Exception as e:
                print(f"❌ Agent A execution error: {e}")
                import traceback
                traceback.print_exc()
                # Add error to history so Agent B can adapt
                execution_history.append({
                    "step_index": step_counter,
                    "action_type": next_action.action_type,
                    "action": next_action,
                    "result": {
                        "status": "error",
                        "error_message": str(e),
                        "screenshot_path": current_screenshot_path,
                    }
                })
                # Continue - let Agent B decide how to recover
        
        print(f"\n{'=' * 70}")
        print(f"✅ Iterative execution completed after {step_counter} steps")
        print(f"{'=' * 70}\n")
        
        return execution_history
        
    finally:
        executor.close()


def run(
    task: str,
    driver_path: Optional[str] = None,
    iterative: bool = True,
    use_real_browser: bool = True,
    browser_type: str = "brave",
) -> None:
    """
    Main entry point. Supports both iterative and batch modes.
    
    Args:
        task: Task description
        driver_path: Optional driver path
        iterative: If True, use iterative feedback loop (default: True)
        use_real_browser: If True, use real browser (default: True)
        browser_type: Browser type to use (default: "brave")
    """
    if iterative:
        results = run_iterative(
            task,
            driver_path,
            use_real_browser=use_real_browser,
            browser_type=browser_type,
        )
        for r in results:
            status = r["result"].get("status")
            print(f"Step {r['step_index']:02d} {r['action_type'].upper()}: {status}")
            if status not in ("success", "skipped"):
                print(f"  Error: {r['result'].get('error_message')}")
    else:
        # Fallback to old batch mode
        load_dotenv()
        
        # Set up Brave browser if using real browser
        if use_real_browser and browser_type.lower() == "brave":
            ensure_brave_remote_debugging()
        
        planner = AgentB()
        plan = planner.plan(task)
        
        executor_kwargs = {
            "driver_path": driver_path,
            "model": "gpt-4o",
        }
        
        if use_real_browser and browser_type.lower() == "brave":
            executor_kwargs.update({
                "use_real_browser": True,
                "browser_type": "brave",
                "cdp_url": "http://localhost:9222",
                "user_data_dir": os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser"),
                "profile_directory": "Default",
                "strict_real_browser": True,
                "force_kill_chrome": False,
            })
        
        executor = AgentA(**executor_kwargs)
        results = executor.execute_plan(plan)
        for r in results:
            status = r["result"].get("status")
            print(f"Step {r['step_index']:02d} {r['action_type'].upper()}: {status}")
            if status not in ("success", "skipped"):
                print(f"  Error: {r['result'].get('error_message')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.orchestrator \"<task description>\" [--batch]")
        sys.exit(1)
    task_arg = sys.argv[1]
    iterative = "--batch" not in sys.argv
    run(task_arg, iterative=iterative)




