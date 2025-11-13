"""Example usage of Agent A with Agent B"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.agentB.agent_b import AgentB
from src.agentA.agent_a import AgentA

# Load environment variables
load_dotenv()


def main():
    """Example: Plan with Agent B and execute with Agent A"""
    
    # Example task
    task = "Open Notion and create a new page"
    
    print("=" * 70)
    print("🤖 Agent A + Agent B Example")
    print("=" * 70)
    print(f"\nTask: {task}\n")
    
    # Step 1: Generate plan with Agent B
    print("📋 Step 1: Generating plan with Agent B...")
    try:
        planner = AgentB()
        plan = planner.plan(task)
        print(f"✅ Plan generated with {len(plan.steps)} steps\n")
    except Exception as e:
        print(f"❌ Error generating plan: {e}")
        return
    
    # Step 2: Execute plan with Agent A
    print("🚀 Step 2: Executing plan with Agent A...\n")
    try:
        executor = AgentA(headless=False)  # Set to True for headless mode
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

