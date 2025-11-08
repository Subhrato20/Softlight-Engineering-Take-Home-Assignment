# Agent A: Web Automation Executor

Agent A executes structured task plans from Agent B using browser automation with Playwright and GPT-4o function calling.

## Features

- **Semantic Element Finding**: Uses GPT-4o to find elements based on natural language descriptions
- **Playwright Integration**: Full browser automation capabilities
- **Screenshot Capture**: Automatic screenshot capture at key moments
- **State Evaluation**: LLM-powered state change detection
- **Function Calling**: GPT-4o with tool calling for intelligent execution

## Installation

```bash
pip install -r requirements.txt
playwright install chromium  # Install browser binaries
```

## Architecture

```
src/agentA/
├── agent_a.py              # Main Agent A class
├── playwright/             # Playwright tools
│   ├── browser.py          # Browser management
│   ├── navigation.py       # Navigation tools
│   ├── page_analyzer.py    # Page content extraction
│   ├── element_finder.py   # Semantic element finding (LLM-powered)
│   ├── interactions.py      # Click, type, select, etc.
│   ├── state_evaluator.py   # State checking and evaluation
│   └── screenshot.py       # Screenshot capture
└── models.py               # Pydantic models (if needed)
```

## Usage

### Basic Usage

```python
from src.agentB import AgentB
from src.agentA import AgentA

# Step 1: Generate plan with Agent B
agent_b = AgentB()
plan = agent_b.plan("Create a new project in Linear")

# Step 2: Execute plan with Agent A
agent_a = AgentA(headless=False)  # Set headless=True for background execution
result = agent_a.execute(plan)

# Check results
if result["success"]:
    print(f"✅ Task completed!")
    print(f"Screenshots saved: {len(result['screenshots'])}")
    for screenshot in result["screenshots"]:
        print(f"  - {screenshot}")
else:
    print(f"❌ Task failed: {result.get('error')}")
```

### With Orchestrator

```python
from src.orchestrator import Orchestrator

orchestrator = Orchestrator()
result = orchestrator.execute_task("Create a new project in Linear")
```

## How It Works

1. **Receives TaskPlan**: Gets structured plan from Agent B
2. **Initializes Browser**: Launches Playwright browser
3. **Executes Steps**: For each action in the plan:
   - Uses semantic element finding to locate elements
   - Performs the required action (click, type, etc.)
   - Verifies state changes if specified
   - Captures screenshots when required
4. **Returns Results**: Screenshots and execution log

## Key Components

### Element Finder
Uses GPT-4o to semantically match natural language descriptions to actual page elements:
- Extracts page content (buttons, inputs, links)
- Sends to LLM with description
- Returns best matching selector

### State Evaluator
Uses LLM to detect UI state changes:
- Compares before/after page states
- Detects modals, forms, success messages
- Verifies expected changes occurred

### Screenshot Tools
Captures screenshots at key moments:
- Sequential naming (step_001, step_002, etc.)
- Full page or element screenshots
- Organized in output directory

## Configuration

```python
agent_a = AgentA(
    api_key="your-api-key",      # Optional, uses OPENAI_API_KEY env var
    headless=False,               # Run browser in background
    browser_type="chromium",      # "chromium", "firefox", or "webkit"
    screenshot_dir="screenshots"  # Directory for screenshots
)
```

## Function Tools Available to GPT-4o

- `find_element_by_description` - Semantic element finding
- `click_element` - Click elements
- `type_text` - Type into inputs
- `select_option` - Select dropdown options
- `navigate` - Navigate to URLs
- `capture_screenshot` - Take screenshots
- `wait_for_condition` - Wait for conditions
- `evaluate_state_change` - Verify state changes

## Error Handling

Agent A includes comprehensive error handling:
- Element not found → Tries alternative selectors
- Action fails → Logs error and continues or stops
- State change not detected → Reports issue
- Screenshot failures → Logs but continues

## Output

Returns dictionary with:
- `success`: Boolean indicating completion
- `goal`: Original task goal
- `completed_steps`: Number of steps completed
- `screenshots`: List of screenshot file paths
- `execution_log`: Detailed log of each step

## Integration with Agent B

Agent A is designed to work seamlessly with Agent B:
- Consumes `TaskPlan` objects directly
- Executes `Action` objects from the plan
- Uses semantic descriptions from Agent B
- Captures screenshots when `capture_after=True`

