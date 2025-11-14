# Intelligent Web Automation System

A sophisticated two-agent system for intelligent web automation that combines AI-powered planning with robust browser automation. The system uses an iterative feedback loop where a planning agent (Agent B) analyzes the current UI state and decides the next action, while an execution agent (Agent A) performs the actual browser automation.

## 🏗️ Architecture

The system consists of two specialized agents working in tandem:

- **Agent B (Planner)**: An intelligent reasoning agent that analyzes screenshots and execution history to decide the next action. Uses vision-capable LLMs (GPT-4o) to understand UI state and make adaptive decisions.

- **Agent A (Executor)**: A robust browser automation agent that executes actions using the `browser-use` library. Handles browser connection management, state persistence, and error recovery.

### How It Works

```
┌─────────────┐
│  User Task  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│           Orchestrator                          │
│  (Manages iterative feedback loop)              │
└──────┬──────────────────────────────┬─────────┘
       │                                │
       ▼                                ▼
┌──────────────┐                ┌──────────────┐
│  Agent B     │                │  Agent A     │
│  (Planner)   │◄─── Screenshot │  (Executor)  │
│              │    + History   │              │
│  Decides     │                │  Executes    │
│  Next Action │───────────────►│  Action      │
└──────────────┘   Action        └──────────────┘
```

1. **Agent B** analyzes the current state (screenshot + execution history) and decides the next action
2. **Agent A** executes the action using browser-use
3. **Agent A** captures a screenshot of the new state
4. **Agent B** analyzes the new state and decides the next action
5. Process repeats until the task is complete

## ✨ Features

- **Iterative Planning**: Dynamic, adaptive planning based on real-time UI state analysis
- **Vision-Based Decision Making**: Uses GPT-4o vision to understand UI screenshots
- **State Persistence**: Maintains browser state across actions using CDP (Chrome DevTools Protocol)
- **Robust Error Handling**: Automatic recovery from browser connection issues
- **Real Browser Support**: Works with your actual browser profile (Brave/Chrome) via CDP
- **Screenshot Capture**: Automatic screenshot capture at key UI state changes
- **Type-Safe Plans**: Uses Pydantic models for structured, validated action plans

## 📋 Requirements

- Python 3.12+
- Brave Browser or Google Chrome (for CDP connection)
- OpenAI API key (for Agent B planning and vision capabilities)
- Browser-use API key (optional, for ChatBrowserUse models)

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Softlight-Engineering-Take-Home-Assignment
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   
   Create a `.env` file in the root directory:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   BROWSER_USE_API_KEY=your_browser_use_api_key_here  # Optional
   ```

## 🎯 Quick Start

### Interactive CLI (Recommended)

Use the beautiful interactive CLI for the best experience:

```bash
python -m src.cli
```

The CLI will:
1. Display a welcome banner
2. Prompt you to enter your task in a nice input box
3. Show examples to guide you
4. Execute the task with real-time progress
5. Display a formatted summary of results

### Command-Line Usage

Alternatively, run tasks directly from the command line:

```bash
python -m src.orchestrator "Create a new issue in Linear called 'Test Issue' and save it"
```

The orchestrator will:
1. Set up the browser connection (Brave/Chrome via CDP)
2. Initialize Agent B (planner) and Agent A (executor)
3. Run the iterative feedback loop until the task is complete

### Example Tasks

```bash
# Navigate and interact
python -m src.orchestrator "Navigate to https://linear.app and create a new issue"

# Complex multi-step task
python -m src.orchestrator "Create a new project in Linear called 'Q4 Planning' with description 'Planning for Q4 2024'"

# Form filling
python -m src.orchestrator "Fill out the contact form on example.com with name 'John Doe' and email 'john@example.com'"
```

## 📖 Usage Examples

### Using Agents Directly

#### Agent B (Planner)

```python
from src.agentB.agent_b import AgentB

# Initialize planner
planner = AgentB()

# Generate a plan from natural language
plan = planner.plan("Create a new project in Linear")
print(f"Goal: {plan.goal}")
print(f"Steps: {len(plan.steps)}")

# Iterative decision making
action = planner.decide_next_action(
    task="Create a new issue",
    screenshot_path="screenshots/current_state.png",
    execution_history=[],
    current_url="https://linear.app"
)
print(f"Next action: {action.action_type} - {action.target_description}")
```

#### Agent A (Executor)

```python
from src.agentA.agent_a import AgentA
from src.agentB.models import Action

# Initialize executor
executor = AgentA(
    use_real_browser=True,
    browser_type="brave",
    cdp_url="http://localhost:9222",
    headless=False
)

# Execute a single action
action = Action(
    action_type="navigate",
    target_description="https://linear.app"
)
result = executor.execute_single_action(action, step_index=1)
print(f"Status: {result['result']['status']}")
```

### Using the Orchestrator Programmatically

```python
from src.orchestrator import run_iterative

# Run iterative execution
results = run_iterative(
    task="Create a new issue in Linear called 'Test Issue'",
    use_real_browser=True,
    browser_type="brave",
    max_steps=50
)

# Review results
for result in results:
    print(f"Step {result['step_index']}: {result['action_type']} - {result['result']['status']}")
```

## 🔧 Configuration

### Browser Setup

The system supports two browser modes:

1. **Real Browser (CDP)**: Connects to your existing Brave/Chrome browser
   - Uses your actual browser profile
   - Maintains login sessions and cookies
   - Requires browser to be running with remote debugging enabled
   - Automatically handled by the orchestrator

2. **Managed Browser**: Browser-use manages its own browser instance
   - Clean browser session each run
   - No profile persistence

### Model Configuration

Agent B uses GPT-4o by default for vision capabilities. You can customize:

```python
# Use a different model
planner = AgentB(model="gpt-4o")
```

Agent A supports:
- `ChatBrowserUse` (if `BROWSER_USE_API_KEY` is set): Uses `bu-latest` or `bu-1-0` models
- `ChatOpenAI`: Uses GPT models like `gpt-4o`, `gpt-4`, etc.

## 📁 Project Structure

```
.
├── src/
│   ├── agentA/              # Execution agent
│   │   ├── agent_a.py       # Main executor implementation
│   │   ├── example_usage.py  # Usage examples
│   │   └── README.md        # Agent A documentation
│   ├── agentB/              # Planning agent
│   │   ├── agent_b.py       # Main planner implementation
│   │   ├── models.py        # Pydantic models (TaskPlan, Action)
│   │   ├── interactive_agent.py  # Interactive mode
│   │   └── README.md        # Agent B documentation
│   └── orchestrator.py      # Main orchestrator (iterative loop)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🧪 How It Works

### Iterative Execution Flow

1. **Initialization**:
   - Orchestrator sets up browser connection (CDP or managed)
   - Initializes Agent B (planner) and Agent A (executor)

2. **Iteration Loop**:
   ```
   For each step:
     a. Agent B analyzes:
        - Current screenshot (if available)
        - Execution history
        - Current URL
        - Original task
     
     b. Agent B decides next action
     
     c. Agent A executes action:
        - Creates fresh browser connection (for CDP)
        - Executes action using browser-use
        - Captures screenshot
     
     d. Agent B evaluates if task is complete
     
     e. If not complete, repeat from step a
   ```

3. **State Management**:
   - Browser state persists across actions (same browser process)
   - Each Agent instance gets fresh handlers to avoid state conflicts
   - Screenshots captured after each action for Agent B analysis

### Browser Connection Management

The system handles browser-use's state clearing by:
- Recreating the Browser connection for each action (when using CDP)
- Maintaining the underlying browser process and page state
- Ensuring fresh event handlers for each Agent instance

## 🛠️ Troubleshooting

### Browser Connection Issues

If you see "Could not access browser page" errors:

1. **Ensure browser is running with remote debugging**:
   ```bash
   # The orchestrator handles this automatically, but you can manually:
   # Brave: /Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222
   ```

2. **Check CDP endpoint**:
   ```bash
   curl http://localhost:9222/json/version
   ```

3. **Close all browser instances** before running (orchestrator handles this)

### API Key Issues

- Ensure `OPENAI_API_KEY` is set in `.env` or environment
- For browser-use models, set `BROWSER_USE_API_KEY` (optional)

### Screenshot Capture Issues

If screenshots aren't being captured:
- Check that the browser connection is valid
- Ensure the page has loaded (wait conditions may be needed)
- Check `screenshots/` directory permissions

## 📝 Notes

- The system is designed for macOS with Brave Browser, but can be adapted for other platforms
- Browser-use clears session state after each task - the system handles this by recreating connections
- Screenshots are saved in the `screenshots/` directory with timestamps
- The iterative approach allows for adaptive planning based on actual UI state

## 📄 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines if applicable]

---

Built with ❤️ using `browser-use`, `OpenAI`, and `Playwright`
