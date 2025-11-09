# Agent A Browser-Use: Vision-Based Browser Automation

This is an alternative implementation of Agent A using the `browser-use` library, which leverages LLM vision models to see and interact with the browser autonomously.

## Key Differences from Agent A (Playwright)

| Feature | Agent A (Playwright) | Agent A Browser-Use |
|---------|---------------------|---------------------|
| **Approach** | DOM-based element finding | Vision-based (sees the page) |
| **Intelligence** | Semantic text matching | Full visual understanding |
| **Autonomy** | Follows structured plan | More autonomous decisions |
| **Screenshot Usage** | Documentation only | Used for vision input |
| **Element Finding** | DOM analysis + LLM | Visual recognition via LLM |

## How Browser-Use Works

1. **Vision Input**: Takes screenshots of the browser
2. **LLM Analysis**: Sends screenshots to vision model (GPT-4o)
3. **Autonomous Actions**: LLM decides what to click/type based on what it sees
4. **Natural Instructions**: Converts Agent B's plan into natural language

## Installation

```bash
pip install browser-use
```

Or add to requirements.txt:
```
browser-use>=0.1.0
```

## Usage

```python
from src.agentB import AgentB
from src.agentA_browser_use import AgentABrowserUse

# Generate plan
agent_b = AgentB()
plan = agent_b.plan("Create a new page in Notion")

# Execute with browser-use
agent_a = AgentABrowserUse(
    headless=False,
    screenshot_dir="screenshots_browser_use",
    model="gpt-4o"
)

result = agent_a.execute(plan)
```

## Advantages of Browser-Use

1. **Visual Understanding**: Can see the page like a human
2. **More Autonomous**: Makes decisions based on visual context
3. **Better for Complex UIs**: Handles visual elements better
4. **Natural Interaction**: Uses natural language instructions

## Disadvantages

1. **Slower**: Takes screenshots and processes with vision model
2. **More Expensive**: Vision API calls cost more
3. **Less Precise**: May make mistakes in element identification
4. **Dependency**: Requires browser-use library

## When to Use

- **Use Browser-Use** when:
  - Complex visual interfaces
  - Need more autonomous behavior
  - DOM structure is unreliable
  - Visual elements are important

- **Use Playwright (Agent A)** when:
  - Need precise control
  - Speed is important
  - Cost is a concern
  - DOM structure is reliable

## Comparison Test

Run both implementations and compare:

```bash
# Test Playwright version
python src/agentA/example_usage.py

# Test Browser-Use version
python src/agentA_browser-use/example_usage.py
```

Compare:
- Success rate
- Execution time
- Cost (API calls)
- Screenshot quality
- Error handling

