"""Example usage of Agent A Browser-Use with Agent B"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.agentB import AgentB

# Import with hyphenated module name
import importlib.util
spec = importlib.util.spec_from_file_location(
    "agent_a_browser_use",
    str(Path(__file__).parent / "agent_a_browser_use.py")
)
agent_a_browser_use = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_a_browser_use)
AgentABrowserUse = agent_a_browser_use.AgentABrowserUse

# Load environment variables
load_dotenv()


def main():
    """Example: Create a page in Notion using browser-use"""
    
    print("=" * 70)
    print("Agent A Browser-Use + Agent B Integration Example")
    print("=" * 70)
    print("This uses browser-use library which leverages LLM vision")
    print("to autonomously interact with the browser.")
    print("=" * 70)
    
    # Step 1: Generate plan with Agent B
    print("\n📋 Step 1: Generating plan with Agent B...")
    agent_b = AgentB()
    task = "Create a new page in Notion"
    plan = agent_b.plan(task)
    
    print(f"✅ Plan generated: {len(plan.steps)} steps")
    print(f"   Goal: {plan.goal}")
    print(f"   Complexity: {plan.estimated_complexity}")
    
    # Step 2: Execute plan with Agent A Browser-Use
    print("\n🤖 Step 2: Executing plan with Agent A Browser-Use...")
    print("   (Browser will open - browser-use will use vision to interact)")
    
    agent_a = AgentABrowserUse(
        headless=False,
        screenshot_dir="screenshots_browser_use",
        model="gpt-4o"
    )
    
    try:
        result = agent_a.execute(plan)
        
        # Display results
        print("\n" + "=" * 70)
        if result["success"]:
            print("✅ TASK COMPLETED SUCCESSFULLY!")
            print(f"   Completed {result['completed_steps']} steps")
            print(f"   Screenshots captured: {len(result['screenshots'])}")
            print("\n   Screenshot files:")
            for screenshot in result["screenshots"]:
                print(f"     - {screenshot}")
        else:
            print("❌ TASK FAILED")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            print(f"   Completed {result.get('completed_steps', 0)} steps")
        
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n⚠️  Execution interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

