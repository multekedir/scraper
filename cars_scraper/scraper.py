"""
Base scraper class and framework for dealership sites.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
import time
import random
import re
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from .models import CarListing
from .robots import RobotsChecker
from .field_keywords import FIELD_KEYWORDS, contains_keyword, get_keywords
from .car_regexes import (
    first_group, VIN_REGEX, PRICE_REGEX, MILEAGE_REGEX, STOCK_REGEX,
    CONDITION_REGEX, AVAILABILITY_REGEX, BODY_STYLE_LABEL_REGEX, BODY_STYLE_VALUE_REGEX,
    EXTERIOR_COLOR_REGEX, INTERIOR_COLOR_REGEX, TRANSMISSION_REGEX, ENGINE_REGEX,
    FUEL_TYPE_LABEL_REGEX, FUEL_TYPE_VALUE_REGEX, DRIVETRAIN_REGEX, DRIVETRAIN_LABEL_REGEX,
    normalize_drivetrain, parse_price_to_int, is_electric as regex_is_electric
)

# Try to import requests_cache for caching support
try:
    import requests_cache
    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False

logger = logging.getLogger(__name__)


class VehicleSummary:
    """Summary of a vehicle from a listing page (before detail page scrape)."""
    def __init__(self, detail_url: str, title: str = "", price: Optional[float] = None):
        self.detail_url = detail_url
        self.title = title
        self.price = price


class DealershipScraper(ABC):
    """Base class for dealership scrapers with improved architecture."""
    
    def __init__(self, name: str, base_url: str, min_delay: float = 1.0, max_delay: float = 2.0, use_cache: bool = True, check_robots: bool = True):
        """
        Initialize the scraper.
        
        Args:
            name: Name of the dealership
            base_url: Base URL of the dealership website
            min_delay: Minimum delay between requests in seconds (default: 1.0)
            max_delay: Maximum delay between requests in seconds (default: 2.0)
            use_cache: Whether to use caching if available (default: True)
            check_robots: Whether to check robots.txt (default: True)
        """
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.use_cache = use_cache and CACHING_AVAILABLE
        self.last_request_time = 0
        
        # Set up robots.txt checker
        self.robots_checker: Optional[RobotsChecker] = None
        if check_robots:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            self.robots_checker = RobotsChecker(base_url, user_agent)
            self.robots_checker.check()
            disallowed = self.robots_checker.get_disallowed_paths()
            if disallowed:
                logger.info(f"{name}: Found {len(disallowed)} disallowed paths in robots.txt")
        
        # Set up session with caching if available
        if self.use_cache:
            # Create a cache with 1 hour expiration
            cache_name = f".cache_{name.lower().replace(' ', '_')}"
            self.session = requests_cache.CachedSession(
                cache_name,
                expire_after=timedelta(hours=1),
                backend='sqlite'
            )
        else:
            self.session = requests.Session()
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _rate_limit(self):
        """Enforce random rate limiting between requests (1-2 seconds)."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        # Generate random delay between min_delay and max_delay
        random_delay = random.uniform(self.min_delay, self.max_delay)
        
        if time_since_last_request < random_delay:
            sleep_time = random_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_page(self, url: str, params: dict = None, use_cache: bool = None, check_robots: bool = True) -> BeautifulSoup:
        """
        Fetch a page and return parsed HTML.
        
        Args:
            url: URL to fetch
            params: Query parameters
            use_cache: Override instance cache setting for this request (None uses instance default)
            check_robots: Whether to check robots.txt before fetching (default: True)
        
        Returns:
            BeautifulSoup object of the parsed HTML
        
        Raises:
            requests.RequestException: If the request fails
            ValueError: If robots.txt disallows the URL
        """
        # Check robots.txt
        if check_robots and self.robots_checker:
            if not self.robots_checker.is_allowed(url):
                raise ValueError(f"robots.txt disallows: {url}")
        
        self._rate_limit()
        
        try:
            # If using cache, requests_cache will automatically return cached responses
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise requests.RequestException(f"Failed to fetch {url}: {str(e)}")
    
    def clear_cache(self):
        """Clear the cache for this scraper."""
        if self.use_cache and hasattr(self.session, 'cache'):
            self.session.cache.clear()
    
    def get_listing_urls(self) -> List[str]:
        """
        Get all listing page URLs (handles pagination).
        
        Returns:
            List of listing page URLs
        
        Note:
            Default implementation returns a single inventory page.
            Override for sites with pagination or multiple inventory pages.
        """
        # Default: assume single inventory page
        # Subclasses should override this
        return [f"{self.base_url}/inventory"]
    
    def parse_list_page(self, html: BeautifulSoup, page_url: str) -> List[VehicleSummary]:
        """
        Parse a listing page to extract vehicle summaries.
        
        Args:
            html: Parsed HTML of the listing page
            page_url: URL of the listing page
        
        Returns:
            List of VehicleSummary objects
        
        Note:
            Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement parse_list_page")
    
    def parse_detail_page(self, html: BeautifulSoup, detail_url: str) -> Optional[CarListing]:
        """
        Parse a vehicle detail page to extract full vehicle information.
        
        Args:
            html: Parsed HTML of the detail page
            detail_url: URL of the detail page
        
        Returns:
            CarListing object or None if parsing fails
        
        Note:
            Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement parse_detail_page")
    
    def _extract_json_ld(self, html: BeautifulSoup) -> Optional[Dict]:
        """
        Extract JSON-LD structured data from HTML.
        
        Args:
            html: Parsed HTML
        
        Returns:
            Dictionary with structured data or None
        """
        scripts = html.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Vehicle', 'Car', 'Automotive']:
                    return data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') in ['Vehicle', 'Car', 'Automotive']:
                            return item
            except (json.JSONDecodeError, AttributeError):
                continue
        return None
    
    def scrape(self) -> List[CarListing]:
        """
        Main scraping method that orchestrates the scraping process.
        
        Returns:
            List of CarListing objects
        
        This method:
        1. Gets all listing page URLs
        2. Parses each listing page for vehicle summaries
        3. Fetches and parses each detail page
        4. Returns complete CarListing objects
        """
        all_listings: List[CarListing] = []
        
        try:
            listing_urls = self.get_listing_urls()
            logger.info(f"{self.name}: Found {len(listing_urls)} listing page(s)")
            
            for listing_url in listing_urls:
                try:
                    html = self._get_page(listing_url)
                    summaries = self.parse_list_page(html, listing_url)
                    logger.info(f"{self.name}: Found {len(summaries)} vehicles on {listing_url}")
                    
                    for summary in summaries:
                        try:
                            detail_html = self._get_page(summary.detail_url)
                            listing = self.parse_detail_page(detail_html, summary.detail_url)
                            if listing:
                                all_listings.append(listing)
                        except Exception as e:
                            logger.warning(f"{self.name}: Failed to parse detail page {summary.detail_url}: {e}")
                            continue
                except Exception as e:
                    logger.error(f"{self.name}: Failed to process listing page {listing_url}: {e}")
                    continue
            
            logger.info(f"{self.name}: Successfully scraped {len(all_listings)} vehicles")
            return all_listings
            
        except Exception as e:
            logger.error(f"{self.name}: Scraping failed: {e}")
            raise
    
    def _extract_price(self, price_text: str) -> float:
        """
        Extract numeric price from text.
        
        Args:
            price_text: Price text (e.g., "$45,999" or "45999")
        
        Returns:
            Numeric price value
        """
        # Remove common currency symbols and formatting
        price_text = price_text.replace('$', '').replace(',', '').replace(' ', '')
        # Remove any non-numeric characters except decimal point
        price_text = ''.join(c for c in price_text if c.isdigit() or c == '.')
        try:
            return float(price_text)
        except ValueError:
            return 0.0
    
    def _extract_year(self, year_text: str) -> int:
        """
        Extract year from text.
        
        Args:
            year_text: Year text (e.g., "2024" or "2024 Model")
        
        Returns:
            Year as integer
        """
        # Extract first 4-digit number
        match = re.search(r'\b(19|20)\d{2}\b', str(year_text))
        if match:
            return int(match.group())
        return datetime.now().year
    
    def _is_electric_keyword(self, text: str) -> bool:
        """
        Check if text contains electric vehicle keywords.
        
        Args:
            text: Text to check
        
        Returns:
            True if text suggests electric vehicle
        """
        if not text:
            return False
        text_lower = text.lower()
        electric_keywords = [
            'electric', 'ev', 'battery', 'plug-in', 'plugin', 
            'phev', 'bev', 'tesla', 'rivian', 'lucid',
            'electric vehicle', 'zero emission', 'zero-emission',
            'electric drive', 'electric motor'
        ]
        return any(keyword in text_lower for keyword in electric_keywords)
    
    def _normalize_fuel_type(self, fuel_text: str) -> Optional[str]:
        """
        Normalize fuel type text to standard values.
        
        Args:
            fuel_text: Raw fuel type text
        
        Returns:
            Normalized fuel type: "electric", "hybrid", "gasoline", "diesel", "phev", "bev", or None
        """
        if not fuel_text:
            return None
        
        text_lower = fuel_text.lower()
        
        if any(kw in text_lower for kw in ['electric', 'ev', 'bev', 'battery electric']):
            if 'plug-in' in text_lower or 'phev' in text_lower:
                return "phev"
            return "electric"
        elif 'hybrid' in text_lower:
            if 'plug-in' in text_lower or 'phev' in text_lower:
                return "phev"
            return "hybrid"
        elif 'gasoline' in text_lower or 'gas' in text_lower:
            return "gasoline"
        elif 'diesel' in text_lower:
            return "diesel"
        
        return None
    
    def _normalize_new_used(self, condition_text: str) -> str:
        """
        Normalize new/used condition text.
        
        Args:
            condition_text: Raw condition text
        
        Returns:
            Normalized condition: "new", "used", or "cpo"
        """
        if not condition_text:
            return "new"
        
        text_lower = condition_text.lower()
        
        if 'certified' in text_lower or 'cpo' in text_lower or 'c.p.o' in text_lower:
            return "cpo"
        elif 'used' in text_lower or 'pre-owned' in text_lower:
            return "used"
        else:
            return "new"
    
    def _extract_mileage(self, mileage_text: str) -> Tuple[Optional[int], str]:
        """
        Extract mileage value and units from text.
        
        Args:
            mileage_text: Text containing mileage (e.g., "5 mi", "12 miles", "100 km")
        
        Returns:
            Tuple of (mileage_value, units) where units is "mi" or "km"
        """
        if not mileage_text:
            return None, "mi"
        
        # Extract number
        match = re.search(r'(\d+(?:[.,]\d+)?)', mileage_text.replace(',', ''))
        if not match:
            return None, "mi"
        
        value = int(float(match.group(1)))
        
        # Determine units
        text_lower = mileage_text.lower()
        if 'km' in text_lower or 'kilometer' in text_lower:
            units = "km"
        else:
            units = "mi"
        
        return value, units
    
    def _parse_vehicle_title(self, title: str) -> Dict[str, Optional[str]]:
        """
        Parse vehicle title like "2025 Hyundai IONIQ 5 SEL" into components.
        
        Args:
            title: Vehicle title text
        
        Returns:
            Dictionary with year, make, model, trim
        """
        result = {
            'year': None,
            'make': None,
            'model': None,
            'trim': None
        }
        
        if not title:
            return result
        
        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', title)
        if year_match:
            result['year'] = int(year_match.group())
            title = title.replace(year_match.group(), '').strip()
        
        # Common makes (expand as needed)
        makes = [
            'Tesla', 'Hyundai', 'Kia', 'Ford', 'Chevrolet', 'Chevy', 'Nissan',
            'BMW', 'Mercedes-Benz', 'Mercedes', 'Audi', 'Volkswagen', 'VW',
            'Toyota', 'Honda', 'Mazda', 'Subaru', 'Volvo', 'Polestar',
            'Rivian', 'Lucid', 'Fisker', 'Genesis', 'Cadillac', 'Lincoln',
            'Jeep', 'Ram', 'GMC', 'Buick', 'Chrysler', 'Dodge', 'INFINITI',
            'Acura', 'Lexus', 'Jaguar', 'Land Rover', 'MINI', 'Mitsubishi',
            'Porsche', 'Alfa Romeo', 'Fiat', 'Maserati'
        ]
        
        words = title.split()
        if words:
            # Try to find make
            for i, word in enumerate(words):
                for make in makes:
                    if word == make or title.startswith(make):
                        result['make'] = make
                        # Model is typically after make
                        if i + 1 < len(words):
                            # Model might be multiple words
                            model_words = []
                            for j in range(i + 1, len(words)):
                                model_words.append(words[j])
                            result['model'] = ' '.join(model_words)
                        break
                if result['make']:
                    break
        
        return result
    
    def _find_field_by_keywords(self, html: BeautifulSoup, field_name: str, 
                                 tag: str = None, class_contains: str = None) -> List:
        """
        Find elements containing keywords for a specific field.
        
        Args:
            html: BeautifulSoup object to search
            field_name: Field name (e.g., "price", "vin", "mileage")
            tag: Optional HTML tag to limit search (e.g., "div", "span", "td")
            class_contains: Optional class name substring to filter by
        
        Returns:
            List of matching elements
        """
        keywords = get_keywords(field_name)
        if not keywords:
            return []
        
        matches = []
        
        # Search in all text or specific tags
        if tag:
            elements = html.find_all(tag)
        else:
            elements = html.find_all(True)  # All elements
        
        for element in elements:
            # Filter by class if specified
            if class_contains:
                classes = element.get('class', [])
                if not any(class_contains.lower() in str(c).lower() for c in classes):
                    continue
            
            text = element.get_text(strip=True)
            if not text:
                continue
            
            # Check if text contains any keyword
            if contains_keyword(text, field_name, case_sensitive=False):
                matches.append(element)
        
        return matches
    
    def _extract_field_value(self, html: BeautifulSoup, field_name: str, 
                             label_pattern: str = None) -> Optional[str]:
        """
        Extract field value by finding label and getting adjacent value.
        
        Args:
            html: BeautifulSoup object to search
            field_name: Field name (e.g., "vin", "stock_number")
            label_pattern: Optional regex pattern for label
        
        Returns:
            Extracted value or None
        """
        keywords = get_keywords(field_name)
        if not keywords:
            return None
        
        # Try different patterns to find label:value pairs
        patterns = [
            # Pattern: <label>Field:</label> <value>
            r'({})\s*:?\s*([^\n\r<]+)'.format('|'.join(re.escape(kw) for kw in keywords)),
            # Pattern: <dt>Field</dt><dd>value</dd>
            # Pattern: <span>Field:</span> <span>value</span>
        ]
        
        text = html.get_text()
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(2).strip()
                # Clean up value
                value = re.sub(r'\s+', ' ', value)
                if value and value not in keywords:  # Don't return the keyword itself
                    return value
        
        # Try finding in definition lists (dt/dd)
        for dt in html.find_all(['dt', 'th', 'label']):
            dt_text = dt.get_text(strip=True)
            if contains_keyword(dt_text, field_name):
                # Get next sibling or parent's next sibling
                next_elem = dt.find_next_sibling(['dd', 'td', 'span', 'div'])
                if next_elem:
                    value = next_elem.get_text(strip=True)
                    if value:
                        return value
        
        # Try finding in tables (th/td pairs)
        for th in html.find_all('th'):
            th_text = th.get_text(strip=True)
            if contains_keyword(th_text, field_name):
                # Find corresponding td
                tr = th.find_parent('tr')
                if tr:
                    tds = tr.find_all('td')
                    if tds:
                        value = tds[0].get_text(strip=True)
                        if value:
                            return value
        
        return None
    
    def _extract_price_from_page(self, html: BeautifulSoup) -> Dict[str, Optional[float]]:
        """
        Extract all price types from a page (MSRP, sale price, etc.).
        Uses regex patterns for more precise extraction.
        
        Args:
            html: BeautifulSoup object
        
        Returns:
            Dictionary with msrp, sale_price, total_price
        """
        prices = {
            'msrp': None,
            'sale_price': None,
            'total_price': None
        }
        
        page_text = html.get_text()
        
        # Use regex to find all prices
        price_matches = PRICE_REGEX.findall(page_text)
        
        # Also check keyword-based elements as fallback
        price_elements = self._find_field_by_keywords(html, "price")
        
        all_prices = []
        
        # Extract prices from regex matches
        for price_str in price_matches:
            price_value = parse_price_to_int(price_str)
            if price_value and price_value > 0:
                all_prices.append(price_value)
        
        # Extract prices from keyword-based elements
        for elem in price_elements:
            text = elem.get_text(strip=True)
            price_value = self._extract_price(text)
            if price_value > 0:
                all_prices.append(price_value)
        
        # Find context for each price to determine type
        for price_value in all_prices:
            # Find the context around this price
            price_pattern = re.compile(rf'\$\s*{re.escape(str(price_value).replace(",", ""))}')
            for match in price_pattern.finditer(page_text):
                start = max(0, match.start() - 50)
                end = min(len(page_text), match.end() + 50)
                context = page_text[start:end].lower()
                
                # Determine price type based on context
                if any(kw in context for kw in ['msrp', 'manufacturer', 'sticker', 'retail']):
                    if prices['msrp'] is None or price_value > prices['msrp']:
                        prices['msrp'] = price_value
                elif any(kw in context for kw in ['sale', 'our price', 'internet', 'e-price', 'dealer price', 'special']):
                    if prices['sale_price'] is None or price_value < (prices['sale_price'] or float('inf')):
                        prices['sale_price'] = price_value
                elif any(kw in context for kw in ['total', 'final', 'out the door', 'otd']):
                    prices['total_price'] = price_value
                else:
                    # Default to sale_price if not specified
                    if prices['sale_price'] is None:
                        prices['sale_price'] = price_value
        
        # If we have sale_price but no total_price, use sale_price as total
        if prices['total_price'] is None and prices['sale_price']:
            prices['total_price'] = prices['sale_price']
        
        return prices
    
    def _extract_vin_from_page(self, html: BeautifulSoup) -> Optional[str]:
        """Extract VIN from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Use regex first (most reliable)
        vin = first_group(VIN_REGEX, page_text)
        if vin:
            return vin.upper()
        
        # Fallback to keyword-based extraction
        vin = self._extract_field_value(html, "vin")
        if vin:
            vin = re.sub(r'[^A-Z0-9]', '', vin.upper())
            if len(vin) == 17:
                return vin
        
        return None
    
    def _extract_stock_from_page(self, html: BeautifulSoup) -> Optional[str]:
        """Extract stock number from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Use regex first
        stock = first_group(STOCK_REGEX, page_text)
        if stock:
            return stock.strip()
        
        # Fallback to keyword-based extraction
        stock = self._extract_field_value(html, "stock_number")
        if stock:
            stock = re.sub(r'\s+', ' ', stock).strip()
            return stock
        
        return None
    
    def _extract_mileage_from_page(self, html: BeautifulSoup) -> Tuple[Optional[int], str]:
        """Extract mileage from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Use regex first
        mileage_str = first_group(MILEAGE_REGEX, page_text)
        if mileage_str:
            value = parse_price_to_int(mileage_str)
            if value is not None:
                return value, "mi"
        
        # Fallback to keyword-based extraction
        mileage_text = self._extract_field_value(html, "mileage")
        if mileage_text:
            return self._extract_mileage(mileage_text)
        
        return None, "mi"
    
    def _extract_condition_from_page(self, html: BeautifulSoup) -> str:
        """Extract new/used condition from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Use regex first
        condition_raw = first_group(CONDITION_REGEX, page_text)
        if condition_raw:
            return self._normalize_new_used(condition_raw)
        
        # Check page title and headings
        title = html.find('title')
        if title:
            title_text = title.get_text()
            condition_raw = first_group(CONDITION_REGEX, title_text)
            if condition_raw:
                return self._normalize_new_used(condition_raw)
            if contains_keyword(title_text, "condition"):
                condition = self._normalize_new_used(title_text)
                if condition != "new":
                    return condition
        
        # Fallback to keyword-based extraction
        condition_text = self._extract_field_value(html, "condition")
        if condition_text:
            return self._normalize_new_used(condition_text)
        
        # Default to new
        return "new"
    
    def _extract_fuel_type_from_page(self, html: BeautifulSoup) -> Optional[str]:
        """Extract fuel type from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Check JSON-LD first (most reliable)
        json_ld = self._extract_json_ld(html)
        if json_ld and 'fuelType' in json_ld:
            return self._normalize_fuel_type(json_ld['fuelType'])
        
        # Use regex for fuel type label
        fuel_text = first_group(FUEL_TYPE_LABEL_REGEX, page_text)
        if fuel_text:
            normalized = self._normalize_fuel_type(fuel_text)
            if normalized:
                return normalized
        
        # Use regex for fuel type value
        fuel_text = first_group(FUEL_TYPE_VALUE_REGEX, page_text)
        if fuel_text:
            normalized = self._normalize_fuel_type(fuel_text)
            if normalized:
                return normalized
        
        # Check engine/motor description using regex
        engine_text = first_group(ENGINE_REGEX, page_text)
        if engine_text:
            if regex_is_electric(engine_text):
                return self._normalize_fuel_type(engine_text)
        
        # Fallback to keyword-based extraction
        fuel_text = self._extract_field_value(html, "fuel_type")
        if fuel_text:
            return self._normalize_fuel_type(fuel_text)
        
        # Check in engine description
        engine_elements = html.find_all(string=re.compile(r'engine|motor', re.I))
        for elem in engine_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text()
                if self._is_electric_keyword(text) or regex_is_electric(text):
                    return self._normalize_fuel_type(text)
        
        return None
    
    def _extract_availability_from_page(self, html: BeautifulSoup) -> Optional[str]:
        """Extract availability status from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Use regex first
        availability_raw = first_group(AVAILABILITY_REGEX, page_text)
        if availability_raw:
            text_lower = availability_raw.lower()
            if 'transit' in text_lower or 'way' in text_lower or 'arriving' in text_lower or 'coming' in text_lower:
                return "in_transit"
            elif 'sold' in text_lower:
                return "sold"
            elif 'reserved' in text_lower:
                return "reserved"
            elif 'stock' in text_lower or 'available' in text_lower:
                return "available"
        
        # Fallback to keyword-based extraction
        availability_text = self._extract_field_value(html, "availability")
        if availability_text:
            text_lower = availability_text.lower()
            if 'transit' in text_lower or 'way' in text_lower:
                return "in_transit"
            elif 'sold' in text_lower:
                return "sold"
            elif 'reserved' in text_lower:
                return "reserved"
            elif 'stock' in text_lower or 'available' in text_lower:
                return "available"
        
        # Check for status badges/indicators
        status_elements = self._find_field_by_keywords(html, "availability")
        for elem in status_elements:
            text = elem.get_text(strip=True).lower()
            if 'transit' in text or 'way' in text:
                return "in_transit"
            elif 'sold' in text:
                return "sold"
            elif 'reserved' in text:
                return "reserved"
            elif 'stock' in text or 'available' in text:
                return "available"
        
        return None
    
    def _extract_colors_from_page(self, html: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
        """Extract exterior and interior colors from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Use regex first
        exterior = first_group(EXTERIOR_COLOR_REGEX, page_text)
        interior = first_group(INTERIOR_COLOR_REGEX, page_text)
        
        if exterior:
            exterior = exterior.strip()
        if interior:
            interior = interior.strip()
        
        # Fallback to keyword-based extraction if regex didn't find anything
        if not exterior or not interior:
            color_elements = self._find_field_by_keywords(html, "colors")
            
            for elem in color_elements:
                text = elem.get_text(strip=True)
                text_lower = text.lower()
                
                if 'exterior' in text_lower or 'ext.' in text_lower:
                    if not exterior:
                        color_value = self._extract_field_value(html, "colors")
                        if color_value and 'exterior' in color_value.lower():
                            exterior = color_value.replace('Exterior Color', '').replace('Ext. Color', '').strip()
                elif 'interior' in text_lower or 'int.' in text_lower:
                    if not interior:
                        color_value = self._extract_field_value(html, "colors")
                        if color_value and 'interior' in color_value.lower():
                            interior = color_value.replace('Interior Color', '').replace('Int. Color', '').strip()
        
        return exterior, interior
    
    def _extract_drivetrain_from_page(self, html: BeautifulSoup) -> Optional[str]:
        """Extract drivetrain from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Try label regex first
        dt_raw = first_group(DRIVETRAIN_LABEL_REGEX, page_text)
        if dt_raw:
            normalized = normalize_drivetrain(dt_raw)
            if normalized:
                return normalized
        
        # Try value regex
        dt_raw = first_group(DRIVETRAIN_REGEX, page_text)
        if dt_raw:
            normalized = normalize_drivetrain(dt_raw)
            if normalized:
                return normalized
        
        return None
    
    def _extract_transmission_from_page(self, html: BeautifulSoup) -> Optional[str]:
        """Extract transmission from page using regex (more precise)."""
        page_text = html.get_text()
        
        transmission = first_group(TRANSMISSION_REGEX, page_text)
        if transmission:
            return transmission.strip()
        
        return None
    
    def _extract_body_style_from_page(self, html: BeautifulSoup) -> Optional[str]:
        """Extract body style from page using regex (more precise)."""
        page_text = html.get_text()
        
        # Try label regex first
        body_style = first_group(BODY_STYLE_LABEL_REGEX, page_text)
        if body_style:
            return body_style.strip()
        
        # Fallback to value regex
        body_style = first_group(BODY_STYLE_VALUE_REGEX, page_text)
        if body_style:
            return body_style.strip()
        
        return None

