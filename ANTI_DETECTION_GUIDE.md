# Anti-Detection Guide for Browser Automation

This guide explains how to prevent websites from detecting automated browsers and provides multiple solutions.

## Problem

Websites can detect automated browsers through various methods:
- `navigator.webdriver` property (set to `true` by Selenium)
- Chrome automation flags
- Missing browser properties (plugins, languages, etc.)
- Behavioral patterns (unnatural mouse movements, timing, etc.)

## Solutions

### 1. Enhanced Selenium (Current Implementation)

The `browser_api.py` file has been updated with anti-detection measures:

**Features:**
- Removes `navigator.webdriver` property
- Disables automation flags
- Adds realistic browser properties (plugins, languages)
- Uses Chrome DevTools Protocol (CDP) to inject stealth scripts

**Usage:**
```python
from src.agentA.browser_api import BrowserAPI

browser = BrowserAPI(
    user_data_dir="~/Library/Application Support/Google/Chrome",
    profile_directory="Default"
)
browser.start_browser()
```

### 2. Undetected ChromeDriver (Recommended)

`undetected-chromedriver` is a library specifically designed to bypass Chrome's automation detection.

**Advantages:**
- Automatically patches ChromeDriver
- Handles Chrome version matching
- Implements multiple stealth techniques
- Actively maintained and updated

**Installation:**
```bash
pip install undetected-chromedriver
```

**Usage:**
```python
# Option 1: Use the stealth browser API
from src.agentA.browser_api_stealth import BrowserAPI

browser = BrowserAPI(
    user_data_dir="~/Library/Application Support/Google/Chrome",
    profile_directory="Default"
)
browser.start_browser()

# Option 2: Use directly
import undetected_chromedriver as uc

driver = uc.Chrome()
driver.get("https://example.com")
```

**To use with AgentA:**
Modify `src/agentA/agent_a.py` to import from `browser_api_stealth` instead of `browser_api`:
```python
from src.agentA.browser_api_stealth import BrowserAPI  # Instead of browser_api
```

### 3. Playwright (Alternative Library)

You already have Playwright installed. It has better stealth capabilities than Selenium.

**Advantages:**
- Better anti-detection by default
- More modern API
- Supports multiple browsers (Chromium, Firefox, WebKit)
- Built-in stealth mode

**Usage:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    page = context.new_page()
    page.goto("https://example.com")
```

### 4. Browser-Use (AI-Powered)

You already have `browser-use` installed. It's an AI-powered browser automation tool.

**Advantages:**
- Uses AI to interact with browsers
- May have built-in anti-detection
- More natural interaction patterns

**Usage:**
Check the `browser-use` documentation for usage examples.

## Best Practices

1. **Use Real User Profiles**: Reuse existing Chrome profiles with cookies and login sessions
   ```python
   user_data_dir="~/Library/Application Support/Google/Chrome"
   profile_directory="Default"
   ```

2. **Add Random Delays**: Avoid predictable timing patterns
   ```python
   import random
   time.sleep(random.uniform(1, 3))
   ```

3. **Use Realistic User Agents**: Match your actual browser
   ```python
   options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...")
   ```

4. **Rotate IPs/Proxies**: For large-scale automation (if needed)

5. **Avoid Headless Mode**: Headless browsers are easier to detect

6. **Human-like Behavior**: 
   - Random mouse movements
   - Variable scroll speeds
   - Natural typing delays

## Comparison

| Solution | Ease of Use | Effectiveness | Maintenance |
|----------|-------------|---------------|-------------|
| Enhanced Selenium | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Undetected ChromeDriver | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Playwright | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Browser-Use | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

## Recommendation

For best results, use **undetected-chromedriver** (`browser_api_stealth.py`). It's specifically designed for this purpose and handles most detection methods automatically.

## Testing Detection

You can test if your browser is detected by visiting:
- https://bot.sannysoft.com/
- https://arh.antoinevastel.com/bots/areyouheadless
- https://intoli.com/blog/not-possible-to-block-chrome-headless/

These sites will show you what detection methods are being used and whether your browser passes them.



