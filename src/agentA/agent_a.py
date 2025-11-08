"""Agent A: Web Automation Executor with GPT-4o Function Calling"""

import os
import sys
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agentB.models import TaskPlan, Action
from .browser_tools import (
    BrowserManager,
    NavigationTools,
    PageAnalyzer,
    ElementFinder,
    InteractionTools,
    StateEvaluator,
    ScreenshotTools
)


class AgentA:
    """Agent A: Executes TaskPlan from Agent B using browser automation"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        headless: bool = False,
        browser_type: str = "chromium",
        screenshot_dir: str = "screenshots",
        user_data_dir: Optional[str] = None,
        connect_to_existing: bool = False,
        ws_endpoint: Optional[str] = None
    ):
        """
        Initialize Agent A.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            headless: Run browser in headless mode (ignored if connect_to_existing=True)
            browser_type: "chromium", "firefox", or "webkit"
            screenshot_dir: Directory to save screenshots
            user_data_dir: Optional directory to save browser data (cookies, localStorage, etc.)
                          If provided, uses persistent context to maintain login sessions.
                          Example: "./browser_data" - you'll stay logged in across runs!
            connect_to_existing: If True, connect to your existing Chrome browser (where you're already logged in)
            ws_endpoint: WebSocket endpoint for CDP connection (defaults to http://localhost:9222)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.headless = headless
        self.browser_type = browser_type
        self.screenshot_dir = screenshot_dir
        self.user_data_dir = user_data_dir
        self.connect_to_existing = connect_to_existing
        self.ws_endpoint = ws_endpoint
        
        # Will be initialized when execute() is called
        self.browser_manager: Optional[BrowserManager] = None
        self.navigation: Optional[NavigationTools] = None
        self.page_analyzer: Optional[PageAnalyzer] = None
        self.element_finder: Optional[ElementFinder] = None
        self.interactions: Optional[InteractionTools] = None
        self.state_evaluator: Optional[StateEvaluator] = None
        self.screenshots: Optional[ScreenshotTools] = None
        
        self.execution_log: List[Dict[str, Any]] = []
    
    def _initialize_tools(self):
        """Initialize all Playwright tools"""
        page = self.browser_manager.get_page()
        
        self.navigation = NavigationTools(page)
        self.page_analyzer = PageAnalyzer(page)
        self.element_finder = ElementFinder(page, self.api_key)
        self.element_finder.set_page_analyzer(self.page_analyzer)
        self.interactions = InteractionTools(page)
        self.state_evaluator = StateEvaluator(page, self.api_key)
        self.state_evaluator.set_page_analyzer(self.page_analyzer)
        self.screenshots = ScreenshotTools(page, self.screenshot_dir)
    
    def _get_function_tools(self) -> List[Dict[str, Any]]:
        """Get function definitions for GPT-4o"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "find_element_by_description",
                    "description": "Find a web element on the current page that matches a natural language description. Uses semantic matching.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Natural language description of the element (e.g., 'Create Project button', 'email input field')"
                            },
                            "element_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of element types to filter by (e.g., ['button', 'input'])"
                            }
                        },
                        "required": ["description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "click_element",
                    "description": "Click an element on the page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the element"},
                            "description": {"type": "string", "description": "Description of what is being clicked"}
                        },
                        "required": ["selector", "description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "type_text",
                    "description": "Type text into an input field",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the input element"},
                            "text": {"type": "string", "description": "Text to type"},
                            "description": {"type": "string", "description": "Description of the input field"}
                        },
                        "required": ["selector", "text", "description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "select_option",
                    "description": "Select an option from a dropdown",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the select element"},
                            "value": {"type": "string", "description": "Value or label to select"},
                            "description": {"type": "string", "description": "Description of the dropdown"}
                        },
                        "required": ["selector", "value", "description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "navigate",
                    "description": "Navigate to a URL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to navigate to"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "capture_screenshot",
                    "description": "Capture a screenshot of the current page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "integer", "description": "Step number for naming"},
                            "description": {"type": "string", "description": "Description of what is being captured"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "wait_for_condition",
                    "description": "Wait for a condition to be met",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "condition": {"type": "string", "description": "Description of condition to wait for"},
                            "timeout": {"type": "integer", "description": "Timeout in milliseconds", "default": 30000}
                        },
                        "required": ["condition"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_state_change",
                    "description": "Evaluate if an expected state change occurred",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expected_change": {"type": "string", "description": "Description of expected change"}
                        },
                        "required": ["expected_change"]
                    }
                }
            }
        ]
    
    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call from GPT-4o"""
        try:
            if function_name == "find_element_by_description":
                result = self.element_finder.find_element_by_description(
                    description=arguments.get("description"),
                    element_types=arguments.get("element_types")
                )
                return result
            
            elif function_name == "click_element":
                result = self.interactions.click_element(
                    selector=arguments.get("selector"),
                    description=arguments.get("description", "")
                )
                return result
            
            elif function_name == "type_text":
                result = self.interactions.type_text(
                    selector=arguments.get("selector"),
                    text=arguments.get("text"),
                    description=arguments.get("description", "")
                )
                return result
            
            elif function_name == "select_option":
                result = self.interactions.select_option(
                    selector=arguments.get("selector"),
                    value=arguments.get("value"),
                    description=arguments.get("description", "")
                )
                return result
            
            elif function_name == "navigate":
                result = self.navigation.navigate(url=arguments.get("url"))
                return result
            
            elif function_name == "capture_screenshot":
                result = self.screenshots.capture_screenshot(
                    step_number=arguments.get("step_number"),
                    description=arguments.get("description")
                )
                return result
            
            elif function_name == "wait_for_condition":
                result = self.state_evaluator.wait_for_condition(
                    condition=arguments.get("condition"),
                    timeout=arguments.get("timeout", 30000)
                )
                return result
            
            elif function_name == "evaluate_state_change":
                result = self.state_evaluator.evaluate_state_change(
                    expected_change=arguments.get("expected_change")
                )
                return result
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute(self, plan: TaskPlan) -> Dict[str, Any]:
        """
        Execute a TaskPlan from Agent B.
        
        Args:
            plan: TaskPlan object from Agent B
        
        Returns:
            dict: Execution result with screenshots and log
        """
        self.execution_log = []
        
        # Initialize browser
        self.browser_manager = BrowserManager(
            headless=self.headless,
            browser_type=self.browser_type,
            user_data_dir=self.user_data_dir,
            connect_to_existing=self.connect_to_existing,
            ws_endpoint=self.ws_endpoint
        )
        self.browser_manager.start()
        
        try:
            # Initialize all tools
            self._initialize_tools()
            
            # Execute each step in the plan
            for step_idx, action in enumerate(plan.steps, 1):
                step_result = self._execute_action(action, step_idx)
                self.execution_log.append({
                    "step": step_idx,
                    "action": action.action_type,
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
            if self.browser_manager:
                self.browser_manager.close()
    
    def _execute_action(self, action: Action, step_number: int) -> Dict[str, Any]:
        """Execute a single action from the plan"""
        # Create context for GPT-4o
        messages = [
            {
                "role": "system",
                "content": f"""You are executing a web automation task. You have access to tools to interact with a web page.

Current step: {action.action_type}
Target: {action.target_description}
Reasoning: {action.reasoning or 'N/A'}
Expected state change: {action.expected_state_change or 'N/A'}

Your task is to execute this action. Use the available tools to:
1. Find the element matching the description
2. Perform the required action
3. Verify the expected state change if specified
4. Capture screenshot if required

Be precise and use the tools available to you."""
            },
            {
                "role": "user",
                "content": f"Execute: {action.action_type} on '{action.target_description}'"
            }
        ]
        
        # Handle different action types
        if action.action_type == "navigate":
            # For navigation, extract URL from description using LLM if needed
            url = self._extract_url_from_description(action.target_description)
            if not url:
                return {
                    "success": False,
                    "error": f"Could not determine URL from description: {action.target_description}"
                }
            
            result = self.navigation.navigate(url)
            if result.get("success") and action.capture_after:
                self.screenshots.capture_screenshot(step_number=step_number, description=action.target_description)
            return result
        
        elif action.action_type == "click":
            # Use GPT-4o to find and click element
            return self._execute_with_llm(messages, action, step_number)
        
        elif action.action_type == "type":
            # Find element and type
            find_result = self.element_finder.find_element_by_description(action.target_description)
            if not find_result.get("success"):
                return find_result
            
            selector = find_result["selector"]
            result = self.interactions.type_text(
                selector=selector,
                text=action.value or "",
                description=action.target_description
            )
            
            if result.get("success") and action.capture_after:
                self.screenshots.capture_screenshot(step_number=step_number, description=f"Typed in {action.target_description}")
            
            return result
        
        elif action.action_type == "select_option":
            find_result = self.element_finder.find_element_by_description(action.target_description)
            if not find_result.get("success"):
                return find_result
            
            selector = find_result["selector"]
            result = self.interactions.select_option(
                selector=selector,
                value=action.value or "",
                description=action.target_description
            )
            
            if result.get("success") and action.capture_after:
                self.screenshots.capture_screenshot(step_number=step_number, description=f"Selected in {action.target_description}")
            
            return result
        
        elif action.action_type == "capture_screenshot":
            result = self.screenshots.capture_screenshot(step_number=step_number, description=action.target_description)
            return result
        
        elif action.action_type == "wait":
            if action.wait_conditions:
                for condition in action.wait_conditions:
                    self.state_evaluator.wait_for_condition(condition)
            return {"success": True, "message": "Wait completed"}
        
        elif action.action_type == "evaluate_state":
            if action.expected_state_change:
                result = self.state_evaluator.evaluate_state_change(action.expected_state_change)
                return result
            return {"success": True, "message": "State evaluated"}
        
        elif action.action_type == "scroll":
            result = self.interactions.scroll_page()
            return result
        
        elif action.action_type == "hover":
            find_result = self.element_finder.find_element_by_description(action.target_description)
            if not find_result.get("success"):
                return find_result
            
            selector = find_result["selector"]
            result = self.interactions.hover_element(selector=selector, description=action.target_description)
            return result
        
        else:
            return {
                "success": False,
                "error": f"Unknown action type: {action.action_type}"
            }
    
    def _execute_with_llm(self, messages: List[Dict], action: Action, step_number: int) -> Dict[str, Any]:
        """Execute action using GPT-4o with function calling"""
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self._get_function_tools(),
                tool_choice="auto",
                temperature=0.3
            )
            
            message = response.choices[0].message
            messages.append(message)
            
            # Check if model wants to call a function
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    # Execute function
                    function_result = self._execute_function(function_name, arguments)
                    
                    # Add result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result)
                    })
                
                iteration += 1
                continue
            
            # No more function calls, action complete
            if action.capture_after:
                self.screenshots.capture_screenshot(step_number=step_number, description=action.target_description)
            
            return {
                "success": True,
                "message": f"Completed {action.action_type} on {action.target_description}",
                "conversation": messages
            }
        
        return {
            "success": False,
            "error": "Max iterations reached without completing action"
        }
    
    def _extract_url_from_description(self, description: str) -> Optional[str]:
        """
        Extract or determine URL from a natural language description.
        Uses LLM to map descriptions like "Linear application homepage" to actual URLs.
        """
        # Check if description already contains a URL
        if "http://" in description or "https://" in description:
            # Extract URL from description
            import re
            urls = re.findall(r'https?://[^\s]+', description)
            if urls:
                return urls[0]
        
        # Use LLM to determine URL from description
        prompt = f"""Given a description of a website or application, determine the URL to navigate to.

Description: "{description}"

Return ONLY the URL (e.g., https://linear.app) or "unknown" if you cannot determine it.
Do not include any explanation, just the URL."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that maps website descriptions to URLs. Return only the URL, nothing else."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3
            )
            
            url = response.choices[0].message.content.strip()
            
            # Clean up response (remove quotes if present)
            url = url.strip('"').strip("'")
            
            # Validate it looks like a URL
            if url.startswith("http://") or url.startswith("https://"):
                return url
            elif url.lower() != "unknown" and "." in url:
                # Try adding https://
                return f"https://{url}"
            else:
                return None
        except Exception as e:
            return None
    
    def _get_screenshot_paths(self) -> List[str]:
        """Get list of screenshot file paths"""
        if not self.screenshots:
            return []
        
        screenshot_dir = Path(self.screenshots.output_dir)
        screenshots = sorted(screenshot_dir.glob("*.png"))
        return [str(s) for s in screenshots]

