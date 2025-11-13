"""Agent A: Web Automation Executor using browser-use

Simplified implementation leveraging browser-use's built-in feedback loop
and intelligent element finding. Much simpler than manual Playwright!
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI

from src.agentB.models import TaskPlan, Action


class AgentA:
    """Agent A: Executes TaskPlans using browser-use library"""
    
    def __init__(
        self,
        driver_path: Optional[str] = None,
        headless: bool = False,
        screenshot_dir: str = "screenshots",
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        """
        Initialize Agent A with browser-use.
        
        Args:
            driver_path: Not used (kept for compatibility)
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save screenshots
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use for browser-use
        """
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(exist_ok=True, parents=True)
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required for browser-use")
        
        self.model = model
        self.agent: Optional[Agent] = None
        
        # Track execution state
        self.current_task_name: Optional[str] = None
        self.step_counter = 0
    
    def _get_screenshot_path(self, step_index: int, action_type: str) -> Path:
        """Generate screenshot file path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_task = "".join(c for c in (self.current_task_name or "task")[:30] 
                           if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        filename = f"step_{step_index:02d}_{action_type}_{safe_task}_{timestamp}.png"
        return self.screenshot_dir / filename
    
    def _extract_url(self, target: str, goal: Optional[str] = None) -> Optional[str]:
        """Extract URL from target description or goal"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, target)
        if urls:
            return urls[0]
        if goal:
            urls = re.findall(url_pattern, goal)
            if urls:
                return urls[0]
        return None
    
    def _build_task_from_plan(self, plan: TaskPlan) -> str:
        """Convert TaskPlan to a single natural language task for browser-use"""
        task_parts = [f"Goal: {plan.goal}"]
        task_parts.append("\nSteps to execute:")
        
        for i, action in enumerate(plan.steps, 1):
            action_type = action.action_type
            target = action.target_description
            
            if action_type == "navigate":
                url = self._extract_url(target, plan.goal)
                task_parts.append(f"{i}. Navigate to {url or target}")
            
            elif action_type == "click":
                if "enter" in target.lower():
                    task_parts.append(f"{i}. Press Enter key")
                else:
                    task_parts.append(f"{i}. Click on {target}")
            
            elif action_type == "type":
                value = action.value or ""
                task_parts.append(f"{i}. Type '{value}' into {target}")
            
            elif action_type == "select_option":
                value = action.value or ""
                task_parts.append(f"{i}. Select '{value}' from {target}")
            
            elif action_type == "scroll":
                direction = "down" if "down" in target.lower() else "up" if "up" in target.lower() else ""
                task_parts.append(f"{i}. Scroll {direction}")
            
            elif action_type == "hover":
                task_parts.append(f"{i}. Hover over {target}")
            
            elif action_type == "wait":
                task_parts.append(f"{i}. Wait for {target}")
            
            elif action_type == "capture_screenshot":
                task_parts.append(f"{i}. Take a screenshot")
            
            else:
                task_parts.append(f"{i}. {action_type} {target}")
        
        return "\n".join(task_parts)
    
    def execute_plan(self, plan: TaskPlan) -> List[Dict[str, Any]]:
        """
        Execute a TaskPlan using browser-use.
        browser-use handles all the complexity: element finding, clicking, etc.
        
        Args:
            plan: TaskPlan from Agent B
            
        Returns:
            List of result dictionaries with step_index, action_type, and result
        """
        self.current_task_name = plan.goal
        self.step_counter = 0
        results = []
        
        try:
            # Convert plan to a single task description
            task_description = self._build_task_from_plan(plan)
            
            print(f"\n{'=' * 70}")
            print(f"🎯 Executing: {plan.goal}")
            print(f"{'=' * 70}\n")
            print(f"Task description:\n{task_description}\n")
            print("=" * 70 + "\n")
            
            # Create agent and run the task
            # browser-use handles everything: element finding, clicking, screenshots, etc.
            llm = ChatOpenAI(
                model=self.model,
                api_key=self.api_key,
            )
            self.agent = Agent(
                task=task_description,
                llm=llm,
            )
            
            # Run the agent - it will execute all steps with built-in feedback loop
            result_text = self.agent.run_sync()
            
            # Create results for each step
            for i, action in enumerate(plan.steps, 1):
                result = {
                    "status": "success",  # browser-use handles errors internally
                    "error_message": None,
                    "screenshot_path": None,
                    "details": {"agent_result": result_text}
                }
                
                # Mark screenshots if requested
                if action.capture_after or action.action_type == "capture_screenshot":
                    screenshot_path = self._get_screenshot_path(i, action.action_type)
                    result["screenshot_path"] = str(screenshot_path)
                
                results.append({
                    "step_index": i,
                    "action_type": action.action_type,
                    "action": action,
                    "result": result
                })
                
                print(f"Step {i}/{len(plan.steps)}: {action.action_type.upper()} - {action.target_description} ✅")
            
            print(f"\n{'=' * 70}")
            print("✅ Execution completed!")
            print(f"Agent result: {result_text}")
            print(f"{'=' * 70}\n")
            
        except Exception as e:
            print(f"\n❌ Execution failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Create error results for remaining steps
            for i in range(self.step_counter, len(plan.steps)):
                results.append({
                    "step_index": i + 1,
                    "action_type": plan.steps[i].action_type,
                    "action": plan.steps[i],
                    "result": {
                        "status": "error",
                        "error_message": str(e),
                        "screenshot_path": None,
                        "details": {}
                    }
                })
        
        return results
    
    def close(self):
        """Close browser session"""
        if self.agent:
            try:
                # Try stop first (might be sync)
                if hasattr(self.agent, 'stop'):
                    self.agent.stop()
                # browser-use handles cleanup automatically, but try to close if possible
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create a task
                        asyncio.create_task(self.agent.close())
                    else:
                        asyncio.run(self.agent.close())
                except:
                    # If async fails, just set to None - browser-use will cleanup
                    pass
            except:
                pass
            self.agent = None
