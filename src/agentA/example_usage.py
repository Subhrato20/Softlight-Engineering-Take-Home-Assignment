"""Example usage of Agent A with Agent B"""

import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.agentB.agent_b import AgentB
from src.agentA.agent_a import AgentA

# Load environment variables
load_dotenv()


def _kill_existing_brave_processes(user_data_dir: str | None = None) -> None:
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
    last_error: Exception | None = None
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


def main():
    """Example: Plan with Agent B and execute with Agent A"""
    
    # Example task
    task = "create a project in Linear?"
    
    print("=" * 70)
    print("🤖 Agent A + Agent B Example")
    print("=" * 70)
    print(f"\nTask: {task}\n")
    debug_port = 9222
    brave_profile_directory = "Default"
    ensure_brave_remote_debugging(
        port=debug_port,
        profile_directory=brave_profile_directory,
    )

    # Step 1: Generate plan with Agent B
    print("📋 Step 1: Generating plan with Agent B...")
    try:
        planner = AgentB()
        plan = planner.plan(task)
        print(f"✅ Plan generated with {len(plan.steps)} steps\n")
    except Exception as e:
        print(f"❌ Error generating plan: {e}")
        return
    
    # Step 2: Execute plan with Agent A (attach to running Chrome via CDP)
    print("🚀 Step 2: Executing plan with Agent A...\n")
    try:
        # Option A: Attach to Brave you started with --remote-debugging-port=9222
        #   macOS launch example (run in a separate terminal first):
        #   /Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser \
        #       --remote-debugging-port=9222 \
        #       --user-data-dir="$HOME/Library/Application Support/BraveSoftware/Brave-Browser" \
        #       --profile-directory="Default"
        executor = AgentA(
            use_real_browser=True,
            browser_type="brave",
            cdp_url=f"http://localhost:{debug_port}",
            user_data_dir=os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser'),
            profile_directory='Default',
            headless=True,
            strict_real_browser=True,
            force_kill_chrome=False,
            model='gpt-4o',
        )

        # Option B: Let AgentA launch Brave itself (requires Brave fully closed)
        # executor = AgentA(
        #     use_real_browser=True,
        #     browser_type="brave",
        #     executable_path='/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
        #     user_data_dir=os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser'),
        #     profile_directory='Default',
        #     headless=False,
        #     model='gpt-4o',
        # )
        results = executor.execute_plan(plan)
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 Execution Summary")
        print("=" * 70)
        
        success_count = sum(1 for r in results if r["result"]["status"] == "success")
        print(f"\n✅ Successful steps: {success_count}/{len(results)}")
        
        if success_count < len(results):
            print("\n⚠️  Failed steps:")
            for r in results:
                if r["result"]["status"] != "success":
                    print(f"  Step {r['step_index']}: {r['action_type']} - {r['result'].get('error_message')}")
        
        print("\n💡 Tip: Check the screenshots/ directory for captured screenshots")
        print("=" * 70)
        
        # Keep browser open for a few seconds to see results
        import time
        print("\nBrowser will close in 5 seconds...")
        time.sleep(5)
        executor.close()
        
    except Exception as e:
        print(f"❌ Error executing plan: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
