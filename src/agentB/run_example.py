#!/usr/bin/env python3
"""Standalone example script for Agent B"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.agentB.agent_b import AgentB

# Load environment variables
load_dotenv()

def main():
    # Initialize Agent B
    try:
        agent = AgentB()
        print("✅ Agent B initialized successfully\n")
    except ValueError as e:
        print(f"❌ Error initializing Agent B: {e}")
        print("\nPlease set your OPENAI_API_KEY environment variable.")
        return
    
    # Example task
    task = "Create a new project in Linear"
    
    print(f"📋 Planning task: {task}\n")
    print("=" * 60)
    
    # Generate plan
    try:
        plan = agent.plan(task)
        
        print(f"\n🎯 Goal: {plan.goal}")
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
        
        print(f"\n{'=' * 60}")
        print(f"📝 EXECUTION PLAN ({len(plan.steps)} steps):")
        print("=" * 60)
        
        for i, step in enumerate(plan.steps, 1):
            print(f"\nStep {i}: {step.action_type.upper()}")
            print(f"  🎯 Target: {step.target_description}")
            if step.value:
                print(f"  📝 Value: {step.value}")
            if step.reasoning:
                print(f"  💡 Reasoning: {step.reasoning}")
            if step.expected_state_change:
                print(f"  🔄 Expected: {step.expected_state_change}")
            if step.capture_after:
                print(f"  📸 Screenshot will be captured")
            if step.wait_conditions:
                print(f"  ⏳ Wait for: {', '.join(step.wait_conditions)}")
        
        print(f"\n{'=' * 60}")
        print("✅ Plan generated successfully!")
        
        # Optionally save to JSON
        import json
        output_file = "plan_output.json"
        with open(output_file, "w") as f:
            json.dump(plan.model_dump(), f, indent=2)
        print(f"💾 Plan saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Error generating plan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


