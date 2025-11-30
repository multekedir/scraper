"""
Generic scraper that can handle multiple dealership sites.
Uses flexible parsing to extract vehicle data from various site structures.
"""

from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
from ..scraper import DealershipScraper, VehicleSummary
from ..models import CarListing
from ..cli import register_scraper
from ..dealership_loader import load_dealerships_from_csv, DealershipInfo
from ..field_keywords import FIELD_KEYWORDS, get_keywords, contains_keyword
from ..checkpoint import CheckpointManager
from ..car_regexes import (
    first_group, VIN_REGEX, PRICE_REGEX, MILEAGE_REGEX, STOCK_REGEX,
    CONDITION_REGEX, AVAILABILITY_REGEX, BODY_STYLE_LABEL_REGEX, BODY_STYLE_VALUE_REGEX,
    EXTERIOR_COLOR_REGEX, INTERIOR_COLOR_REGEX, TRANSMISSION_REGEX, ENGINE_REGEX,
    FUEL_TYPE_LABEL_REGEX, FUEL_TYPE_VALUE_REGEX, DRIVETRAIN_REGEX, DRIVETRAIN_LABEL_REGEX,
    normalize_drivetrain, parse_price_to_int, is_electric as regex_is_electric
)
from datetime import datetime
import logging

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Create a dummy tqdm that just returns the iterable
    def tqdm(iterable=None, *args, **kwargs):
        if iterable is None:
            return lambda x: x
        return iterable

logger = logging.getLogger(__name__)


class GenericDealershipScraper(DealershipScraper):
    """
    Generic scraper that attempts to extract vehicle data from any dealership site.
    Uses flexible selectors and patterns to work with different site structures.
    """
    
    def __init__(self, dealership_info: DealershipInfo):
        """
        Initialize scraper for a specific dealership.
        
        Args:
            dealership_info: DealershipInfo object with name, website, and city
        """
        super().__init__(
            name=dealership_info.name,
            base_url=dealership_info.website,
            min_delay=3.0,  # Slower = less bot-like
            max_delay=7.0,  # Random delays 3-7 seconds
            use_cache=True,
            check_robots=False  # Site blocks robots.txt too
        )
        self.dealership_info = dealership_info
        self.city = dealership_info.city
        # Extract state from city if available (e.g., "Portland (Beaverton area)" -> "OR")
        self.state = self._extract_state_from_city(dealership_info.city)
    
    def _extract_state_from_city(self, city: str) -> Optional[str]:
        """Extract state abbreviation from city string if present."""
        # Most cities in the CSV are in Oregon, but check for state indicators
        if 'OR' in city.upper() or 'Oregon' in city:
            return "OR"
        elif 'WA' in city.upper() or 'Washington' in city:
            return "WA"
        # Default to OR for Portland area
        return "OR"
    
    def get_listing_urls(self) -> List[str]:
        """
        Get listing page URLs by trying common inventory page patterns.
        
        Returns:
            List of listing page URLs
        """
        urls = []
        base = self.base_url.rstrip('/')
        
        # Common inventory page patterns
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
                html = self._get_page(pattern, check_robots=False)
                # Check if this looks like an inventory page
                if self._is_inventory_page(html):
                    urls.append(pattern)
                    logger.debug(f"{self.name}: Found inventory page at {pattern}")
                    break
            except Exception as e:
                logger.debug(f"{self.name}: {pattern} not accessible: {e}")
                continue
        
        # If no inventory page found, try the base URL
        if not urls:
            try:
                html = self._get_page(base, check_robots=False)
                if self._is_inventory_page(html):
                    urls.append(base)
            except:
                pass
        
        # If still nothing, return the most likely URL
        if not urls:
            urls = [f"{base}/inventory"]
            logger.warning(f"{self.name}: Using default inventory URL, may not work")
        
        return urls
    
    def _is_inventory_page(self, html: BeautifulSoup) -> bool:
        """Check if a page looks like an inventory/listing page."""
        text = html.get_text().lower()
        
        # Use field keywords to check for inventory indicators
        inventory_keywords = get_keywords("name") + ["inventory", "vehicles", "browse", "available"]
        
        # Check for multiple vehicle cards/items using keywords
        vehicle_indicators = html.find_all(['div', 'article', 'li'], 
                                          class_=lambda x: x and any(
                                              kw in str(x).lower() 
                                              for kw in ['vehicle', 'inventory', 'car', 'listing', 'item']
                                          ))
        
        # Also check for price elements (inventory pages usually have prices)
        price_elements = self._find_field_by_keywords(html, "price")
        
        return (any(kw in text for kw in inventory_keywords) or 
                len(vehicle_indicators) >= 3 or
                len(price_elements) >= 2)
    
    def parse_list_page(self, html: BeautifulSoup, page_url: str) -> List[VehicleSummary]:
        """
        Parse listing page using flexible selectors.
        
        Args:
            html: Parsed HTML
            page_url: URL of the page
        
        Returns:
            List of VehicleSummary objects
        """
        summaries = []
        
        # Try multiple selector patterns to find vehicle cards
        # Use keywords to build dynamic selectors
        vehicle_keywords = ['vehicle', 'inventory', 'car', 'listing', 'item', 'stock']
        selectors = [
            # Common patterns
            '.vehicle-card',
            '.inventory-item',
            '.vehicle-listing',
            '.car-listing',
            '[data-vehicle-id]',
            '[data-vin]',
            '.vehicle',
            '.inventory-vehicle',
            # More generic
            'article.vehicle',
            'div.vehicle',
            'li.vehicle',
            # Table rows (some sites use tables)
            'tr.vehicle',
            'tr[data-vin]',
        ]
        
        # Add dynamic selectors based on keywords
        for keyword in vehicle_keywords:
            selectors.extend([
                f'.{keyword}-card',
                f'.{keyword}-item',
                f'.{keyword}-listing',
                f'[class*="{keyword}"]',
            ])
        
        vehicle_cards = []
        for selector in selectors:
            cards = html.select(selector)
            if len(cards) >= 2:  # Need at least 2 to be confident
                vehicle_cards = cards
                logger.debug(f"{self.name}: Found {len(cards)} vehicles using selector: {selector}")
                break
        
        # If no cards found with specific selectors, try finding links with vehicle-like patterns
        if not vehicle_cards:
            # Look for links that might be vehicle detail pages
            all_links = html.find_all('a', href=True)
            vehicle_links = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text().lower()
                # Check if link looks like a vehicle detail page
                if any(pattern in href.lower() for pattern in ['/vehicle/', '/inventory/', '/car/', '/detail/']):
                    if any(kw in text for kw in ['new', 'used', '2024', '2025']) or re.search(r'\d{4}', text):
                        vehicle_links.append(link)
            
            if vehicle_links:
                vehicle_cards = vehicle_links[:50]  # Limit to reasonable number
                logger.debug(f"{self.name}: Found {len(vehicle_links)} potential vehicle links")
        
        # Extract summaries from cards
        for card in vehicle_cards:
            try:
                # Find detail URL
                link = card.find('a', href=True) if card.name != 'a' else card
                if not link:
                    continue
                
                href = link.get('href', '')
                if not href:
                    continue
                
                detail_url = urljoin(self.base_url, href)
                
                # Extract title
                title = ""
                title_elem = (card.find(['h1', 'h2', 'h3', 'h4']) or 
                             card.find(class_=lambda x: x and 'title' in str(x).lower()) or
                             card.find(class_=lambda x: x and 'name' in str(x).lower()))
                if title_elem:
                    title = title_elem.get_text(strip=True)
                elif link:
                    title = link.get_text(strip=True)
                
                # Extract price if available - use keywords and regex
                price = None
                # Try finding price using keywords
                price_elems = self._find_field_by_keywords(card, "price")
                if price_elems:
                    price_text = price_elems[0].get_text(strip=True)
                    # Use regex to extract price
                    price_str = first_group(PRICE_REGEX, price_text)
                    if price_str:
                        price = parse_price_to_int(price_str)
                    else:
                        price = self._extract_price(price_text)
                else:
                    # Fallback to class-based search
                    price_elem = card.find(class_=lambda x: x and 'price' in str(x).lower())
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
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
        Parse detail page using all available extraction methods.
        
        Args:
            html: Parsed HTML
            detail_url: URL of detail page
        
        Returns:
            CarListing or None if parsing fails
        """
        try:
            page_text = html.get_text()
            
            # Use regex patterns first (most precise), then fall back to helper methods
            # VIN - try regex first
            vin = first_group(VIN_REGEX, page_text)
            if vin:
                logger.debug(f"{self.name}: Extracted VIN using regex: {vin}")
            else:
                vin = self._extract_vin_from_page(html)
                if vin:
                    logger.debug(f"{self.name}: Extracted VIN using keywords: {vin}")
            
            # Stock number - try regex first
            stock = first_group(STOCK_REGEX, page_text)
            if stock:
                logger.debug(f"{self.name}: Extracted stock using regex: {stock}")
            else:
                stock = self._extract_stock_from_page(html)
                if stock:
                    logger.debug(f"{self.name}: Extracted stock using keywords: {stock}")
            
            # Mileage - try regex first
            mileage_str = first_group(MILEAGE_REGEX, page_text)
            if mileage_str:
                mileage = parse_price_to_int(mileage_str)
                units = "mi"
                logger.debug(f"{self.name}: Extracted mileage using regex: {mileage} {units}")
            else:
                mileage, units = self._extract_mileage_from_page(html)
                if mileage:
                    logger.debug(f"{self.name}: Extracted mileage using keywords: {mileage} {units}")
            
            # Condition - try regex first
            condition_raw = first_group(CONDITION_REGEX, page_text)
            if condition_raw:
                condition = self._normalize_new_used(condition_raw)
            else:
                condition = self._extract_condition_from_page(html)
            
            # Availability - try regex first
            availability_raw = first_group(AVAILABILITY_REGEX, page_text)
            status = None
            if availability_raw:
                text_lower = availability_raw.lower()
                if 'transit' in text_lower or 'way' in text_lower or 'arriving' in text_lower:
                    status = "in_transit"
                elif 'sold' in text_lower:
                    status = "sold"
                elif 'reserved' in text_lower:
                    status = "reserved"
                elif 'stock' in text_lower or 'available' in text_lower:
                    status = "available"
            if not status:
                status = self._extract_availability_from_page(html)
            
            # Use helper methods (which also use keywords and regex internally)
            prices = self._extract_price_from_page(html)
            fuel_type = self._extract_fuel_type_from_page(html)
            drivetrain = self._extract_drivetrain_from_page(html)
            
            # Transmission - try regex first
            transmission = first_group(TRANSMISSION_REGEX, page_text)
            if not transmission:
                transmission = self._extract_transmission_from_page(html)
            if transmission:
                transmission = transmission.strip()
            
            # Body style - try regex first
            body_style = first_group(BODY_STYLE_LABEL_REGEX, page_text)
            if not body_style:
                body_style = first_group(BODY_STYLE_VALUE_REGEX, page_text)
            if not body_style:
                body_style = self._extract_body_style_from_page(html)
            if body_style:
                body_style = body_style.strip()
            
            # Colors - try regex first
            exterior = first_group(EXTERIOR_COLOR_REGEX, page_text)
            interior = first_group(INTERIOR_COLOR_REGEX, page_text)
            if not exterior or not interior:
                ext_int = self._extract_colors_from_page(html)
                if not exterior:
                    exterior = ext_int[0]
                if not interior:
                    interior = ext_int[1]
            if exterior:
                exterior = exterior.strip()
            if interior:
                interior = interior.strip()
            
            # Parse title
            title_elem = html.find('h1') or html.find('title')
            title = title_elem.get_text(strip=True) if title_elem else ""
            title_parts = self._parse_vehicle_title(title)
            
            # Extract images
            images = []
            img_tags = html.find_all('img', src=True)
            for img in img_tags:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    full_url = urljoin(self.base_url, src)
                    if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        if 'vehicle' in full_url.lower() or 'inventory' in full_url.lower() or 'car' in full_url.lower():
                            images.append(full_url)
            
            # Extract description - use keywords to find description elements
            description = None
            desc_keywords = ['description', 'details', 'overview', 'about']
            for keyword in desc_keywords:
                desc_elems = html.find_all(['div', 'p', 'section'], 
                                          class_=lambda x: x and keyword in str(x).lower())
                if desc_elems:
                    description = desc_elems[0].get_text(strip=True)
                    if len(description) > 50:  # Only use if substantial
                        break
            
            # Extract features - use keywords to find feature sections
            features = []
            feature_keywords = ['feature', 'option', 'equipment', 'standard', 'included']
            for keyword in feature_keywords:
                feature_containers = html.find_all(['ul', 'div', 'dl'], 
                                                  class_=lambda x: x and keyword in str(x).lower())
                for container in feature_containers:
                    items = container.find_all('li') or container.find_all(['span', 'div', 'dt', 'dd'])
                    for item in items:
                        text = item.get_text(strip=True)
                        if text and len(text) > 2 and len(text) < 100:  # Reasonable feature length
                            features.append(text)
                if features:
                    break
            
            # Determine year, make, model from title or page
            year = title_parts.get('year')
            make = title_parts.get('make')
            model = title_parts.get('model')
            trim = title_parts.get('trim')
            
            # Fallback: try to extract from page content if title parsing failed
            # Use keywords to find make/model information
            if not make or not model:
                # Look for elements containing vehicle name keywords
                name_elements = self._find_field_by_keywords(html, "name")
                for elem in name_elements:
                    text = elem.get_text(strip=True)
                    parts = self._parse_vehicle_title(text)
                    if parts.get('make') and not make:
                        make = parts.get('make')
                    if parts.get('model') and not model:
                        model = parts.get('model')
                    if parts.get('year') and not year:
                        year = parts.get('year')
                
                # Also try regex pattern on full page text
                if not make or not model:
                    make_model_pattern = r'\b(Tesla|Hyundai|Kia|Ford|Chevrolet|Nissan|BMW|Mercedes|Audi|Toyota|Honda|Mazda|Subaru|Volvo|Polestar|Rivian|Lucid|Genesis|Cadillac|Lincoln|Jeep|Ram|GMC|Buick|Chrysler|Dodge|INFINITI|Acura|Lexus|Jaguar|Land Rover|MINI|Mitsubishi|Porsche)\s+([A-Z0-9\s]+?)(?:\s|$|,|\d)'
                    match = re.search(make_model_pattern, page_text, re.IGNORECASE)
                    if match:
                        if not make:
                            make = match.group(1)
                        if not model:
                            model = match.group(2).strip()
            
            # Final fallbacks
            if not year:
                year = datetime.now().year
            if not make:
                make = "Unknown"
            if not model:
                model = "Unknown"
            
            # Only create listing if we have minimum required data
            if make == "Unknown" and model == "Unknown":
                logger.warning(f"{self.name}: Could not extract make/model from {detail_url}")
                return None
            
            return CarListing(
                dealer_name=self.name,
                dealer_website=self.base_url,
                vehicle_url=detail_url,
                year=year,
                make=make,
                model=model,
                trim=trim,
                new_used=condition,
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
                images=images[:10],  # Limit to 10 images
                description=description,
                features=features[:20],  # Limit to 20 features
            )
        
        except Exception as e:
            logger.warning(f"{self.name}: Error parsing detail page {detail_url}: {e}")
            return None


class MultiDealershipScraper:
    """
    Scraper that handles multiple dealerships from CSV.
    Creates a GenericDealershipScraper for each dealership.
    """
    
    def __init__(self, csv_path: str = "dealerships.csv", checkpoint_file: Optional[str] = ".scraper_checkpoint.json", resume: bool = True):
        """
        Initialize multi-dealership scraper.
        
        Args:
            csv_path: Path to dealerships CSV file
            checkpoint_file: Path to checkpoint file for resuming
            resume: Whether to resume from checkpoint if available
        """
        self.csv_path = csv_path
        self.dealerships: List[DealershipInfo] = []
        self.checkpoint_file = checkpoint_file
        self.resume = resume
        self.checkpoint = CheckpointManager(checkpoint_file)
        self._load_dealerships()
        
        # Load checkpoint if resuming
        if self.resume:
            checkpoint_loaded = self.checkpoint.load()
            if checkpoint_loaded:
                logger.info(f"Resuming from checkpoint: {len(self.checkpoint.completed_dealerships)} dealerships already completed")
    
    def _load_dealerships(self):
        """Load dealerships from CSV."""
        try:
            self.dealerships = load_dealerships_from_csv(self.csv_path)
            logger.info(f"Loaded {len(self.dealerships)} dealerships from {self.csv_path}")
        except Exception as e:
            logger.error(f"Failed to load dealerships from {self.csv_path}: {e}")
            self.dealerships = []
    
    def scrape_all(self, output_writer=None) -> List[CarListing]:
        """
        Scrape all dealerships with checkpoint support and optional streaming output.
        
        Args:
            output_writer: Optional StreamingOutputWriter for incremental saves
        
        Returns:
            List of all CarListing objects from all dealerships
        """
        # Start with listings from checkpoint
        all_listings = self.checkpoint.get_listings()
        completed_dealerships = set(self.checkpoint.completed_dealerships)
        
        # Filter out already completed dealerships
        remaining_dealerships = [
            dealer for dealer in self.dealerships 
            if dealer.name not in completed_dealerships
        ]
        
        if not remaining_dealerships:
            logger.info("All dealerships already completed (from checkpoint)")
            return all_listings
        
        logger.info(f"Scraping {len(remaining_dealerships)} remaining dealerships "
                   f"(skipping {len(completed_dealerships)} already completed)")
        
        # Scrape remaining dealerships
        for dealer_info in tqdm(remaining_dealerships, desc="Dealerships", disable=not TQDM_AVAILABLE):
            try:
                scraper = GenericDealershipScraper(dealer_info)
                listings = scraper.scrape()
                all_listings.extend(listings)
                completed_dealerships.add(dealer_info.name)
                
                # Stream output incrementally if writer provided
                if output_writer and listings:
                    output_writer.append_cars(listings)
                    logger.debug(f"{dealer_info.name}: Streamed {len(listings)} vehicles to output")
                
                # Save checkpoint after each dealership
                self.checkpoint.save(completed_dealerships, all_listings)
                
                logger.info(f"{dealer_info.name}: Scraped {len(listings)} vehicles "
                          f"(total: {len(all_listings)} listings)")
            except Exception as e:
                logger.error(f"{dealer_info.name}: Scraping failed: {e}", exc_info=True)
                # Still save checkpoint even on failure, so we don't retry failed ones
                completed_dealerships.add(dealer_info.name)
                self.checkpoint.save(completed_dealerships, all_listings)
                continue
        
        # Final checkpoint save
        self.checkpoint.save(completed_dealerships, all_listings)
        logger.info(f"Scraping complete: {len(all_listings)} total listings from {len(completed_dealerships)} dealerships")
        
        return all_listings


# Register individual scrapers for each dealership in the CSV
def register_all_dealership_scrapers(csv_path: str = "dealerships.csv"):
    """
    Register a scraper for each dealership in the CSV.
    Each dealership gets registered with a sanitized name.
    """
    try:
        dealerships = load_dealerships_from_csv(csv_path)
        
        for dealer_info in dealerships:
            # Create a scraper class for this specific dealership
            dealer_name_safe = dealer_info.name.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('/', '_')
            dealer_name_safe = re.sub(r'[^a-z0-9_]', '', dealer_name_safe)
            
            # Create a scraper class for this specific dealership
            # Use a factory function to properly capture dealer_info
            def create_scraper_class(dealer_info_captured):
                class SpecificDealershipScraper(GenericDealershipScraper):
                    def __init__(self):
                        super().__init__(dealer_info_captured)
                return SpecificDealershipScraper
            
            scraper_class = create_scraper_class(dealer_info)
            
            register_scraper(dealer_name_safe, scraper_class)
            logger.debug(f"Registered scraper: {dealer_name_safe} for {dealer_info.name}")
        
        logger.info(f"Registered {len(dealerships)} dealership scrapers")
        return len(dealerships)
    
    except Exception as e:
        logger.error(f"Failed to register dealership scrapers: {e}", exc_info=True)
        return 0


# Auto-register all dealerships when this module is imported
import os
from pathlib import Path

def _find_csv_path():
    """Find the dealerships.csv file in common locations."""
    # Try current directory
    if Path("dealerships.csv").exists():
        return "dealerships.csv"
    # Try parent directory (project root)
    if Path("../dealerships.csv").exists():
        return "../dealerships.csv"
    # Try absolute path from this file's location
    script_dir = Path(__file__).parent.parent.parent
    csv_path = script_dir / "dealerships.csv"
    if csv_path.exists():
        return str(csv_path)
    return "dealerships.csv"  # Default, will fail gracefully if not found

try:
    csv_path = _find_csv_path()
    register_all_dealership_scrapers(csv_path)
except Exception as e:
    logger.warning(f"Could not auto-register dealership scrapers: {e}")
    logger.debug(f"Error details: {e}", exc_info=True)

