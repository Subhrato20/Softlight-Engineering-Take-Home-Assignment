"""Example usage of Agent B"""

import os
from dotenv import load_dotenv
from .agent_b import AgentB

# Load environment variables
load_dotenv()

def main():
    # Initialize Agent B
    agent = AgentB()
    
    # Example task
    task = "Create a new project in Linear"
    
    print(f"Planning task: {task}\n")
    print("=" * 60)
    
    # Generate plan
    try:
        plan = agent.plan(task)
        
        print(f"\nGoal: {plan.goal}")
        print(f"Complexity: {plan.estimated_complexity}")
        print(f"\nAssumptions: {plan.assumptions}")
        print(f"\nPotential Issues: {plan.potential_issues}")
        print(f"\nSuccess Criteria: {plan.success_criteria}")
        
        print(f"\n{'=' * 60}")
        print(f"EXECUTION PLAN ({len(plan.steps)} steps):")
        print("=" * 60)
        
        for i, step in enumerate(plan.steps, 1):
            print(f"\nStep {i}: {step.action_type.upper()}")
            print(f"  Target: {step.target_description}")
            if step.value:
                print(f"  Value: {step.value}")
            if step.reasoning:
                print(f"  Reasoning: {step.reasoning}")
            if step.expected_state_change:
                print(f"  Expected: {step.expected_state_change}")
            if step.capture_after:
                print(f"  📸 Screenshot will be captured")
            if step.wait_conditions:
                print(f"  Wait for: {', '.join(step.wait_conditions)}")
        
        print(f"\n{'=' * 60}")
        print("Plan generated successfully!")
        
    except Exception as e:
        print(f"Error generating plan: {e}")

if __name__ == "__main__":
    main()

