"""
Selenium-based generic scraper that uses keywords and regex for extraction.
Combines Selenium (for JavaScript rendering) with generic parsing logic.
"""

from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
from ..selenium_scraper import SeleniumDealershipScraper
from ..scraper import VehicleSummary
from ..models import CarListing
from ..dealership_loader import DealershipInfo
from ..field_keywords import FIELD_KEYWORDS, get_keywords, contains_keyword
from ..car_regexes import (
    first_group, VIN_REGEX, PRICE_REGEX, MILEAGE_REGEX, STOCK_REGEX,
    CONDITION_REGEX, AVAILABILITY_REGEX, BODY_STYLE_LABEL_REGEX, BODY_STYLE_VALUE_REGEX,
    EXTERIOR_COLOR_REGEX, INTERIOR_COLOR_REGEX, TRANSMISSION_REGEX, ENGINE_REGEX,
    FUEL_TYPE_LABEL_REGEX, FUEL_TYPE_VALUE_REGEX, DRIVETRAIN_REGEX, DRIVETRAIN_LABEL_REGEX,
    normalize_drivetrain, parse_price_to_int, is_electric as regex_is_electric
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SeleniumGenericDealershipScraper(SeleniumDealershipScraper):
    """
    Generic Selenium scraper that uses keywords and regex for extraction.
    Works exactly like GenericDealershipScraper but uses Selenium for page fetching.
    """
    
    def __init__(self, dealership_info: DealershipInfo, headless: bool = True):
        """
        Initialize scraper for a specific dealership.
        
        Args:
            dealership_info: DealershipInfo object with name, website, and city
            headless: Run browser in headless mode
        """
        super().__init__(
            name=dealership_info.name,
            base_url=dealership_info.website,
            headless=headless,
            min_delay=3.0,  # Slower = less bot-like
            max_delay=7.0,  # Random delays 3-7 seconds
        )
        self.dealership_info = dealership_info
        self.city = dealership_info.city
        # Extract state from city if available
        self.state = self._extract_state_from_city(dealership_info.city)
    
    def _extract_state_from_city(self, city: str) -> Optional[str]:
        """Extract state abbreviation from city string if present."""
        if 'OR' in city.upper() or 'Oregon' in city:
            return "OR"
        elif 'WA' in city.upper() or 'Washington' in city:
            return "WA"
        return "OR"  # Default
    
    def get_listing_urls(self) -> List[str]:
        """
        Get listing page URLs - same logic as GenericDealershipScraper.
        Uses new_inventory_url if available, otherwise tries common patterns.
        """
        # If new_inventory_url is provided in CSV, use it directly
        if self.dealership_info.new_inventory_url:
            logger.info(f"{self.name}: Using provided inventory URL: {self.dealership_info.new_inventory_url}")
            return [self.dealership_info.new_inventory_url]
        
        # Otherwise, try common inventory page patterns
        base = self.base_url.rstrip('/')
        patterns = [
            f"{base}/inventory",
            f"{base}/new-inventory",
            f"{base}/inventory/new",
            f"{base}/new-vehicles",
            f"{base}/vehicles/new",
            f"{base}/search/new",
            f"{base}/inventory/index.htm",
            f"{base}/new",
        ]
        
        # Try to find the actual inventory page
        for pattern in patterns:
            try:
                html = self._get_page(pattern, wait_for=None, scroll=False)
                if self._is_inventory_page(html):
                    logger.debug(f"{self.name}: Found inventory page at {pattern}")
                    return [pattern]
            except Exception as e:
                logger.debug(f"{self.name}: {pattern} not accessible: {e}")
                continue
        
        # Default fallback
        return [f"{base}/inventory"]
    
    def _is_inventory_page(self, html: BeautifulSoup) -> bool:
        """Check if a page looks like an inventory/listing page."""
        text = html.get_text().lower()
        inventory_keywords = get_keywords("name") + ["inventory", "vehicles", "browse", "available"]
        vehicle_indicators = html.find_all(['div', 'article', 'li'], 
                                          class_=lambda x: x and any(
                                              kw in str(x).lower() 
                                              for kw in ['vehicle', 'inventory', 'car', 'listing', 'item']
                                          ))
        price_elements = self._find_field_by_keywords(html, "price")
        return (any(kw in text for kw in inventory_keywords) or 
                len(vehicle_indicators) >= 3 or
                len(price_elements) >= 2)
    
    def parse_list_page(self, html: BeautifulSoup, page_url: str) -> List[VehicleSummary]:
        """
        Parse listing page using keywords and flexible selectors.
        Same logic as GenericDealershipScraper.
        """
        summaries = []
        
        # Try multiple selector patterns to find vehicle cards
        vehicle_keywords = ['vehicle', 'inventory', 'car', 'listing', 'item', 'stock']
        selectors = [
            '.vehicle-card', '.inventory-item', '.vehicle-listing', '.car-listing',
            '[data-vehicle-id]', '[data-vin]', '.vehicle', '.inventory-vehicle',
            'article.vehicle', 'div.vehicle', 'li.vehicle',
        ]
        
        vehicle_cards = []
        for selector in selectors:
            cards = html.select(selector)
            if len(cards) >= 2:
                vehicle_cards = cards
                logger.debug(f"{self.name}: Found {len(cards)} vehicles using selector: {selector}")
                break
        
        # Extract summaries from cards using keywords and regex
        for card in vehicle_cards:
            try:
                link = card.find('a', href=True) if card.name != 'a' else card
                if not link:
                    continue
                
                href = link.get('href', '')
                if not href:
                    continue
                
                detail_url = urljoin(self.base_url, href)
                
                # Skip invalid URLs
                if not detail_url.startswith(('http://', 'https://')):
                    continue
                
                skip_patterns = ['/contact', '/about', '/financing', '/service', '/directions']
                if any(pattern in detail_url.lower() for pattern in skip_patterns):
                    continue
                
                # Extract title
                title = ""
                title_elem = (card.find(['h1', 'h2', 'h3', 'h4']) or 
                             card.find(class_=lambda x: x and 'title' in str(x).lower()) or
                             card.find(class_=lambda x: x and 'name' in str(x).lower()))
                if title_elem:
                    title = title_elem.get_text(strip=True)
                elif link:
                    title = link.get_text(strip=True)
                
                # Extract price using keywords and regex
                price = None
                price_elems = self._find_field_by_keywords(card, "price")
                if price_elems:
                    price_text = price_elems[0].get_text(strip=True)
                    price_str = first_group(PRICE_REGEX, price_text)
                    if price_str:
                        price = parse_price_to_int(price_str)
                    else:
                        price = self._extract_price(price_text)
                
                if detail_url and title:
                    summaries.append(VehicleSummary(detail_url, title, price))
            
            except Exception as e:
                logger.debug(f"{self.name}: Error parsing vehicle card: {e}")
                continue
        
        logger.info(f"{self.name}: Extracted {len(summaries)} vehicle summaries from listing page")
        return summaries
    
    def parse_detail_page(self, html: BeautifulSoup, detail_url: str) -> Optional[CarListing]:
        """
        Parse detail page using keywords and regex patterns.
        Same extraction logic as GenericDealershipScraper - uses all the regex
        patterns and keyword-based extraction methods.
        """
        try:
            page_text = html.get_text()
            
            # VIN - try regex first, then keywords
            vin = first_group(VIN_REGEX, page_text)
            if not vin:
                vin = self._extract_vin_from_page(html)
            
            # Stock - try regex first, then keywords
            stock = first_group(STOCK_REGEX, page_text)
            if not stock:
                stock = self._extract_stock_from_page(html)
            
            # Mileage - try regex first, then keywords
            mileage_str = first_group(MILEAGE_REGEX, page_text)
            if mileage_str:
                mileage = parse_price_to_int(mileage_str)
                units = "mi"
            else:
                mileage, units = self._extract_mileage_from_page(html)
            
            # Condition - try regex first, then keywords
            condition_raw = first_group(CONDITION_REGEX, page_text)
            if condition_raw:
                condition = self._normalize_new_used(condition_raw)
            else:
                condition = self._extract_condition_from_page(html)
            
            # Availability - try regex first, then keywords
            availability_raw = first_group(AVAILABILITY_REGEX, page_text)
            status = None
            if availability_raw:
                text_lower = availability_raw.lower()
                if 'transit' in text_lower or 'way' in text_lower:
                    status = "in_transit"
                elif 'sold' in text_lower:
                    status = "sold"
                elif 'reserved' in text_lower:
                    status = "reserved"
                elif 'stock' in text_lower or 'available' in text_lower:
                    status = "available"
            if not status:
                status = self._extract_availability_from_page(html)
            
            # Use helper methods (which use keywords and regex internally)
            prices = self._extract_price_from_page(html)
            fuel_type = self._extract_fuel_type_from_page(html)
            drivetrain = self._extract_drivetrain_from_page(html)
            
            # Transmission - try regex first, then keywords
            transmission = first_group(TRANSMISSION_REGEX, page_text)
            if not transmission:
                transmission = self._extract_transmission_from_page(html)
            if transmission:
                transmission = transmission.strip()
            
            # Body style - try regex first, then keywords
            body_style = first_group(BODY_STYLE_LABEL_REGEX, page_text)
            if not body_style:
                body_style = first_group(BODY_STYLE_VALUE_REGEX, page_text)
            if not body_style:
                body_style = self._extract_body_style_from_page(html)
            if body_style:
                body_style = body_style.strip()
            
            # Colors - try regex first, then keywords
            exterior = first_group(EXTERIOR_COLOR_REGEX, page_text)
            interior = first_group(INTERIOR_COLOR_REGEX, page_text)
            if not exterior or not interior:
                ext_int = self._extract_colors_from_page(html)
                if not exterior:
                    exterior = ext_int[0]
                if not interior:
                    interior = ext_int[1]
            
            # Extract title and parse year/make/model
            title_elem = html.find('h1') or html.find('title')
            title = title_elem.get_text(strip=True) if title_elem else ""
            title_parts = self._parse_vehicle_title(title)
            
            # Extract images
            images = []
            img_tags = html.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    full_url = urljoin(detail_url, src)
                    if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        if 'vehicle' in full_url.lower() or 'inventory' in full_url.lower():
                            images.append(full_url)
            
            # Determine year, make, model
            year = title_parts.get('year') or datetime.now().year
            make = title_parts.get('make') or "Unknown"
            model = title_parts.get('model') or "Unknown"
            
            # Create CarListing using all extracted data
            return CarListing(
                dealer_name=self.dealership_info.name,
                dealer_website=self.dealership_info.website,
                vehicle_url=detail_url,
                year=year,
                make=make,
                model=model,
                trim=title_parts.get('trim'),
                new_used=condition or "new",
                fuel_type=fuel_type,
                drivetrain=drivetrain,
                transmission=transmission,
                body_style=body_style,
                msrp=prices.get('msrp'),
                sale_price=prices.get('sale_price'),
                total_price=prices.get('total_price'),
                vin=vin,
                stock_number=stock,
                mileage=mileage,
                mileage_units=units,
                in_stock_status=status,
                exterior_color=exterior,
                interior_color=interior,
                dealer_location_city=self.city.split('(')[0].strip() if '(' in self.city else self.city,
                dealer_location_state=self.state,
                images=images[:10],
            )
        
        except Exception as e:
            logger.warning(f"{self.name}: Error parsing detail page {detail_url}: {e}")
            return None

