# Field Keywords Usage Guide

The scraper framework includes a comprehensive set of field keywords to help identify and extract vehicle data from dealership pages.

## Overview

The `FIELD_KEYWORDS` dictionary contains common terms used on dealership websites for various vehicle attributes. These keywords are used by helper methods in the `DealershipScraper` base class to locate and extract data.

## Available Fields

### Name/Title
Keywords: "New", "Used", "Certified"
- Used to identify vehicle titles and headings
- Usually found in H1/H2 tags on detail pages

### Price
Keywords: "MSRP", "Internet Price", "Sale Price", "Our Price", "Dealer Price", "No Bull Price", "One Price", "E-Price", "Request ePrice", "$"
- Used to find pricing information
- Multiple price types supported (MSRP, sale price, total price)

### VIN
Keywords: "VIN", "Vin:", "Vehicle Identification Number"
- Used to locate vehicle identification numbers
- Automatically validates 17-character format

### Stock Number
Keywords: "Stock #", "Stock:", "Stock Number", "Stk #"
- Used to find dealer stock numbers

### Mileage
Keywords: "Mileage", "Odometer", "Miles", "mi."
- Used to extract mileage/odometer readings
- Handles both miles and kilometers

### Condition
Keywords: "Condition", "New", "Used", "Pre-Owned", "Certified Pre-Owned", "CPO"
- Used to determine if vehicle is new, used, or CPO
- Normalized to: "new", "used", "cpo"

### Fuel Type
Keywords: "Fuel Type", "Fuel", "Engine", "Hybrid", "Plug-In Hybrid", "PHEV", "Electric", "EV", "Battery Electric", "BEV"
- Used to identify electric/hybrid vehicles
- Normalized to standard fuel types

### Availability
Keywords: "In Stock", "Available", "In Transit", "On the Way", "Sold", "Reserved", "Order Yours"
- Used to determine vehicle availability status
- Normalized to: "available", "in_transit", "sold", "reserved"

### Body Style
Keywords: "Body Style", "Body:", "Sedan", "SUV", "Truck", "Hatchback", "Wagon"
- Used to identify vehicle body style

### Colors
Keywords: "Exterior Color", "Interior Color", "Ext. Color", "Int. Color", "Exterior:", "Interior:"
- Used to extract exterior and interior color information

## Usage in Scrapers

### Helper Methods Available

The `DealershipScraper` base class provides several helper methods that use these keywords:

```python
# Find elements containing keywords
elements = self._find_field_by_keywords(html, "price", tag="div", class_contains="price")

# Extract field value (finds label:value pairs)
vin = self._extract_field_value(html, "vin")
stock = self._extract_field_value(html, "stock_number")

# Extract prices (returns dict with msrp, sale_price, total_price)
prices = self._extract_price_from_page(html)

# Extract VIN (validates format)
vin = self._extract_vin_from_page(html)

# Extract stock number
stock = self._extract_stock_from_page(html)

# Extract mileage (returns tuple: (value, units))
mileage, units = self._extract_mileage_from_page(html)

# Extract condition (normalized)
condition = self._extract_condition_from_page(html)

# Extract fuel type (normalized)
fuel_type = self._extract_fuel_type_from_page(html)

# Extract availability status
status = self._extract_availability_from_page(html)

# Extract colors (returns tuple: (exterior, interior))
exterior, interior = self._extract_colors_from_page(html)
```

### Example Implementation

```python
from cars_scraper.scraper import DealershipScraper, VehicleSummary
from cars_scraper.models import CarListing
from bs4 import BeautifulSoup
from typing import List, Optional

class MyDealershipScraper(DealershipScraper):
    def parse_detail_page(self, html: BeautifulSoup, detail_url: str) -> Optional[CarListing]:
        # Use helper methods that leverage field keywords
        prices = self._extract_price_from_page(html)
        vin = self._extract_vin_from_page(html)
        stock = self._extract_stock_from_page(html)
        mileage, units = self._extract_mileage_from_page(html)
        condition = self._extract_condition_from_page(html)
        fuel_type = self._extract_fuel_type_from_page(html)
        status = self._extract_availability_from_page(html)
        exterior, interior = self._extract_colors_from_page(html)
        
        # Parse title for year/make/model
        title_elem = html.find('h1') or html.find('h2')
        title = title_elem.get_text(strip=True) if title_elem else ""
        title_parts = self._parse_vehicle_title(title)
        
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
        )
```

## Extending Keywords

To add more keywords, edit `cars_scraper/field_keywords.py`:

```python
FIELD_KEYWORDS = {
    "price": [
        # ... existing keywords ...
        "Your New Keyword",  # Add here
    ],
    # ... other fields ...
}
```

## Best Practices

1. **Use helper methods first**: The base class methods handle common patterns
2. **Fallback to manual parsing**: If keywords don't work, implement custom logic
3. **Combine with CSS selectors**: Use keywords to find elements, then use CSS to extract values
4. **Test with real pages**: Keywords are based on common patterns but may need adjustment per site
5. **Log when keywords fail**: Help identify sites that need custom handling

