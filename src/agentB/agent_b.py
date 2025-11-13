"""Agent B: Intelligent Task Planner with Reasoning Capabilities

This agent takes natural language task descriptions and generates structured,
executable plans for web automation tasks.
"""

import json
import os
import base64
from typing import Optional, List, Dict
from openai import OpenAI
from pydantic import ValidationError

from .models import TaskPlan, Action


class AgentB:
    """Agent B: Converts natural language tasks into structured execution plans"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ):
        """
        Initialize Agent B with OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (defaults to gpt-4o)
            temperature: Temperature for model (lower = more deterministic)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.temperature = temperature
        
        # Use gpt-4o by default
        self.model = model or self._get_best_available_model()
    
    def _get_best_available_model(self) -> str:
        """Return the default model (gpt-4o)"""
        return "gpt-4o"
    
    def _create_planning_prompt(self, task: str) -> str:
        """Create a detailed prompt for the reasoning model"""
        return f"""You are an intelligent web automation planner. Your task is to break down a high-level natural language instruction into a detailed, executable plan.

TASK: {task}

Your goal is to create a step-by-step plan that can be executed by a web automation agent (using Playwright). The agent can:
- Navigate to URLs
- Click buttons, links, and interactive elements
- Type text into input fields
- Select options from dropdowns
- Scroll pages
- Wait for elements or conditions
- Capture screenshots
- Evaluate page state

IMPORTANT CONSIDERATIONS:
1. **Generalizability**: The plan should work on any web application, not just specific ones. Use semantic descriptions (e.g., "Create Project button") rather than specific CSS selectors.
2. **State Detection**: Identify when UI state changes occur (modals opening, forms appearing, success messages) that don't change the URL. These are critical moments to capture screenshots.
3. **Screenshot Strategy**: Capture screenshots after significant state changes:
   - Before and after opening modals/dialogs
   - After filling forms
   - After submitting actions
   - When success/error messages appear
   - At key decision points
4. **Error Handling**: Consider what could go wrong and how to detect it (validation errors, network issues, missing elements).
5. **User Context**: Make reasonable assumptions about user state (logged in, permissions, etc.) and document them.

OUTPUT FORMAT:
Return a JSON object with this structure:
{{
    "goal": "The original task description",
    "steps": [
        {{
            "action_type": "navigate|click|type|wait|capture_screenshot|evaluate_state|scroll|select_option|hover",
            "target_description": "Natural language description of what to interact with",
            "value": "Optional value for type/select_option actions",
            "expected_state_change": "What should happen after this action",
            "capture_after": true/false,
            "reasoning": "Why this action is needed",
            "wait_conditions": ["condition1", "condition2"]
        }}
    ],
    "assumptions": ["assumption1", "assumption2"],
    "potential_issues": ["issue1", "issue2"],
    "success_criteria": ["criterion1", "criterion2"],
    "estimated_complexity": "simple|moderate|complex"
}}

Think step by step:
1. What is the end goal?
2. What are the logical steps to achieve it?
3. What UI elements will need to be interacted with?
4. When do state changes occur that warrant screenshots?
5. What could go wrong?

Now generate the plan:"""
    
    def plan(self, task: str) -> TaskPlan:
        """
        Generate a structured execution plan from a natural language task.
        
        Args:
            task: Natural language description of the task (e.g., "Create a new project in Linear")
            
        Returns:
            TaskPlan: Structured plan with ordered actions
            
        Raises:
            ValueError: If plan generation fails
        """
        prompt = self._create_planning_prompt(task)
        return self._generate_plan(prompt, self.model)
    
    def _generate_plan(self, prompt: str, model: str) -> TaskPlan:
        """Generate plan using the specified model"""
        try:
            # For reasoning models (o1), use standard completion
            # For GPT models, use chat completion with JSON mode
            if model.startswith("o1"):
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert web automation planner. Always respond with valid JSON only, no additional text."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=self.temperature,
                )
                content = response.choices[0].message.content
            else:
                # For GPT models, use JSON mode
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert web automation planner. Always respond with valid JSON only, no additional text."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=self.temperature,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
            
            # Parse JSON response
            if content:
                # Clean up response (remove markdown code blocks if present)
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                plan_data = json.loads(content)
                
                # Validate and create TaskPlan
                return TaskPlan(**plan_data)
            else:
                raise ValueError("Empty response from model")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except ValidationError as e:
            raise ValueError(f"Plan validation failed: {e}")
        except Exception as e:
            raise ValueError(f"Model API error: {e}")
    
    def refine_plan(self, plan: TaskPlan, feedback: str) -> TaskPlan:
        """
        Refine an existing plan based on feedback or new information.
        
        Args:
            plan: The original TaskPlan
            feedback: Feedback or additional context to incorporate
            
        Returns:
            TaskPlan: Refined plan
        """
        refinement_prompt = f"""You have an existing plan that needs refinement based on feedback.

ORIGINAL PLAN:
{plan.model_dump_json(indent=2)}

FEEDBACK/CONTEXT:
{feedback}

Please generate a refined plan following the same structure. Address the feedback while maintaining the overall goal."""
        
        try:
            return self._generate_plan(refinement_prompt, self.model)
        except Exception as e:
            raise ValueError(f"Failed to refine plan: {e}")
    
    def decide_next_action(
        self,
        task: str,
        screenshot_path: Optional[str] = None,
        execution_history: Optional[List[Dict]] = None,
        current_url: Optional[str] = None,
    ) -> Action:
        """
        Decide the next action based on current UI state (screenshot).
        This enables real-time adaptive planning.
        
        Args:
            task: The original task description
            screenshot_path: Path to current screenshot
            execution_history: List of previous actions and results
            current_url: Current page URL
            
        Returns:
            Action: Next action to execute
        """
        execution_history = execution_history or []
        
        # Build context from execution history
        history_text = ""
        if execution_history:
            history_text = "\n\nEXECUTION HISTORY:\n"
            for i, step in enumerate(execution_history, 1):
                action = step.get("action", {})
                result = step.get("result", {})
                if isinstance(action, dict):
                    action_type = action.get("action_type", "unknown")
                    target = action.get("target_description", "")
                else:
                    action_type = getattr(action, "action_type", "unknown")
                    target = getattr(action, "target_description", "")
                
                history_text += f"{i}. {action_type}: {target}\n"
                history_text += f"   Status: {result.get('status', 'unknown')}\n"
                if result.get('error_message'):
                    history_text += f"   Error: {result.get('error_message')}\n"
        
        # Create prompt for vision-based decision making
        prompt = f"""You are an intelligent web automation agent that analyzes UI states and decides the next action.

ORIGINAL TASK: {task}

CURRENT STATE:
- URL: {current_url or "Unknown"}
- Screenshot available: {"Yes" if screenshot_path else "No"}
{history_text}

Your job is to analyze the current UI state and decide the SINGLE next action to take.

AVAILABLE ACTIONS:
- navigate: Navigate to a URL
- click: Click a button, link, or interactive element
- type: Type text into an input field
- select_option: Select an option from a dropdown
- scroll: Scroll the page (up/down)
- wait: Wait for an element or condition
- capture_screenshot: Take a screenshot of current state
- hover: Hover over an element
- evaluate_state: Evaluate if task is complete

IMPORTANT:
1. Look at the screenshot (if provided) to understand the current UI state
2. Consider what has been done so far (execution history)
3. Decide the ONE next action that moves toward completing the task
4. If a modal/form appears, interact with it
5. If the task appears complete, use evaluate_state
6. Always capture screenshots after significant state changes (modals, forms, success messages)

OUTPUT FORMAT (JSON only):
{{
    "action_type": "navigate|click|type|wait|capture_screenshot|evaluate_state|scroll|select_option|hover",
    "target_description": "Natural language description of what to interact with",
    "value": "Optional value for type/select_option actions",
    "expected_state_change": "What should happen after this action",
    "capture_after": true/false,
    "reasoning": "Why this action is needed based on current UI state",
    "wait_conditions": ["condition1", "condition2"]
}}

Think step by step:
1. What does the current screenshot show?
2. What has been done so far?
3. What is the next logical step to complete the task?
4. What UI element needs to be interacted with?

Now decide the next action:"""

        messages = [
            {
                "role": "system",
                "content": "You are an expert web automation agent. Analyze UI screenshots and decide the next action. Always respond with valid JSON only, no additional text."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Add screenshot if available (for vision models)
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                with open(screenshot_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "This is the current UI state. Analyze it and decide the next action."
                        }
                    ]
                })
            except Exception as e:
                # If screenshot can't be read, continue without it
                pass
        
        try:
            # Use vision-capable model (gpt-4o supports vision)
            vision_model = "gpt-4o" if screenshot_path else self.model
            
            response = self.client.chat.completions.create(
                model=vision_model,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            if content:
                # Clean up response
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                action_data = json.loads(content)
                return Action(**action_data)
            else:
                raise ValueError("Empty response from model")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except ValidationError as e:
            raise ValueError(f"Action validation failed: {e}")
        except Exception as e:
            raise ValueError(f"Model API error: {e}")
    
    def is_task_complete(
        self,
        task: str,
        screenshot_path: Optional[str] = None,
        execution_history: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Determine if the task has been completed based on current state.
        
        Args:
            task: Original task description
            screenshot_path: Path to current screenshot
            execution_history: List of previous actions
            
        Returns:
            bool: True if task appears complete
        """
        # Use decide_next_action to check completion
        try:
            next_action = self.decide_next_action(
                task=task,
                screenshot_path=screenshot_path,
                execution_history=execution_history,
            )
            return next_action.action_type == "evaluate_state"
        except Exception:
            return False

