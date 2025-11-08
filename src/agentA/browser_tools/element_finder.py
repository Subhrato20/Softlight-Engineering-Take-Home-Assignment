"""Semantic element finding using LLM"""

from typing import Optional, Dict, Any, List
from playwright.sync_api import Page
from openai import OpenAI
import json
import os


class ElementFinder:
    """Finds elements on page using semantic matching with LLM"""
    
    def __init__(self, page: Page, api_key: Optional[str] = None):
        """
        Initialize element finder.
        
        Args:
            page: Playwright Page object
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.page = page
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required for semantic element finding")
        
        self.client = OpenAI(api_key=self.api_key)
        self.page_analyzer = None  # Will be set by Agent A
    
    def set_page_analyzer(self, page_analyzer):
        """Set the page analyzer instance"""
        self.page_analyzer = page_analyzer
    
    def find_element_by_description(
        self, 
        description: str,
        element_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Find an element on the page matching a natural language description.
        Uses LLM to semantically match the description to actual page elements.
        
        Args:
            description: Natural language description (e.g., "Create Project button")
            element_types: Optional list of element types to filter by
                          (e.g., ["button", "link", "input"])
        
        Returns:
            Dictionary with selector, element_info, and confidence
        """
        if not self.page_analyzer:
            raise RuntimeError("Page analyzer not set. Call set_page_analyzer() first.")
        
        # Get page content
        page_state = self.page_analyzer.analyze_page_state()
        interactive_elements = page_state.get("interactive_elements", [])
        
        # Filter by element types if specified
        if element_types:
            interactive_elements = [
                el for el in interactive_elements 
                if el.get("type") in element_types
            ]
        
        if not interactive_elements:
            return {
                "success": False,
                "error": "No interactive elements found on page",
                "selector": None
            }
        
        # Use LLM to find best matching element
        prompt = f"""You are analyzing a web page to find an element that matches a description.

TARGET DESCRIPTION: "{description}"

AVAILABLE ELEMENTS ON THE PAGE:
{json.dumps(interactive_elements, indent=2)}

Your task is to find the element that best matches the description "{description}".

Return a JSON object with:
{{
    "index": <index of the best matching element in the list above>,
    "confidence": <0.0 to 1.0, how confident you are this is the right element>,
    "reasoning": "<brief explanation of why this element matches>"
}}

If no element matches well (confidence < 0.5), return:
{{
    "index": null,
    "confidence": 0.0,
    "reasoning": "<explanation of why no element matches>"
}}

Return ONLY valid JSON, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at matching natural language descriptions to web page elements. Always respond with valid JSON only."
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
            
            if result.get("index") is None or result.get("confidence", 0) < 0.5:
                return {
                    "success": False,
                    "error": result.get("reasoning", "No matching element found"),
                    "confidence": result.get("confidence", 0.0),
                    "selector": None
                }
            
            element_index = result["index"]
            if element_index >= len(interactive_elements):
                return {
                    "success": False,
                    "error": "Invalid element index returned",
                    "selector": None
                }
            
            matched_element = interactive_elements[element_index]
            selector = matched_element.get("selector", "")
            
            # Verify selector works
            try:
                element = self.page.query_selector(selector)
                if element:
                    is_visible = self.page.evaluate("""
                        (selector) => {
                            const el = document.querySelector(selector);
                            return el && el.offsetParent !== null;
                        }
                    """, selector)
                    
                    return {
                        "success": True,
                        "selector": selector,
                        "element_info": matched_element,
                        "confidence": result.get("confidence", 0.8),
                        "reasoning": result.get("reasoning", ""),
                        "visible": is_visible
                    }
                else:
                    return {
                        "success": False,
                        "error": "Selector found but element not found on page",
                        "selector": selector
                    }
            except Exception as e:
                # Try alternative selector strategies
                return self._try_alternative_selectors(matched_element, description)
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error finding element: {str(e)}",
                "selector": None
            }
    
    def _try_alternative_selectors(
        self, 
        element_info: Dict[str, Any], 
        description: str
    ) -> Dict[str, Any]:
        """Try alternative selector strategies"""
        alternatives = []
        
        # Try by ID
        if element_info.get("id"):
            alternatives.append(f"#{element_info['id']}")
        
        # Try by name (for inputs)
        if element_info.get("name"):
            alternatives.append(f"[name='{element_info['name']}']")
        
        # Try by text content (for buttons/links)
        if element_info.get("text"):
            text = element_info["text"].strip()
            if text:
                # Try exact text match
                alternatives.append(f"text='{text}'")
        
        # Try by aria-label
        if element_info.get("aria_label"):
            alternatives.append(f"[aria-label='{element_info['aria_label']}']")
        
        # Try each alternative
        for selector in alternatives:
            try:
                element = self.page.query_selector(selector)
                if element:
                    return {
                        "success": True,
                        "selector": selector,
                        "element_info": element_info,
                        "confidence": 0.7,
                        "reasoning": "Found using alternative selector",
                        "visible": True
                    }
            except Exception:
                continue
        
        return {
            "success": False,
            "error": "Could not find element with any selector strategy",
            "selector": None
        }

