"""Example usage of Agent A with Agent B"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.agentB import AgentB
from src.agentA import AgentA

# Load environment variables
load_dotenv()


def main():
    """Example: Create a project in Linear"""
    
    print("=" * 70)
    print("Agent A + Agent B Integration Example")
    print("=" * 70)
    
    # Step 1: Generate plan with Agent B
    print("\n📋 Step 1: Generating plan with Agent B...")
    agent_b = AgentB()
    task = "Create a new page in Notion"
    plan = agent_b.plan(task)
    
    print(f"✅ Plan generated: {len(plan.steps)} steps")
    print(f"   Goal: {plan.goal}")
    print(f"   Complexity: {plan.estimated_complexity}")
    
    # Step 2: Execute plan with Agent A
    print("\n🤖 Step 2: Executing plan with Agent A...")
    print("   (Browser will open - you can watch the automation)")
    
    # Option 1: Connect to existing browser (recommended - uses your current Chrome session)
    # First, start Chrome with: /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
    agent_a = AgentA(
        headless=False,
        screenshot_dir="screenshots",
        connect_to_existing=True,  # Connect to your existing Chrome browser
        ws_endpoint="http://localhost:9222"  # Default CDP endpoint
    )
    
    # Option 2: Use persistent context (alternative - creates separate browser profile)
    # agent_a = AgentA(
    #     headless=False,
    #     screenshot_dir="screenshots",
    #     user_data_dir="./browser_data"  # Persistent browser data - keeps you logged in!
    # )
    
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

