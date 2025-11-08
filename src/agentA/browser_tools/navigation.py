"""Navigation tools for web automation"""

from typing import Optional
from playwright.sync_api import Page


class NavigationTools:
    """Tools for page navigation"""
    
    def __init__(self, page: Page):
        """
        Initialize navigation tools.
        
        Args:
            page: Playwright Page object
        """
        self.page = page
    
    def navigate(self, url: str, wait_until: str = "load") -> dict:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: When to consider navigation successful
                       Options: "load", "domcontentloaded", "networkidle", "commit"
        
        Returns:
            dict: Navigation result with status and current URL
        """
        try:
            self.page.goto(url, wait_until=wait_until)
            return {
                "success": True,
                "url": self.page.url,
                "title": self.page.title(),
                "message": f"Navigated to {url}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": self.page.url if self.page else None
            }
    
    def get_current_url(self) -> str:
        """Get the current page URL"""
        return self.page.url
    
    def get_page_title(self) -> str:
        """Get the current page title"""
        return self.page.title()
    
    def go_back(self) -> dict:
        """
        Navigate back in browser history.
        
        Returns:
            dict: Navigation result
        """
        try:
            self.page.go_back()
            return {
                "success": True,
                "url": self.page.url,
                "message": "Navigated back"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def go_forward(self) -> dict:
        """
        Navigate forward in browser history.
        
        Returns:
            dict: Navigation result
        """
        try:
            self.page.go_forward()
            return {
                "success": True,
                "url": self.page.url,
                "message": "Navigated forward"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def reload(self, wait_until: str = "load") -> dict:
        """
        Reload the current page.
        
        Args:
            wait_until: When to consider reload successful
        
        Returns:
            dict: Reload result
        """
        try:
            self.page.reload(wait_until=wait_until)
            return {
                "success": True,
                "url": self.page.url,
                "message": "Page reloaded"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

