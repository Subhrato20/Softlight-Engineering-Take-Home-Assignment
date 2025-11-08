#!/usr/bin/env python3
"""Interactive CLI for testing Agent B with custom tasks"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.agentB.agent_b import AgentB

# Load environment variables
load_dotenv()


def print_plan(plan, save_json=False):
    """Pretty print a TaskPlan"""
    print(f"\n{'=' * 70}")
    print(f"🎯 GOAL: {plan.goal}")
    print(f"{'=' * 70}")
    print(f"📊 Complexity: {plan.estimated_complexity}")
    
    if plan.assumptions:
        print(f"\n💭 Assumptions:")
        for assumption in plan.assumptions:
            print(f"   • {assumption}")
    
    if plan.potential_issues:
        print(f"\n⚠️  Potential Issues:")
        for issue in plan.potential_issues:
            print(f"   • {issue}")
    
    if plan.success_criteria:
        print(f"\n✅ Success Criteria:")
        for criterion in plan.success_criteria:
            print(f"   • {criterion}")
    
    print(f"\n{'=' * 70}")
    print(f"📝 EXECUTION PLAN ({len(plan.steps)} steps):")
    print(f"{'=' * 70}")
    
    for i, step in enumerate(plan.steps, 1):
        print(f"\n┌─ Step {i}: {step.action_type.upper()}")
        print(f"│  🎯 Target: {step.target_description}")
        if step.value:
            print(f"│  📝 Value: {step.value}")
        if step.reasoning:
            print(f"│  💡 Reasoning: {step.reasoning}")
        if step.expected_state_change:
            print(f"│  🔄 Expected: {step.expected_state_change}")
        if step.capture_after:
            print(f"│  📸 Screenshot will be captured")
        if step.wait_conditions:
            print(f"│  ⏳ Wait for: {', '.join(step.wait_conditions)}")
        print(f"└─")
    
    print(f"\n{'=' * 70}")
    print("✅ Plan generated successfully!")
    
    if save_json:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_goal = "".join(c for c in plan.goal[:30] if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        output_file = f"plan_{safe_goal}_{timestamp}.json"
        with open(output_file, "w") as f:
            json.dump(plan.model_dump(), f, indent=2)
        print(f"💾 Plan saved to {output_file}")


def main():
    """Interactive CLI for testing Agent B"""
    print("🤖 Agent B - Interactive Testing Mode")
    print("=" * 70)
    
    # Initialize Agent B
    try:
        agent = AgentB()
        print("✅ Agent B initialized successfully\n")
    except ValueError as e:
        print(f"❌ Error initializing Agent B: {e}")
        print("\nPlease set your OPENAI_API_KEY environment variable.")
        return
    
    auto_save = False
    print("Commands:")
    print("  - Enter a task to generate a plan")
    print("  - Type 'exit' or 'quit' to exit")
    print("  - Type 'help' for more options")
    print("  - Type 'save' to toggle auto-save JSON files")
    print("  - Type 'save on' or 'save off' to control saving\n")
    
    while True:
        try:
            # Get user input
            task = input("\n📋 Enter task (or 'help'/'exit'/'save'): ").strip()
            
            if not task:
                continue
            
            if task.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if task.lower() == 'help':
                print("\n📖 Available commands:")
                print("  - Enter any task description to generate a plan")
                print("  - 'save' - Toggle auto-save JSON files (currently: " + ("ON" if auto_save else "OFF") + ")")
                print("  - 'save on' - Enable auto-save")
                print("  - 'save off' - Disable auto-save")
                print("  - 'exit'/'quit' - Exit the program")
                print("\n💡 Example tasks:")
                print("  - Create a new project in Linear")
                print("  - Send an email in Gmail")
                print("  - Create a new issue in GitHub")
                print("  - Book a flight on Expedia")
                print("  - Add an item to cart on Amazon")
                continue
            
            if task.lower() in ['save', 'save on', 'save off']:
                if task.lower() == 'save':
                    auto_save = not auto_save
                elif task.lower() == 'save on':
                    auto_save = True
                else:
                    auto_save = False
                print(f"💾 Auto-save: {'ENABLED' if auto_save else 'DISABLED'}")
                continue
            
            # Generate plan
            print(f"\n🔄 Generating plan for: {task}")
            print("⏳ This may take a moment...\n")
            
            try:
                plan = agent.plan(task)
                print_plan(plan, save_json=auto_save)
            except Exception as e:
                print(f"\n❌ Error generating plan: {e}")
                import traceback
                traceback.print_exc()
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break


if __name__ == "__main__":
    main()


