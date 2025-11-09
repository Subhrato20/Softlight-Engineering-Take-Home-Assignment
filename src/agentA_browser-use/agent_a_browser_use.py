"""Agent A Browser-Use: Executes TaskPlan using browser-use library

This implementation uses browser-use library which leverages LLM vision
to see and interact with the browser, making it more autonomous than
the Playwright-based approach.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agentB.models import TaskPlan, Action

try:
    from browser_use import Browser, BrowserConfig, Agent
    from browser_use.browser.browser import Browser as BrowserUseBrowser
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    print("Warning: browser-use not installed. Install with: pip install browser-use")


class AgentABrowserUse:
    """Agent A using browser-use library for autonomous browser automation"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        headless: bool = False,
        screenshot_dir: str = "screenshots_browser_use",
        model: str = "gpt-4o",
        user_data_dir: Optional[str] = None,
        connect_to_existing: bool = False,
        ws_endpoint: Optional[str] = None
    ):
        """
        Initialize Agent A Browser-Use.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            headless: Run browser in headless mode
            screenshot_dir: Directory to save screenshots
            model: LLM model to use (defaults to gpt-4o)
            user_data_dir: Optional directory for persistent browser data
            connect_to_existing: If True, connect to existing browser via CDP
            ws_endpoint: WebSocket endpoint for CDP connection
        """
        if not BROWSER_USE_AVAILABLE:
            raise ImportError(
                "browser-use library not installed. "
                "Install with: pip install browser-use"
            )
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.user_data_dir = user_data_dir
        self.connect_to_existing = connect_to_existing
        self.ws_endpoint = ws_endpoint or "http://localhost:9222"
        
        self.browser: Optional[BrowserUseBrowser] = None
        self.agent: Optional[Agent] = None
        self.execution_log: List[Dict[str, Any]] = []
        self.screenshot_count = 0
    
    def _initialize_browser(self):
        """Initialize browser-use browser instance"""
        config = BrowserConfig(
            headless=self.headless,
            user_data_dir=self.user_data_dir,
        )
        
        if self.connect_to_existing:
            # Connect to existing browser via CDP
            self.browser = Browser(config=config)
            # Note: browser-use may need custom CDP connection handling
            # This is a simplified version
        else:
            self.browser = Browser(config=config)
        
        # Initialize agent with the browser
        self.agent = Agent(
            task="",  # Will be set per action
            browser=self.browser,
            llm=self._get_llm()
        )
    
    def _get_llm(self):
        """Get LLM instance for browser-use"""
        from openai import OpenAI
        from browser_use import LLM
        
        client = OpenAI(api_key=self.api_key)
        return LLM(model=self.model, client=client)
    
    def _capture_screenshot(self, step_number: Optional[int] = None, description: Optional[str] = None) -> str:
        """Capture screenshot and return filepath"""
        self.screenshot_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if step_number is not None:
            filename = f"step_{step_number:03d}_{timestamp}.png"
        elif description:
            safe_desc = "".join(c for c in description[:30] if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            filename = f"{safe_desc}_{timestamp}.png"
        else:
            filename = f"screenshot_{self.screenshot_count:03d}_{timestamp}.png"
        
        filepath = self.screenshot_dir / filename
        
        if self.browser and hasattr(self.browser, 'page'):
            self.browser.page.screenshot(path=str(filepath), full_page=True)
        
        return str(filepath)
    
    def _action_to_instruction(self, action: Action) -> str:
        """Convert Action to natural language instruction for browser-use"""
        instruction_parts = []
        
        if action.action_type == "navigate":
            instruction_parts.append(f"Navigate to {action.target_description}")
        
        elif action.action_type == "click":
            instruction_parts.append(f"Click on the {action.target_description}")
            if action.reasoning:
                instruction_parts.append(f"({action.reasoning})")
        
        elif action.action_type == "type":
            instruction_parts.append(f"Type '{action.value}' into the {action.target_description}")
            if action.reasoning:
                instruction_parts.append(f"({action.reasoning})")
        
        elif action.action_type == "select_option":
            instruction_parts.append(f"Select '{action.value}' from the {action.target_description}")
        
        elif action.action_type == "hover":
            instruction_parts.append(f"Hover over the {action.target_description}")
        
        elif action.action_type == "scroll":
            instruction_parts.append(f"Scroll the page")
        
        elif action.action_type == "wait":
            if action.wait_conditions:
                instruction_parts.append(f"Wait for: {', '.join(action.wait_conditions)}")
            else:
                instruction_parts.append("Wait a moment")
        
        elif action.action_type == "evaluate_state":
            if action.expected_state_change:
                instruction_parts.append(f"Verify that {action.expected_state_change}")
        
        return ". ".join(instruction_parts) if instruction_parts else action.target_description
    
    def execute(self, plan: TaskPlan) -> Dict[str, Any]:
        """
        Execute a TaskPlan from Agent B using browser-use.
        
        Args:
            plan: TaskPlan object from Agent B
        
        Returns:
            dict: Execution result with screenshots and log
        """
        self.execution_log = []
        self.screenshot_count = 0
        
        # Initialize browser
        self._initialize_browser()
        
        try:
            # Execute each step in the plan
            for step_idx, action in enumerate(plan.steps, 1):
                step_result = self._execute_action(action, step_idx, plan.goal)
                self.execution_log.append({
                    "step": step_idx,
                    "action": action.action_type,
                    "target": action.target_description,
                    "result": step_result
                })
                
                # Check if step failed critically
                if not step_result.get("success", False) and action.action_type in ["navigate", "click"]:
                    return {
                        "success": False,
                        "error": f"Step {step_idx} failed: {step_result.get('error', 'Unknown error')}",
                        "completed_steps": step_idx - 1,
                        "total_steps": len(plan.steps),
                        "screenshots": self._get_screenshot_paths()
                    }
            
            return {
                "success": True,
                "goal": plan.goal,
                "completed_steps": len(plan.steps),
                "screenshots": self._get_screenshot_paths(),
                "execution_log": self.execution_log
            }
        
        finally:
            # Cleanup
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
    
    def _execute_action(self, action: Action, step_number: int, goal: str) -> Dict[str, Any]:
        """Execute a single action using browser-use"""
        try:
            # Convert action to instruction
            instruction = self._action_to_instruction(action)
            
            # Create task description that includes context
            task_description = f"""
Goal: {goal}

Current step ({step_number}): {instruction}

Expected outcome: {action.expected_state_change or 'Continue to next step'}
"""
            
            # Update agent task
            self.agent.task = task_description
            
            # Execute using browser-use agent
            # browser-use will use vision to see the page and execute the action
            result = self.agent.run()
            
            # Capture screenshot if required
            screenshot_path = None
            if action.capture_after:
                screenshot_path = self._capture_screenshot(
                    step_number=step_number,
                    description=action.target_description
                )
            
            # Wait for conditions if specified
            if action.wait_conditions:
                import time
                time.sleep(2)  # Simple wait, browser-use handles more complex waits
            
            return {
                "success": True,
                "instruction": instruction,
                "result": str(result) if result else "Completed",
                "screenshot": screenshot_path
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "instruction": self._action_to_instruction(action)
            }
    
    def _get_screenshot_paths(self) -> List[str]:
        """Get list of screenshot file paths"""
        screenshots = sorted(self.screenshot_dir.glob("*.png"))
        return [str(s) for s in screenshots]

