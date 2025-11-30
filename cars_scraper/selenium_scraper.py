"""
Selenium-based scraper for JavaScript-heavy dealership sites.
"""

from abc import ABC
from typing import List, Optional
import time
import random
import logging
from bs4 import BeautifulSoup
from .scraper import DealershipScraper, VehicleSummary
from .models import CarListing
from .field_keywords import FIELD_KEYWORDS, get_keywords, contains_keyword
from .car_regexes import (
    first_group, VIN_REGEX, PRICE_REGEX, MILEAGE_REGEX, STOCK_REGEX,
    CONDITION_REGEX, AVAILABILITY_REGEX, BODY_STYLE_LABEL_REGEX, BODY_STYLE_VALUE_REGEX,
    EXTERIOR_COLOR_REGEX, INTERIOR_COLOR_REGEX, TRANSMISSION_REGEX, ENGINE_REGEX,
    FUEL_TYPE_LABEL_REGEX, FUEL_TYPE_VALUE_REGEX, DRIVETRAIN_REGEX, DRIVETRAIN_LABEL_REGEX,
    normalize_drivetrain, parse_price_to_int, is_electric as regex_is_electric
)

# Try to import Selenium driver
try:
    from .selenium_driver import SeleniumDriver
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    SeleniumDriver = None

logger = logging.getLogger(__name__)


class SeleniumDealershipScraper(DealershipScraper):
    """
    Base scraper using Selenium for JavaScript-rendered sites.
    Inherits from DealershipScraper but overrides HTTP methods.
    
    This class uses Selenium to fetch pages (for JavaScript-heavy sites),
    but still uses all the keyword and regex extraction methods from DealershipScraper:
    
    - _find_field_by_keywords() - Uses FIELD_KEYWORDS to find elements
    - _extract_field_value() - Extracts values using keywords
    - _extract_vin_from_page() - Uses VIN_REGEX
    - _extract_price_from_page() - Uses PRICE_REGEX
    - _extract_mileage_from_page() - Uses MILEAGE_REGEX
    - _extract_stock_from_page() - Uses STOCK_REGEX
    - _extract_condition_from_page() - Uses CONDITION_REGEX
    - _extract_fuel_type_from_page() - Uses FUEL_TYPE regex and keywords
    - _extract_availability_from_page() - Uses AVAILABILITY_REGEX
    - _extract_colors_from_page() - Uses COLOR regex patterns
    - _extract_drivetrain_from_page() - Uses DRIVETRAIN_REGEX
    - _extract_transmission_from_page() - Uses TRANSMISSION_REGEX
    - _extract_body_style_from_page() - Uses BODY_STYLE regex
    
    All these methods are inherited from DealershipScraper and work with
    BeautifulSoup objects, so they work seamlessly with Selenium-rendered HTML.
    """
    
    def __init__(self, name: str, base_url: str, headless: bool = True, 
                 min_delay: float = 3.0, max_delay: float = 7.0):
        """
        Initialize Selenium-based scraper.
        
        Args:
            name: Dealership name
            base_url: Base URL
            headless: Run browser in headless mode
            min_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
        """
        # Initialize parent (but we won't use its session)
        super().__init__(
            name=name,
            base_url=base_url,
            min_delay=min_delay,
            max_delay=max_delay,
            use_cache=False,  # Selenium doesn't use requests cache
            check_robots=False  # We're using a real browser
        )
        
        self.headless = headless
        self.driver: Optional[SeleniumDriver] = None
    
    def _init_driver(self):
        """Initialize Selenium driver (lazy initialization)."""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not installed. Install with: pip install selenium webdriver-manager undetected-chromedriver")
        
        if self.driver is None:
            self.driver = SeleniumDriver(headless=self.headless, use_undetected=True)
            logger.info(f"{self.name}: Initialized Selenium driver")
    
    def _close_driver(self):
        """Close Selenium driver."""
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def _get_page(self, url: str, wait_for: Optional[str] = None, 
                  scroll: bool = True) -> BeautifulSoup:
        """
        Fetch page using Selenium instead of requests.
        
        Args:
            url: URL to fetch
            wait_for: CSS selector to wait for
            scroll: Whether to scroll to load lazy content
        
        Returns:
            BeautifulSoup object
        """
        self._init_driver()
        self._rate_limit()
        
        try:
            # Get page with Selenium
            html_source = self.driver.get_page(
                url=url,
                wait_for_element=wait_for,
                scroll=scroll
            )
            
            return BeautifulSoup(html_source, 'lxml')
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to fetch {url} with Selenium: {e}")
            raise
    
    def scrape(self) -> List[CarListing]:
        """
        Override scrape to properly manage Selenium lifecycle.
        """
        try:
            # Initialize driver once for entire scrape
            self._init_driver()
            
            # Call parent scrape method
            listings = super().scrape()
            
            return listings
            
        finally:
            # Always close driver when done
            self._close_driver()

