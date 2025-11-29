"""
Example scraper implementation.
This is a template showing how to create a site-specific scraper.
"""

from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from ..scraper import DealershipScraper, VehicleSummary
from ..models import CarListing
from ..cli import register_scraper
from datetime import datetime


class ExampleDealershipScraper(DealershipScraper):
    """
    Example scraper implementation.
    
    This is a template - replace with actual selectors and logic
    for your specific dealership site.
    """
    
    def __init__(self):
        super().__init__(
            name="Example Dealership",
            base_url="https://example.com",
            min_delay=1.0,
            max_delay=2.0,
            use_cache=True,
            check_robots=True
        )
    
    def get_listing_urls(self) -> List[str]:
        """
        Get all listing page URLs.
        
        Returns:
            List of URLs to scrape for vehicle listings
        """
        # Example: single inventory page
        # For pagination, you might do:
        # urls = []
        # for page in range(1, 10):
        #     urls.append(f"{self.base_url}/inventory?page={page}")
        # return urls
        
        return [f"{self.base_url}/inventory"]
    
    def parse_list_page(self, html: BeautifulSoup, page_url: str) -> List[VehicleSummary]:
        """
        Parse a listing page to extract vehicle summaries.
        
        Args:
            html: Parsed HTML of the listing page
            page_url: URL of the listing page
        
        Returns:
            List of VehicleSummary objects
        """
        summaries = []
        
        # TODO: Replace with actual CSS selectors for your site
        # Example selectors (adjust for your site):
        vehicle_cards = html.select('.vehicle-card, .inventory-item, [data-vehicle-id]')
        
        for card in vehicle_cards:
            # Find the link to the detail page
            link = card.find('a', href=True)
            if not link:
                continue
            
            detail_url = urljoin(self.base_url, link['href'])
            
            # Extract title
            title_elem = card.find(['h2', 'h3', 'h4'], class_=lambda x: x and 'title' in x.lower())
            title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
            
            # Extract price if available on listing page
            price_elem = card.find(class_=lambda x: x and 'price' in str(x).lower())
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._extract_price(price_text)
            
            summaries.append(VehicleSummary(detail_url, title, price))
        
        return summaries
    
    def parse_detail_page(self, html: BeautifulSoup, detail_url: str) -> CarListing:
        """
        Parse a vehicle detail page to extract full vehicle information.
        
        Args:
            html: Parsed HTML of the detail page
            detail_url: URL of the detail page
        
        Returns:
            CarListing object
        """
        # Try JSON-LD first (most reliable)
        json_ld = self._extract_json_ld(html)
        
        # Extract data using helper methods
        prices = self._extract_price_from_page(html)
        vin = self._extract_vin_from_page(html)
        stock = self._extract_stock_from_page(html)
        mileage, units = self._extract_mileage_from_page(html)
        condition = self._extract_condition_from_page(html)
        fuel_type = self._extract_fuel_type_from_page(html)
        drivetrain = self._extract_drivetrain_from_page(html)
        transmission = self._extract_transmission_from_page(html)
        body_style = self._extract_body_style_from_page(html)
        exterior, interior = self._extract_colors_from_page(html)
        status = self._extract_availability_from_page(html)
        
        # Parse title for year/make/model
        title_elem = html.find('h1') or html.find('h2')
        title = title_elem.get_text(strip=True) if title_elem else ""
        title_parts = self._parse_vehicle_title(title)
        
        # Extract images
        images = []
        img_tags = html.find_all('img', src=True)
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and 'vehicle' in src.lower():
                images.append(urljoin(self.base_url, src))
        
        # Extract description
        desc_elem = html.find(['div', 'p'], class_=lambda x: x and 'description' in str(x).lower())
        description = desc_elem.get_text(strip=True) if desc_elem else None
        
        # Extract features
        features = []
        feature_elems = html.find_all(['li', 'span'], class_=lambda x: x and 'feature' in str(x).lower())
        for feat in feature_elems:
            features.append(feat.get_text(strip=True))
        
        return CarListing(
            dealer_name=self.name,
            dealer_website=self.base_url,
            vehicle_url=detail_url,
            year=title_parts.get('year') or datetime.now().year,
            make=title_parts.get('make') or "Unknown",
            model=title_parts.get('model') or "Unknown",
            trim=title_parts.get('trim'),
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
            images=images,
            description=description,
            features=features,
        )


# Register the scraper (uncomment when ready to use)
# register_scraper("example_dealership", ExampleDealershipScraper)

