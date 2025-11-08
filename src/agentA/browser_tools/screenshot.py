"""Screenshot capture tools"""

from typing import Optional, Dict, Any
from pathlib import Path
from playwright.sync_api import Page
from datetime import datetime


class ScreenshotTools:
    """Tools for capturing screenshots"""
    
    def __init__(self, page: Page, output_dir: str = "screenshots"):
        """
        Initialize screenshot tools.
        
        Args:
            page: Playwright Page object
            output_dir: Directory to save screenshots
        """
        self.page = page
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_count = 0
    
    def capture_screenshot(
        self, 
        filename: Optional[str] = None,
        step_number: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture screenshot of current page state.
        
        Args:
            filename: Optional custom filename
            step_number: Optional step number for naming
            description: Optional description for filename
        
        Returns:
            dict: Screenshot result with file path
        """
        try:
            # Generate filename if not provided
            if not filename:
                self.screenshot_count += 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if step_number is not None:
                    filename = f"step_{step_number:03d}_{timestamp}.png"
                elif description:
                    safe_desc = "".join(c for c in description[:30] if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
                    filename = f"{safe_desc}_{timestamp}.png"
                else:
                    filename = f"screenshot_{self.screenshot_count:03d}_{timestamp}.png"
            
            # Ensure filename ends with .png
            if not filename.endswith('.png'):
                filename += '.png'
            
            filepath = self.output_dir / filename
            
            # Capture screenshot
            self.page.screenshot(path=str(filepath), full_page=True)
            
            return {
                "success": True,
                "filepath": str(filepath),
                "filename": filename,
                "message": f"Screenshot saved: {filename}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "filepath": None
            }
    
    def capture_element_screenshot(
        self, 
        selector: str,
        filename: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture screenshot of a specific element.
        
        Args:
            selector: CSS selector for element
            filename: Optional custom filename
            description: Optional description for filename
        
        Returns:
            dict: Screenshot result with file path
        """
        try:
            element = self.page.wait_for_selector(selector, timeout=10000)
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if description:
                    safe_desc = "".join(c for c in description[:30] if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
                    filename = f"element_{safe_desc}_{timestamp}.png"
                else:
                    filename = f"element_{timestamp}.png"
            
            if not filename.endswith('.png'):
                filename += '.png'
            
            filepath = self.output_dir / filename
            element.screenshot(path=str(filepath))
            
            return {
                "success": True,
                "filepath": str(filepath),
                "filename": filename,
                "selector": selector,
                "message": f"Element screenshot saved: {filename}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "filepath": None,
                "selector": selector
            }
    
    def set_output_directory(self, output_dir: str):
        """Change the output directory for screenshots"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_screenshot_count(self) -> int:
        """Get the current screenshot count"""
        return self.screenshot_count

