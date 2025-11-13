# Agent A: Web Automation Executor

Agent A is the execution engine that takes structured TaskPlans from Agent B and performs web automation tasks using **browser-use**. 

## Why browser-use?

- **Built-in feedback loop**: Automatically handles retries and error recovery
- **Intelligent element finding**: Uses LLM to find elements semantically
- **Simple API**: No need for complex selector logic or manual element finding
- **Much less code**: ~180 lines vs 600+ lines with manual Playwright

## Features

- **Browser Automation**: Uses browser-use library (built on Playwright)
- **Automatic Element Finding**: browser-use uses LLM to find elements by description
- **Feedback Loop**: Built-in retry and error handling
- **Screenshot Capture**: Automatically captures screenshots at key UI states
- **Action Support**: Supports all action types from Agent B by converting them to natural language

## Installation

Agent A requires browser-use. Install it with:

```bash
pip install -r requirements.txt
```

Set your OpenAI API key (optional, but recommended for better element finding):

```bash
export OPENAI_API_KEY="sk-...your_key..."
```

## Usage

### Basic Usage

```python
from src.agentB.agent_b import AgentB
from src.agentA.agent_a import AgentA

# Generate plan with Agent B
planner = AgentB()
plan = planner.plan("Create a new project in Linear")

# Execute plan with Agent A
executor = AgentA(headless=False)
results = executor.execute_plan(plan)

# Close browser when done
executor.close()
```

### With Orchestrator

```bash
python -m src.orchestrator "Navigate to https://www.google.com and search for Softlight Engineering"
```

### Example Script

```bash
python src/agentA/example_usage.py
```

## How It Works

### Simple and Clean

Agent A converts the structured TaskPlan from Agent B into a natural language task description, then passes it to browser-use's `Agent.run()`. 

**That's it!** browser-use handles:
- Element finding (using LLM)
- Clicking, typing, scrolling
- Error handling and retries
- Screenshot capture
- State management

### Task Conversion

The TaskPlan is converted to a step-by-step natural language description:
```
Goal: Navigate to Google and search
Steps:
1. Navigate to https://www.google.com
2. Type 'Softlight Engineering' into search input field
3. Click on Google Search button
```

browser-use then executes this using its built-in feedback loop and intelligent element finding.

### Execution Results

Each action returns a result dictionary:
```python
{
    "step_index": 1,
    "action_type": "click",
    "action": Action(...),
    "result": {
        "status": "success" | "error" | "pending",
        "error_message": None | str,
        "screenshot_path": None | str,
        "details": {...}
    }
}
```

## Configuration

### Initialization Parameters

- `driver_path`: Kept for compatibility (not used with Playwright)
- `headless`: Run browser in headless mode (default: False)
- `screenshot_dir`: Directory for screenshots (default: "screenshots")
- `api_key`: OpenAI API key (defaults to OPENAI_API_KEY env var)
- `model`: Model for element finding (default: "gpt-4o-mini")

## Error Handling

Agent A includes robust error handling:
- Element not found: Tries multiple finding strategies
- Timeout errors: Provides clear error messages
- Action failures: Continues execution and reports errors
- Browser errors: Gracefully handles browser crashes

## Limitations

- Element finding relies on visible elements and semantic descriptions
- Complex dynamic UIs may require more specific descriptions
- Some SPAs may need additional wait conditions
- Rate limiting may affect LLM-powered element finding

## Integration with Agent B

Agent A is designed to work seamlessly with Agent B:

1. Agent B generates a TaskPlan with structured actions
2. Agent A executes each action in sequence
3. Screenshots are captured at key states
4. Results are returned for analysis

See `src/orchestrator.py` for the complete integration example.

