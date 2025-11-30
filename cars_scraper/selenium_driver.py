"""
Selenium WebDriver configuration and utilities.
"""

import logging
import os
from typing import Optional
import random
import time

# Try to import Selenium dependencies
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

# Try to import undetected_chromedriver for better stealth
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

logger = logging.getLogger(__name__)


class SeleniumDriver:
    """Wrapper for Selenium WebDriver with anti-detection features."""
    
    def __init__(self, headless: bool = True, use_undetected: bool = True):
        """
        Initialize Selenium driver.
        
        Args:
            headless: Run browser in headless mode (no GUI)
            use_undetected: Use undetected_chromedriver for better stealth
        """
        self.headless = headless
        self.use_undetected = use_undetected and UNDETECTED_AVAILABLE
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Set up Chrome WebDriver with optimal settings."""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not installed. Install with: pip install selenium")
        
        # Check if display is available when not in headless mode
        if not self.headless:
            display = os.environ.get('DISPLAY')
            if not display:
                logger.warning("DISPLAY environment variable not set. Chrome may not be able to open a visible window.")
                logger.warning("If you're on Linux, you may need X11 forwarding or a display server.")
                logger.warning("Consider using --headless mode or setting up X11 forwarding.")
        
        if self.use_undetected:
            logger.info(f"Using undetected_chromedriver for stealth (headless={self.headless})")
            options = uc.ChromeOptions()
            
            # Headless mode (careful - some sites detect headless)
            if self.headless:
                options.add_argument('--headless=new')  # New headless mode
                logger.debug("Chrome will run in headless mode")
            else:
                logger.info("Chrome will run with visible browser window")
            
            # Performance & stealth options
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            
            # Random user agent from pool
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            options.add_argument(f'user-agent={random.choice(user_agents)}')
            
            # Create driver
            self.driver = uc.Chrome(options=options, version_main=120)
            
        else:
            logger.info(f"Using standard Selenium ChromeDriver (headless={self.headless})")
            options = Options()
            
            if self.headless:
                options.add_argument('--headless=new')
                logger.debug("Chrome will run in headless mode")
            else:
                logger.info("Chrome will run with visible browser window")
            
            # Anti-detection options
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-notifications')
            
            # Random user agent
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            options.add_argument(f'user-agent={user_agent}')
            
            # Create service
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    driver_path = ChromeDriverManager().install()
                    # Fix: webdriver-manager sometimes returns wrong file (e.g., THIRD_PARTY_NOTICES)
                    if 'THIRD_PARTY_NOTICES' in driver_path or not os.path.isfile(driver_path) or not os.access(driver_path, os.X_OK):
                        # Find the actual chromedriver executable
                        driver_dir = os.path.dirname(driver_path)
                        chromedriver_found = False
                        # Search in the directory structure
                        for root, dirs, files in os.walk(driver_dir):
                            for file in files:
                                if file == 'chromedriver':
                                    full_path = os.path.join(root, file)
                                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                                        driver_path = full_path
                                        chromedriver_found = True
                                        logger.debug(f"Found chromedriver at: {driver_path}")
                                        break
                            if chromedriver_found:
                                break
                        if not chromedriver_found:
                            # Try parent directory
                            parent_dir = os.path.dirname(driver_dir)
                            for root, dirs, files in os.walk(parent_dir):
                                for file in files:
                                    if file == 'chromedriver':
                                        full_path = os.path.join(root, file)
                                        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                                            driver_path = full_path
                                            chromedriver_found = True
                                            logger.debug(f"Found chromedriver at: {driver_path}")
                                            break
                                if chromedriver_found:
                                    break
                        if not chromedriver_found:
                            raise FileNotFoundError(f"Could not find chromedriver executable in {driver_dir}")
                    service = Service(driver_path)
                except Exception as e:
                    logger.warning(f"Failed to use ChromeDriverManager: {e}. Trying system chromedriver.")
                    # Fallback: use system ChromeDriver
                    service = Service()
            else:
                # Fallback: use system ChromeDriver
                service = Service()
            
            # Create driver
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Override navigator.webdriver flag
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def get_page(self, url: str, wait_for_element: Optional[str] = None, 
                 wait_timeout: int = 10, scroll: bool = True) -> str:
        """
        Navigate to URL and return page source.
        
        Args:
            url: URL to navigate to
            wait_for_element: CSS selector to wait for before returning
            wait_timeout: Maximum seconds to wait
            scroll: Whether to scroll page to trigger lazy loading
        
        Returns:
            Page HTML source
        """
        logger.debug(f"Navigating to: {url}")
        
        # Navigate to URL
        self.driver.get(url)
        
        # Random human-like delay
        time.sleep(random.uniform(1.5, 3.0))
        
        # Wait for specific element if specified
        if wait_for_element:
            try:
                WebDriverWait(self.driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                )
                logger.debug(f"Found element: {wait_for_element}")
            except TimeoutException:
                logger.warning(f"Timeout waiting for element: {wait_for_element}")
        
        # Scroll to trigger lazy loading
        if scroll:
            self._scroll_page()
        
        # Additional wait for dynamic content
        time.sleep(random.uniform(0.5, 1.5))
        
        return self.driver.page_source
    
    def _scroll_page(self):
        """Scroll page slowly to trigger lazy loading (human-like behavior)."""
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        # Scroll in steps
        current_position = 0
        step = viewport_height // 2  # Scroll half viewport at a time
        
        while current_position < total_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(random.uniform(0.3, 0.7))  # Human-like delay
            current_position += step
            
            # Check if new content loaded (page height increased)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height > total_height:
                total_height = new_height
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
    
    def click_element(self, selector: str, wait_timeout: int = 10) -> bool:
        """
        Click an element by CSS selector.
        
        Args:
            selector: CSS selector
            wait_timeout: Maximum seconds to wait
        
        Returns:
            True if clicked successfully
        """
        try:
            element = WebDriverWait(self.driver, wait_timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            time.sleep(random.uniform(0.5, 1.5))
            return True
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Could not click element {selector}: {e}")
            return False
    
    def wait_for_ajax(self, timeout: int = 10):
        """Wait for jQuery AJAX calls to complete."""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return jQuery.active == 0")
            )
        except:
            # jQuery might not be present, ignore
            pass
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

