"""Browser initialization and management"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional
import os


class BrowserManager:
    """Manages Playwright browser instance and pages"""
    
    def __init__(
        self, 
        headless: bool = False, 
        browser_type: str = "chromium",
        user_data_dir: Optional[str] = None,
        connect_to_existing: bool = False,
        ws_endpoint: Optional[str] = None
    ):
        """
        Initialize browser manager.
        
        Args:
            headless: Run browser in headless mode (ignored if connect_to_existing=True)
            browser_type: "chromium", "firefox", or "webkit"
            user_data_dir: Optional directory to save browser data (cookies, localStorage, etc.)
                          If provided, uses persistent context to maintain login sessions
            connect_to_existing: If True, connect to an existing browser via CDP
            ws_endpoint: WebSocket endpoint for CDP connection (defaults to http://localhost:9222)
        """
        self.headless = headless
        self.browser_type = browser_type
        self.user_data_dir = user_data_dir
        self.connect_to_existing = connect_to_existing
        self.ws_endpoint = ws_endpoint or "http://localhost:9222"
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_persistent = user_data_dir is not None
        self.is_connected = False
    
    def start(self):
        """Start Playwright and launch browser (with optional persistent context or CDP connection)"""
        self.playwright = sync_playwright().start()
        
        # If connecting to existing browser, use CDP
        if self.connect_to_existing:
            self._connect_via_cdp()
            return
        
        if self.browser_type == "chromium":
            if self.user_data_dir:
                # Use persistent context (saves cookies, localStorage, sessionStorage, etc.)
                # This allows maintaining login sessions across runs
                self.context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                # In persistent context mode, the returned object IS the context
                # Get existing pages or create new one
                if self.context.pages:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
                # For persistent context, browser is accessed via context
                self.browser = None  # Not directly accessible in persistent mode
            else:
                # Normal launch (non-persistent)
                self.browser = self.playwright.chromium.launch(headless=self.headless)
                self.context = self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                self.page = self.context.new_page()
        elif self.browser_type == "firefox":
            # Firefox doesn't support persistent context the same way
            # Use regular launch with user_data_dir if provided
            if self.user_data_dir:
                # Firefox uses profile directory
                self.browser = self.playwright.firefox.launch(
                    headless=self.headless,
                    firefox_user_prefs={"profile": self.user_data_dir}
                )
            else:
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            self.page = self.context.new_page()
        elif self.browser_type == "webkit":
            # WebKit doesn't support persistent context
            self.browser = self.playwright.webkit.launch(headless=self.headless)
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            self.page = self.context.new_page()
        else:
            raise ValueError(f"Unknown browser type: {self.browser_type}")
        
        # Set default timeout
        self.page.set_default_timeout(30000)
    
    def _connect_via_cdp(self):
        """Connect to an existing browser via Chrome DevTools Protocol (CDP)"""
        if self.browser_type != "chromium":
            raise ValueError("CDP connection only supported for Chromium browsers")
        
        try:
            # Connect to existing browser via CDP
            self.browser = self.playwright.chromium.connect_over_cdp(self.ws_endpoint)
            self.is_connected = True
            
            # Get existing contexts (your open browser tabs/windows)
            contexts = self.browser.contexts
            
            if contexts:
                # Use the first existing context (your main browser window)
                self.context = contexts[0]
                # Get existing pages or create new one
                if self.context.pages:
                    self.page = self.context.pages[0]
                    print(f"✅ Connected to existing browser with {len(self.context.pages)} open page(s)")
                else:
                    self.page = self.context.new_page()
                    print("✅ Connected to existing browser, created new page")
            else:
                # No existing context, create new one
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                print("✅ Connected to existing browser, created new context")
            
            self.page.set_default_timeout(30000)
            
        except Exception as e:
            error_msg = (
                f"\n❌ Failed to connect to existing browser at {self.ws_endpoint}\n\n"
                f"To fix this, you need to start Chrome with remote debugging enabled:\n\n"
                f"Option 1: Use the helper script:\n"
                f"  ./start_chrome_with_debugging.sh\n\n"
                f"Option 2: Manual command (close existing Chrome first):\n"
                f"  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222\n\n"
                f"Option 3: If Chrome is already running, close it and restart with the flag above.\n\n"
                f"Then run Agent A again.\n\n"
                f"Original error: {str(e)}"
            )
            raise RuntimeError(error_msg)
    
    def get_page(self) -> Page:
        """Get the current page"""
        if self.page is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.page
    
    def new_page(self) -> Page:
        """Create a new page"""
        if self.context is None:
            raise RuntimeError("Browser context not initialized. Call start() first.")
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
        return self.page
    
    def close(self):
        """Close browser and cleanup"""
        # If connected to existing browser, don't close it - just disconnect
        if self.is_connected:
            # Only close pages we created, not the browser itself
            if self.page and self.page not in (self.context.pages if self.context else []):
                try:
                    self.page.close()
                except Exception:
                    pass
            # Disconnect from browser (but don't close the actual browser)
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            return
        
        # For persistent context, only close pages, not the context
        # This preserves the session data
        if self.is_persistent and self.context:
            # Close all pages but keep context alive to save state
            for page in self.context.pages:
                try:
                    page.close()
                except Exception:
                    pass
            # Close the persistent context (saves state)
            try:
                self.context.close()
            except Exception:
                pass
        else:
            # Normal cleanup for non-persistent mode
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
        
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
        
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

