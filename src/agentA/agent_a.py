"""Agent A: Web Automation Executor using browser-use

Simplified implementation leveraging browser-use's built-in feedback loop
and intelligent element finding. Much simpler than manual Playwright!
"""

import os
import re
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request
from typing import List, Dict, Optional, Any
from datetime import datetime

from browser_use import Agent, Browser
try:
    # Try to import ChatBrowserUse first
    from browser_use import ChatBrowserUse  # type: ignore
    CHAT_BROWSER_USE_AVAILABLE = True
except Exception:
    CHAT_BROWSER_USE_AVAILABLE = False
    try:
        # Fallback to ChatOpenAI
        from browser_use import ChatOpenAI  # type: ignore
    except Exception:
        from browser_use.llm.openai.chat import ChatOpenAI

from src.agentB.models import TaskPlan, Action


class AgentA:
    """Agent A: Executes TaskPlans using browser-use library"""
    
    def __init__(
        self,
        driver_path: Optional[str] = None,
        headless: bool = True,
        screenshot_dir: str = "screenshots",
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        use_real_browser: bool = True,
        browser_type: str = "chrome",
        executable_path: Optional[str] = None,
        user_data_dir: Optional[str] = None,
        profile_directory: str = "Default",
        cdp_url: Optional[str] = None,
        strict_real_browser: bool = False,
        force_kill_chrome: bool = True,
    ):
        """
        Initialize Agent A with browser-use.
        
        Args:
            driver_path: Not used (kept for compatibility)
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save screenshots
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use. If ChatBrowserUse is available, accepts 'bu-latest' or 'bu-1-0' 
                   (GPT model names like 'gpt-4o' will be converted to 'bu-latest').
                   If ChatOpenAI is used, accepts GPT model names like 'gpt-4o', 'gpt-4', etc.
            use_real_browser: Whether to connect to existing Chrome profile via CDP
            browser_type: Browser to control via CDP. Supported: "chrome" (default), "brave".
            executable_path: Path to Chrome executable (auto-detected by platform if not set)
            user_data_dir: Browser user data dir (profile root). Auto by platform if not set
            profile_directory: Browser profile directory name (e.g., "Default", "Profile 1")
        """
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(exist_ok=True, parents=True)
        
        # ChatBrowserUse uses BROWSER_USE_API_KEY, ChatOpenAI uses OPENAI_API_KEY
        if CHAT_BROWSER_USE_AVAILABLE:
            # ChatBrowserUse needs BROWSER_USE_API_KEY
            self.api_key = api_key or os.getenv("BROWSER_USE_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "BROWSER_USE_API_KEY required for ChatBrowserUse. "
                    "Set BROWSER_USE_API_KEY environment variable or pass api_key parameter. "
                    "Get your API key at https://cloud.browser-use.com/new-api-key"
                )
            # ChatBrowserUse models: 'bu-latest' or 'bu-1-0'
            if model.startswith("gpt-"):
                # Default to bu-latest for GPT models when using ChatBrowserUse
                self.model = "bu-latest"
            elif model in ["bu-latest", "bu-1-0"]:
                self.model = model
            else:
                raise ValueError(f"Invalid model for ChatBrowserUse: '{model}'. Must be 'bu-latest' or 'bu-1-0', or a GPT model name (will be converted to 'bu-latest')")
        else:
            # ChatOpenAI needs OPENAI_API_KEY
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key required for browser-use. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
            # For ChatOpenAI, only GPT models are allowed
            if not model.startswith("gpt-"):
                raise ValueError(f"Only GPT models are supported with ChatOpenAI. Got: {model}. Use 'gpt-4o', 'gpt-4', etc.")
            self.model = model
        
        self.agent: Optional[Agent] = None

        # Real browser configuration
        self.use_real_browser = use_real_browser
        self.browser: Optional[Browser] = None
        self.cdp_url = cdp_url
        self.strict_real_browser = strict_real_browser
        self.force_kill_browser = force_kill_chrome
        self.browser_type = browser_type.lower()
        supported_browsers = {"chrome", "brave"}
        if self.browser_type not in supported_browsers:
            raise ValueError(
                f"Browser '{browser_type}' not supported. Choose one of {sorted(supported_browsers)} "
                "or set use_real_browser=False to use the managed browser."
            )
        if use_real_browser:
            import platform
            system = platform.system()

            executable_path, user_data_dir, process_names = self._resolve_browser_defaults(
                browser_type=self.browser_type,
                system=system,
                executable_path_override=executable_path,
                user_data_dir_override=user_data_dir,
            )
            self.browser_process_names = process_names

            # Preflight: optional forced browser kill + lock cleanup
            self.executable_path = executable_path
            self.user_data_dir = user_data_dir
            self.profile_directory = profile_directory
            if self.force_kill_browser:
                self._force_kill_browser()

            browser_label = "Brave" if self.browser_type == "brave" else "Chrome"

            # If a CDP URL is provided, prefer attaching to an existing browser instance
            if self.cdp_url and self._is_cdp_reachable(self.cdp_url):
                self.browser = Browser(
                    cdp_url=self.cdp_url,
                    user_data_dir=self.user_data_dir,
                    profile_directory=self.profile_directory,
                )
            else:
                # If CDP URL provided but not reachable, fall back to launching a local instance
                if self.cdp_url and not self._is_cdp_reachable(self.cdp_url):
                    print(f"⚠️  CDP URL not reachable. Launching local {browser_label} with your profile instead.")

                # macOS: fail fast if browser executable not found
                if system == "Darwin" and not os.path.exists(self.executable_path):
                    raise FileNotFoundError(
                        f"{browser_label} executable not found at {self.executable_path}. "
                        f"Install {browser_label} or pass executable_path to AgentA."
                    )

                self.browser = Browser(
                    executable_path=self.executable_path,
                    user_data_dir=self.user_data_dir,
                    profile_directory=self.profile_directory,
                )

            # Preflight lock check (best-effort): if browser is running, profile has lock markers
            self._profile_lock_detected = False
            try:
                root = self.user_data_dir
                lock_markers = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
                if any(os.path.exists(os.path.join(root, m)) for m in lock_markers):
                    self._profile_lock_detected = True
            except Exception:
                # Non-fatal: continue without lock detection
                pass

        # Track execution state
        self.current_task_name: Optional[str] = None
        self.step_counter = 0

    def _resolve_browser_defaults(
        self,
        browser_type: str,
        system: str,
        executable_path_override: Optional[str],
        user_data_dir_override: Optional[str],
    ) -> tuple[str, str, list[str]]:
        """Resolve default executable path, user data dir, and process names for supported browsers."""
        browser_type = browser_type.lower()
        exec_path = executable_path_override
        user_dir = user_data_dir_override
        process_names: list[str]

        if browser_type == "brave":
            if system == "Darwin":
                exec_path = exec_path or "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
                user_dir = user_dir or os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser")
            elif system == "Windows":
                exec_path = exec_path or r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
                user_dir = user_dir or os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")
            else:
                # Linux
                user_dir = user_dir or os.path.expanduser("~/.config/BraveSoftware/Brave-Browser")
                if not exec_path:
                    brave_candidates = ["/usr/bin/brave-browser", "/usr/bin/brave"]
                    exec_path = next((p for p in brave_candidates if os.path.exists(p)), brave_candidates[0])
            process_names = ["Brave Browser", "Brave Browser Helper", "brave", "chrome_crashpad_handler"]
        else:
            # Default to Chrome
            if system == "Darwin":
                exec_path = exec_path or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                user_dir = user_dir or os.path.expanduser("~/Library/Application Support/Google/Chrome")
            elif system == "Windows":
                exec_path = exec_path or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                user_dir = user_dir or os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
            else:
                user_dir = user_dir or os.path.expanduser("~/.config/google-chrome")
                if not exec_path:
                    chrome_candidates = [
                        "/usr/bin/google-chrome",
                        "/usr/bin/google-chrome-stable",
                        "/usr/bin/chromium-browser",
                        "/usr/bin/chromium",
                    ]
                    exec_path = next((p for p in chrome_candidates if os.path.exists(p)), chrome_candidates[0])
            process_names = ["Google Chrome", "Google Chrome Helper", "chrome", "chrome_crashpad_handler"]

        if exec_path is None or user_dir is None:
            raise ValueError(f"Could not determine defaults for browser '{browser_type}'.")

        return exec_path, user_dir, process_names

    def _force_kill_browser(self):
        """Force-kill browser processes and remove profile lock markers on macOS."""
        try:
            browser_label = "Chrome" if self.browser_type == "chrome" else "Brave"
            print(f"🔧 Forcing {browser_label} shutdown (macOS)...")
            # Kill common browser processes
            for name in self.browser_process_names:
                try:
                    subprocess.run(["killall", "-9", name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

            # Small delay to allow OS to release locks
            time.sleep(0.5)

            # Remove profile lock files if present
            if self.user_data_dir:
                for marker in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
                    p = os.path.join(self.user_data_dir, marker)
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass
        except Exception:
            pass

    def _is_cdp_reachable(self, url: str) -> bool:
        """Quickly check if a CDP endpoint responds at /json/version."""
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme:
                url = f"http://{url}"
                parsed = urllib.parse.urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            with urllib.request.urlopen(base + "/json/version", timeout=1.5) as resp:  # type: ignore
                return resp.status == 200
        except Exception:
            return False
    
    def _get_screenshot_path(self, step_index: int, action_type: str) -> Path:
        """Generate screenshot file path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_task = "".join(c for c in (self.current_task_name or "task")[:30] 
                           if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        filename = f"step_{step_index:02d}_{action_type}_{safe_task}_{timestamp}.png"
        return self.screenshot_dir / filename
    
    def initialize_browser(self):
        """Initialize the browser agent if not already initialized"""
        if self.agent:
            return
        
        # Use ChatBrowserUse if available, otherwise ChatOpenAI
        if CHAT_BROWSER_USE_AVAILABLE:
            # ChatBrowserUse uses 'bu-latest' or 'bu-1-0' models
            llm = ChatBrowserUse(
                model=self.model,  # Already converted to bu-latest or bu-1-0 in __init__
                api_key=self.api_key,
            )
        else:
            # ChatOpenAI uses GPT model names
            llm = ChatOpenAI(
                model=self.model,  # GPT model name (gpt-4o, gpt-4, etc.)
                api_key=self.api_key,
            )
        
        if self.use_real_browser and self.browser:
            browser_label = "Chrome" if self.browser_type == "chrome" else "Brave"
            print(f"🔗 Connecting to existing {browser_label} browser...")
            try:
                if self.cdp_url:
                    print(f"   CDP URL: {self.cdp_url}")
                print(f"   Executable: {self.executable_path}")
                print(f"   Profile: {self.profile_directory}")
                print(f"   User data dir: {self.user_data_dir}")
            except Exception:
                pass
            if not self.cdp_url:
                print(f"   ⚠️  Make sure {self.browser_type.title()} is fully closed before running!")
            if getattr(self, "_profile_lock_detected", False):
                print(f"   ⚠️  Detected {self.browser_type.title()} profile lock markers. "
                      f"If connection times out, quit {self.browser_type.title()} (Cmd+Q) and retry.")
            self.agent = Agent(
                task="",  # Will be set per action
                browser=self.browser,
                llm=llm,
            )
        else:
            self.agent = Agent(
                task="",  # Will be set per action
                llm=llm,
                headless=self.headless,
            )
    
    def _action_to_description(self, action: Action) -> str:
        """Convert a single Action to natural language description"""
        action_type = action.action_type
        target = action.target_description
        
        if action_type == "navigate":
            url = self._extract_url(target, target)
            return f"Navigate to {url or target}"
        elif action_type == "click":
            if "enter" in target.lower():
                return "Press Enter key"
            else:
                return f"Click on {target}"
        elif action_type == "type":
            value = action.value or ""
            return f"Type '{value}' into {target}"
        elif action_type == "select_option":
            value = action.value or ""
            return f"Select '{value}' from {target}"
        elif action_type == "scroll":
            direction = "down" if "down" in target.lower() else "up" if "up" in target.lower() else ""
            return f"Scroll {direction}"
        elif action_type == "wait":
            return f"Wait for {target}"
        elif action_type == "capture_screenshot":
            # Screenshot capture is handled separately, not as a browser-use action
            # Return a no-op action that just waits briefly
            return "Wait briefly for the page to stabilize"
        elif action_type == "hover":
            return f"Hover over {target}"
        elif action_type == "evaluate_state":
            return f"Evaluate if the task is complete. Check: {target}"
        else:
            return f"{action_type} {target}"
    
    def execute_single_action(
        self,
        action: Action,
        step_index: int = 1,
    ) -> Dict[str, Any]:
        """
        Execute a simple task based on action and return the result with screenshot.
        Each action becomes a complete simple task for browser-use.
        This avoids browser-use's history/state issues by treating each action as a fresh task.
        
        Args:
            action: Action to execute
            step_index: Step number for tracking
            
        Returns:
            Dictionary with step_index, action, result (including screenshot_path)
        """
        # Handle capture_screenshot action type specially - don't execute via browser-use
        if action.action_type == "capture_screenshot":
            screenshot_path = self.capture_current_screenshot(step_index, action.action_type)
            return {
                "step_index": step_index,
                "action_type": action.action_type,
                "action": action,
                "result": {
                    "status": "success",
                    "error_message": None,
                    "screenshot_path": str(screenshot_path) if screenshot_path else None,
                    "details": {"agent_result": "Screenshot captured successfully"}
                }
            }
        
        # Convert action to a simple, complete task for browser-use
        task_text = self._action_to_simple_task(action)
        
        try:
            # Create LLM
            if CHAT_BROWSER_USE_AVAILABLE:
                llm = ChatBrowserUse(
                    model=self.model,
                    api_key=self.api_key,
                )
            else:
                llm = ChatOpenAI(
                    model=self.model,
                    api_key=self.api_key,
                )
            
            # Reuse browser if available, otherwise create new one
            browser_to_use = None
            
            # For CDP connections, always recreate the Browser object to ensure
            # fresh handlers are initialized (browser-use clears state after run_sync)
            if self.use_real_browser and self.cdp_url and self._is_cdp_reachable(self.cdp_url):
                # Recreate Browser connection to ensure fresh handlers
                # The underlying browser process stays the same, so state is maintained
                try:
                    browser_to_use = Browser(
                        cdp_url=self.cdp_url,
                        user_data_dir=self.user_data_dir,
                        profile_directory=self.profile_directory,
                    )
                    self.browser = browser_to_use
                except Exception as e:
                    print(f"   ⚠️  Failed to recreate browser connection: {e}")
                    # Fallback to existing browser if available
                    if self.browser:
                        browser_to_use = self.browser
            elif self.use_real_browser and self.browser:
                # Use existing browser if CDP URL not available
                browser_to_use = self.browser
            elif self.agent and hasattr(self.agent, 'browser') and self.agent.browser:
                browser_to_use = self.agent.browser
                # Update self.browser for consistency
                self.browser = browser_to_use
            
            # Create agent with simple task
            if browser_to_use:
                # Small delay to ensure browser connection is ready
                time.sleep(0.1)
                temp_agent = Agent(
                    task=task_text,
                    browser=browser_to_use,
                    llm=llm,
                )
            else:
                # Create new browser if needed
                temp_agent = Agent(
                    task=task_text,
                    llm=llm,
                    headless=self.headless,
                )
                # Update self.browser for future reuse
                if hasattr(temp_agent, 'browser') and temp_agent.browser:
                    self.browser = temp_agent.browser
            
            # Execute the complete simple task
            result_text: Optional[str] = None
            status = "success"
            error_message = None
            
            try:
                result_text = temp_agent.run_sync()
                # Small delay to let browser state stabilize
                time.sleep(0.5)
                
                # Convert result_text to string safely
                if result_text is not None:
                    if not isinstance(result_text, str):
                        result_text = str(result_text)
            except Exception as e:
                error_message = str(e)
                result_text = f"Error: {error_message}"
                status = "error"
                print(f"   ⚠️  Task execution had issues: {e}")
            
            # Update browser reference for future reuse
            # Note: We don't keep the agent reference since browser-use clears
            # session state after run_sync(), and we'll recreate the Browser connection
            # for the next action anyway
            if hasattr(temp_agent, 'browser') and temp_agent.browser:
                # Only update browser if we're not using CDP (managed browser)
                if not (self.use_real_browser and self.cdp_url):
                    self.browser = temp_agent.browser
            # Clear agent reference to force fresh connection next time
            self.agent = None
            
            # Always capture screenshot after action execution
            screenshot_path = None
            try:
                # Small delay before screenshot to ensure page is stable
                time.sleep(0.3)
                screenshot_path = self.capture_current_screenshot(step_index, action.action_type)
            except Exception as e:
                print(f"   ⚠️  Could not capture screenshot: {e}")
            
            result = {
                "status": status,
                "error_message": error_message,
                "screenshot_path": str(screenshot_path) if screenshot_path else None,
                "details": {"agent_result": result_text if result_text else "Completed"}
            }
            
            return {
                "step_index": step_index,
                "action_type": action.action_type,
                "action": action,
                "result": result
            }
            
        except Exception as e:
            # Capture screenshot even on error
            screenshot_path = None
            try:
                screenshot_path = self.capture_current_screenshot(step_index, action.action_type)
            except:
                pass
            
            return {
                "step_index": step_index,
                "action_type": action.action_type,
                "action": action,
                "result": {
                    "status": "error",
                    "error_message": str(e),
                    "screenshot_path": str(screenshot_path) if screenshot_path else None,
                    "details": {}
                }
            }
    
    def _action_to_simple_task(self, action: Action) -> str:
        """Convert an Action to a simple, complete task description for browser-use"""
        action_type = action.action_type
        target = action.target_description
        
        if action_type == "navigate":
            url = self._extract_url(target, target)
            if url:
                return f"Navigate to {url}"
            else:
                # Extract app name or use target as-is
                if "linear" in target.lower():
                    return "Navigate to https://linear.app"
                elif "notion" in target.lower():
                    return "Navigate to https://www.notion.so"
                else:
                    return f"Navigate to {target}"
        elif action_type == "click":
            if "enter" in target.lower():
                return "Press the Enter key"
            else:
                return f"Click on {target}"
        elif action_type == "type":
            value = action.value or ""
            return f"Type '{value}' into {target}"
        elif action_type == "select_option":
            value = action.value or ""
            return f"Select '{value}' from {target}"
        elif action_type == "scroll":
            direction = "down" if "down" in target.lower() else "up" if "up" in target.lower() else "down"
            return f"Scroll {direction} on the page"
        elif action_type == "wait":
            return f"Wait for {target} to appear"
        elif action_type == "hover":
            return f"Hover over {target}"
        elif action_type == "evaluate_state":
            return f"Check if {target}. Evaluate the current state of the page."
        else:
            return f"{action_type} {target}"
    
    def capture_current_screenshot(self, step_index: int, action_type: str) -> Optional[str]:
        """Capture a screenshot of the current browser state"""
        screenshot_path = self._get_screenshot_path(step_index, action_type)
        try:
            # Try multiple ways to access the Playwright page
            page = None
            
            # Method 1: Try to access browser-use's underlying browser/page
            if self.agent and hasattr(self.agent, 'browser'):
                browser_obj = self.agent.browser
                if browser_obj:
                    # Try different attribute names browser-use might use
                    if hasattr(browser_obj, 'page'):
                        page = browser_obj.page
                    elif hasattr(browser_obj, '_page'):
                        page = browser_obj._page
                    elif hasattr(browser_obj, 'context') and hasattr(browser_obj.context, 'pages'):
                        pages = browser_obj.context.pages
                        if pages:
                            page = pages[0]
            
            # Method 2: Try to access via browser attribute
            if not page and self.browser:
                if hasattr(self.browser, 'page'):
                    page = self.browser.page
                elif hasattr(self.browser, '_page'):
                    page = self.browser._page
                elif hasattr(self.browser, 'context') and hasattr(self.browser.context, 'pages'):
                    pages = self.browser.context.pages
                    if pages:
                        page = pages[0]
            
            # Method 3: Try to get page from browser-use's internal state
            if not page and self.agent:
                # browser-use might store page in different places
                for attr in ['_browser', 'browser', '_context']:
                    if hasattr(self.agent, attr):
                        obj = getattr(self.agent, attr)
                        if obj and hasattr(obj, 'page'):
                            page = obj.page
                            break
                        elif obj and hasattr(obj, 'context') and hasattr(obj.context, 'pages'):
                            pages = obj.context.pages
                            if pages:
                                page = pages[0]
                                break
            
            if page:
                page.screenshot(path=str(screenshot_path))
                print(f"   📸 Screenshot captured: {screenshot_path}")
                return str(screenshot_path)
            else:
                print(f"   ⚠️  Warning: Could not access browser page to capture screenshot")
                return None
        except Exception as e:
            print(f"   ⚠️  Warning: Could not capture screenshot: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_current_url(self) -> Optional[str]:
        """Get the current page URL"""
        try:
            # Try to access browser-use's underlying browser/page
            if self.agent and hasattr(self.agent, 'browser'):
                browser_obj = self.agent.browser
                if browser_obj and hasattr(browser_obj, 'page'):
                    page = browser_obj.page
                    if page:
                        return page.url
            
            # Fallback: try to access via browser attribute
            if self.browser and hasattr(self.browser, 'page'):
                page = self.browser.page
                if page:
                    return page.url
            
            return None
        except Exception:
            return None
    
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
            # If real browser configured, attach to Chrome via CDP; else use managed browser
            # Use ChatBrowserUse if available, otherwise ChatOpenAI (GPT models only)
            if CHAT_BROWSER_USE_AVAILABLE:
                llm = ChatBrowserUse(
                    model=self.model,
                    api_key=self.api_key,
                )
            else:
                llm = ChatOpenAI(
                    model=self.model,
                    api_key=self.api_key,
                )
            if self.use_real_browser and self.browser:
                browser_label = "Chrome" if self.browser_type == "chrome" else "Brave"
                print(f"🔗 Connecting to existing {browser_label} browser...")
                try:
                    if self.cdp_url:
                        print(f"   CDP URL: {self.cdp_url}")
                    print(f"   Executable: {self.executable_path}")
                    print(f"   Profile: {self.profile_directory}")
                    print(f"   User data dir: {self.user_data_dir}")
                except Exception:
                    pass
                if not self.cdp_url:
                    print(f"   ⚠️  Make sure {self.browser_type.title()} is fully closed before running!")
                if getattr(self, "_profile_lock_detected", False):
                    print(f"   ⚠️  Detected {self.browser_type.title()} profile lock markers. "
                          f"If connection times out, quit {self.browser_type.title()} (Cmd+Q) and retry.")
                self.agent = Agent(
                    task=task_description,
                    browser=self.browser,
                    llm=llm,
                )
            else:
                self.agent = Agent(
                    task=task_description,
                    llm=llm,
                    headless=self.headless,
                )
            
            # Run the agent - it will execute all steps with built-in feedback loop
            result_text: Optional[str] = None
            try:
                result_text = self.agent.run_sync()
            except Exception as e:
                # Fallback: if CDP/connect fails in real mode, retry with managed browser
                transient = (
                    "Cannot connect to host localhost",
                    "timed out",
                    "CDP",
                    "ClientConnectorError",
                    "Root CDP client not initialized",
                )
                if self.use_real_browser and any(s in str(e) for s in transient):
                    if self.strict_real_browser:
                        raise
                    print("\n⚠️  Real browser connection failed. Falling back to managed browser.")
                    self.agent = Agent(
                        task=task_description,
                        llm=llm,
                        headless=self.headless,
                    )
                    result_text = self.agent.run_sync()
                else:
                    raise
            
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
