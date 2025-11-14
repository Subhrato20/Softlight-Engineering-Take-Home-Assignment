# Intelligent Web Automation System

A two-agent system for intelligent web automation that captures UI states in real-time. Agent B (planner) analyzes screenshots and decides actions, while Agent A (executor) performs browser automation. Screenshots are captured independently using Playwright CDP.

## 🏗️ Architecture

```
User Task → Orchestrator → Agent B (Planner) → Agent A (Executor) → Browser
                ↓              ↑                    ↓
         Screenshots    (Playwright CDP)    (browser-use)
```

- **Agent B**: Analyzes screenshots using GPT-4o vision, decides next action
- **Agent A**: Executes actions using browser-use (LLM-powered element finding)
- **Orchestrator**: Coordinates agents and captures screenshots via Playwright CDP
- **Key Innovation**: Screenshots captured independently, ensuring reliable capture at every step

## ✨ Features

- **Vision-Based Planning**: GPT-4o analyzes UI screenshots semantically
- **Iterative Loop**: Adapts to dynamic UI states (modals, forms, etc.)
- **Independent Screenshots**: Playwright CDP capture (separate from browser-use)
- **Real Browser**: Works with your Brave/Chrome profile via CDP
- **Beautiful CLI**: Interactive interface with rich formatting
- **Generalizable**: Works with any web app, no hardcoded selectors

## 📋 Requirements

- Python 3.12+
- Brave Browser or Chrome
- OpenAI API key (`OPENAI_API_KEY`)
- Browser-use API key (optional, `BROWSER_USE_API_KEY`)

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up `.env`**:
   ```bash
   OPENAI_API_KEY=your_key_here
   ```

3. **Run the CLI**:
   ```bash
   python -m src.cli
   ```

   Or use command-line:
   ```bash
   python -m src.orchestrator "Create a new issue in Linear called 'Test Issue'"
   ```

## 🧪 How It Works

1. **Orchestrator** captures screenshot (Playwright CDP)
2. **Agent B** analyzes screenshot + history → decides action
3. **Agent A** executes action (browser-use finds elements, clicks, types)
4. **Orchestrator** captures new screenshot
5. Repeat until task complete

**Technology Split**:
- **browser-use**: Execution (actions, element finding)
- **Playwright**: Screenshots (direct CDP, independent)

## 📁 Project Structure

```
src/
├── agentA/          # Executor (browser-use)
├── agentB/          # Planner (GPT-4o vision)
├── orchestrator.py  # Main loop + screenshot capture
└── cli.py          # Interactive CLI
screenshots/         # Captured UI states
```

## 🛠️ Troubleshooting

**Screenshots not capturing?**
- Check CDP: `curl http://localhost:9222/json/version`
- Ensure browser has open pages
- Verify `screenshots/` directory is writable

**Browser connection issues?**
- Orchestrator handles browser setup automatically
- Close all browser instances before running

## 📝 Notes

- Screenshots saved to `screenshots/` with format: `step_{index}_{action}_{task}_{timestamp}.png`
- Browser state persists across actions (same process, fresh handlers)
- Designed for macOS/Brave, adaptable to other platforms
- Works with any web app - no hardcoded selectors needed

---

