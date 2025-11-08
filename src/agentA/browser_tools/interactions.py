"""Interaction tools for web automation"""

from typing import Optional, Dict, Any
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


class InteractionTools:
    """Tools for interacting with web elements"""
    
    def __init__(self, page: Page):
        """
        Initialize interaction tools.
        
        Args:
            page: Playwright Page object
        """
        self.page = page
    
    def click_element(self, selector: str, description: str = "") -> Dict[str, Any]:
        """
        Click an element on the page.
        
        Args:
            selector: CSS selector or text selector
            description: Description of element (for logging)
        
        Returns:
            dict: Click result
        """
        try:
            # Scroll element into view first
            self.page.evaluate(f"""
                (selector) => {{
                    const el = document.querySelector(selector);
                    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            """, selector)
            
            # Wait for element to be visible and clickable
            element = self.page.wait_for_selector(selector, state="visible", timeout=10000)
            element.click()
            
            return {
                "success": True,
                "selector": selector,
                "description": description,
                "message": f"Clicked element: {description or selector}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Element not found or not clickable: {selector}",
                "selector": selector
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }
    
    def type_text(
        self, 
        selector: str, 
        text: str, 
        description: str = "",
        clear_first: bool = False
    ) -> Dict[str, Any]:
        """
        Type text into an input field.
        
        Args:
            selector: CSS selector for input element
            text: Text to type
            description: Description of element (for logging)
            clear_first: Whether to clear field before typing
        
        Returns:
            dict: Type result
        """
        try:
            element = self.page.wait_for_selector(selector, state="visible", timeout=10000)
            
            if clear_first:
                element.fill("")
            
            element.type(text, delay=50)  # Small delay for realism
            
            return {
                "success": True,
                "selector": selector,
                "text": text,
                "description": description,
                "message": f"Typed text into {description or selector}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Input element not found: {selector}",
                "selector": selector
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }
    
    def fill_field(
        self, 
        selector: str, 
        text: str, 
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Fill an input field (clears and types).
        
        Args:
            selector: CSS selector for input element
            text: Text to fill
            description: Description of element (for logging)
        
        Returns:
            dict: Fill result
        """
        try:
            element = self.page.wait_for_selector(selector, state="visible", timeout=10000)
            element.fill(text)
            
            return {
                "success": True,
                "selector": selector,
                "text": text,
                "description": description,
                "message": f"Filled field {description or selector}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Input element not found: {selector}",
                "selector": selector
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }
    
    def select_option(
        self, 
        selector: str, 
        value: str, 
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Select an option from a dropdown.
        
        Args:
            selector: CSS selector for select element
            value: Value or label to select
            description: Description of element (for logging)
        
        Returns:
            dict: Select result
        """
        try:
            element = self.page.wait_for_selector(selector, state="visible", timeout=10000)
            
            # Try selecting by value first, then by label
            try:
                element.select_option(value)
            except:
                element.select_option(label=value)
            
            return {
                "success": True,
                "selector": selector,
                "value": value,
                "description": description,
                "message": f"Selected option in {description or selector}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Select element not found: {selector}",
                "selector": selector
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }
    
    def hover_element(self, selector: str, description: str = "") -> Dict[str, Any]:
        """
        Hover over an element.
        
        Args:
            selector: CSS selector for element
            description: Description of element (for logging)
        
        Returns:
            dict: Hover result
        """
        try:
            element = self.page.wait_for_selector(selector, state="visible", timeout=10000)
            element.hover()
            
            return {
                "success": True,
                "selector": selector,
                "description": description,
                "message": f"Hovered over {description or selector}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Element not found: {selector}",
                "selector": selector
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }
    
    def scroll_to_element(self, selector: str, description: str = "") -> Dict[str, Any]:
        """
        Scroll element into view.
        
        Args:
            selector: CSS selector for element
            description: Description of element (for logging)
        
        Returns:
            dict: Scroll result
        """
        try:
            element = self.page.wait_for_selector(selector, timeout=10000)
            element.scroll_into_view_if_needed()
            
            return {
                "success": True,
                "selector": selector,
                "description": description,
                "message": f"Scrolled to {description or selector}"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Element not found: {selector}",
                "selector": selector
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }
    
    def scroll_page(self, direction: str = "down", pixels: int = 500) -> Dict[str, Any]:
        """
        Scroll the page.
        
        Args:
            direction: "up" or "down"
            pixels: Number of pixels to scroll
        
        Returns:
            dict: Scroll result
        """
        try:
            if direction == "down":
                self.page.evaluate(f"window.scrollBy(0, {pixels})")
            else:
                self.page.evaluate(f"window.scrollBy(0, -{pixels})")
            
            return {
                "success": True,
                "direction": direction,
                "pixels": pixels,
                "message": f"Scrolled {direction} {pixels} pixels"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

