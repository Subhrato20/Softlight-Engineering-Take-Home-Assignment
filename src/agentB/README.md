# Agent B: Intelligent Task Planner

Agent B is a reasoning-powered planner that converts natural language task descriptions into structured, executable plans for web automation.

## Features

- **Reasoning Capabilities**: Uses advanced models (GPT-5, o1, GPT-4o) with fallback support
- **Structured Output**: Returns validated Pydantic models for type safety
- **Generalizable Plans**: Creates plans that work across different web applications
- **State-Aware**: Identifies when to capture screenshots based on UI state changes
- **Error Handling**: Includes potential issues and success criteria in plans

## Installation

```bash
pip install -r requirements.txt
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_api_key_here
```

Or create a `.env` file:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

```python
from src.agentB import AgentB

# Initialize Agent B
agent = AgentB()

# Generate a plan
task = "Create a new project in Linear"
plan = agent.plan(task)

# Access the plan
print(f"Goal: {plan.goal}")
print(f"Steps: {len(plan.steps)}")

for step in plan.steps:
    print(f"- {step.action_type}: {step.target_description}")
    if step.capture_after:
        print("  📸 Screenshot")
```

### Plan Structure

The `TaskPlan` object contains:

- **goal**: Original task description
- **steps**: List of `Action` objects
- **assumptions**: Assumptions about user state/website
- **potential_issues**: Edge cases to watch for
- **success_criteria**: How to verify completion
- **estimated_complexity**: simple | moderate | complex

Each `Action` includes:

- **action_type**: navigate, click, type, wait, capture_screenshot, etc.
- **target_description**: Natural language description of element
- **value**: Input value (for type/select actions)
- **expected_state_change**: What should happen
- **capture_after**: Whether to screenshot
- **reasoning**: Why this action is needed
- **wait_conditions**: Conditions to wait for

### Model Selection

Agent B automatically tries models in this order:
1. GPT-5 (if available)
2. o1-preview (reasoning model)
3. o1-mini (smaller reasoning model)
4. GPT-4o (fallback)

You can specify a model explicitly:

```python
agent = AgentB(model="o1-preview")
```

### Refining Plans

```python
# Refine a plan based on feedback
refined_plan = agent.refine_plan(plan, "The user is already logged in")
```

## Example Output

For task: "Create a new project in Linear"

```json
{
  "goal": "Create a new project in Linear",
  "steps": [
    {
      "action_type": "navigate",
      "target_description": "Linear application homepage",
      "expected_state_change": "Page loads with Linear interface",
      "capture_after": true
    },
    {
      "action_type": "click",
      "target_description": "Create Project button or menu item",
      "expected_state_change": "Create project modal opens",
      "capture_after": true,
      "reasoning": "Need to open the project creation interface"
    },
    {
      "action_type": "type",
      "target_description": "Project name input field",
      "value": "My New Project",
      "expected_state_change": "Text appears in input field",
      "capture_after": true
    },
    {
      "action_type": "click",
      "target_description": "Create or Submit button",
      "expected_state_change": "Project is created, success message appears",
      "capture_after": true
    }
  ],
  "assumptions": [
    "User is logged into Linear",
    "User has permission to create projects"
  ],
  "potential_issues": [
    "Modal might not open if button is disabled",
    "Form validation errors might appear",
    "Network errors during submission"
  ],
  "success_criteria": [
    "New project appears in project list",
    "Success notification is visible",
    "URL changes to project page"
  ]
}
```

## Integration

Agent B is designed to work with Agent A (the executor). The structured plan output can be directly consumed by Agent A to perform the actual browser automation.


