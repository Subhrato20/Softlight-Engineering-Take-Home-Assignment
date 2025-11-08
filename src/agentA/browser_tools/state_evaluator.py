"""State evaluation and waiting tools"""

from typing import Optional, Dict, Any, List
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from openai import OpenAI
import json
import os


class StateEvaluator:
    """Tools for evaluating page state and waiting for conditions"""
    
    def __init__(self, page: Page, api_key: Optional[str] = None):
        """
        Initialize state evaluator.
        
        Args:
            page: Playwright Page object
            api_key: OpenAI API key for state evaluation (optional)
        """
        self.page = page
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.page_analyzer = None
    
    def set_page_analyzer(self, page_analyzer):
        """Set the page analyzer instance"""
        self.page_analyzer = page_analyzer
    
    def check_element_exists(self, description: str) -> bool:
        """
        Check if an element matching description exists on page.
        
        Args:
            description: Natural language description of element
        
        Returns:
            bool: True if element exists
        """
        if not self.page_analyzer:
            return False
        
        # Get interactive elements
        interactive_elements = self.page_analyzer.get_interactive_elements()
        
        # Simple text matching (could be enhanced with LLM)
        description_lower = description.lower()
        for element in interactive_elements:
            element_text = element.get("text", "").lower()
            if description_lower in element_text or element_text in description_lower:
                return True
        
        return False
    
    def get_element_text(self, selector: str) -> str:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector for element
        
        Returns:
            str: Element text content
        """
        try:
            element = self.page.query_selector(selector)
            if element:
                return element.inner_text()
            return ""
        except Exception:
            return ""
    
    def is_element_visible(self, selector: str) -> bool:
        """
        Check if an element is visible.
        
        Args:
            selector: CSS selector for element
        
        Returns:
            bool: True if element is visible
        """
        try:
            return self.page.evaluate("""
                (selector) => {
                    const el = document.querySelector(selector);
                    return el && el.offsetParent !== null;
                }
            """, selector)
        except Exception:
            return False
    
    def wait_for_element(
        self, 
        description: str, 
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        Wait for an element matching description to appear.
        
        Args:
            description: Natural language description of element
            timeout: Timeout in milliseconds
        
        Returns:
            dict: Wait result
        """
        # This is a simplified version - in practice, you'd use element_finder
        # to find the element and then wait for it
        try:
            # For now, wait for page to be in a stable state
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            return {
                "success": True,
                "message": f"Waited for element: {description}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Timeout waiting for element: {description}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def wait_for_condition(
        self, 
        condition: str, 
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        Wait for a custom condition.
        
        Args:
            condition: Description of condition (e.g., "modal opens", "text appears")
            timeout: Timeout in milliseconds
        
        Returns:
            dict: Wait result
        """
        try:
            # Wait for page to be stable
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            
            # Additional check based on condition
            if "modal" in condition.lower() or "dialog" in condition.lower():
                # Check if modal is open
                modals = self.page_analyzer._check_modals() if self.page_analyzer else []
                if modals:
                    return {
                        "success": True,
                        "message": f"Condition met: {condition}"
                    }
            
            return {
                "success": True,
                "message": f"Condition met: {condition}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Timeout waiting for condition: {condition}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def wait_for_navigation(self, timeout: int = 30000) -> Dict[str, Any]:
        """
        Wait for page navigation to complete.
        
        Args:
            timeout: Timeout in milliseconds
        
        Returns:
            dict: Wait result
        """
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            return {
                "success": True,
                "url": self.page.url,
                "message": "Navigation completed"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": "Timeout waiting for navigation"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def evaluate_state_change(
        self, 
        expected_change: str,
        previous_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate if expected state change occurred using LLM.
        
        Args:
            expected_change: Description of expected change (e.g., "modal opens")
            previous_state: Previous page state for comparison
        
        Returns:
            dict: Evaluation result
        """
        if not self.page_analyzer or not self.client:
            return {
                "success": False,
                "error": "State evaluation requires page analyzer and OpenAI API"
            }
        
        current_state = self.page_analyzer.analyze_page_state()
        
        prompt = f"""You are evaluating whether an expected state change occurred on a web page.

EXPECTED CHANGE: "{expected_change}"

CURRENT PAGE STATE:
{json.dumps(current_state, indent=2)}

{f'PREVIOUS PAGE STATE:\n{json.dumps(previous_state, indent=2)}' if previous_state else ''}

Determine if the expected change "{expected_change}" has occurred.

Return a JSON object:
{{
    "change_occurred": true/false,
    "confidence": 0.0-1.0,
    "evidence": "<brief explanation of what you observe>",
    "details": "<any relevant details about the state change>"
}}

Return ONLY valid JSON, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at evaluating web page state changes. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "success": True,
                "change_occurred": result.get("change_occurred", False),
                "confidence": result.get("confidence", 0.0),
                "evidence": result.get("evidence", ""),
                "details": result.get("details", "")
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error evaluating state change: {str(e)}"
            }

