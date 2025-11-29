# Electric Car Scraper CLI

A Python command-line tool to scrape dealership websites for new electric cars under $60,000 and output the results in JSON format.

## Features

- **Comprehensive data model**: Captures all vehicle details including VIN, stock number, trim, fuel type, colors, location, status, and more
- **Robots.txt compliance**: Automatically checks and respects robots.txt rules before scraping
- **Structured data parsing**: Extracts JSON-LD structured data when available for accurate information
- **Multi-site support**: Scrape multiple dealership sites with a unified interface
- **Advanced filtering**: Filter by electric vehicles, new/used status, price, and mileage
- **Export to JSON**: Export results with full metadata and timestamps
- **Progress indicators and summary statistics**: Real-time feedback during scraping
- **Automatic request throttling**: Random delays between 1-2 seconds to be respectful to servers
- **Caching support**: Automatically caches responses for 1 hour to reduce server load and speed up repeated runs
- **Comprehensive logging**: Configurable logging levels with optional file output

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. The package can be used directly or installed in development mode:
```bash
pip install -e .
```

## Usage

### Basic Usage

Scrape all registered dealership sites:
```bash
python -m cars_scraper.cli --all-sites
```

Scrape specific sites:
```bash
python -m cars_scraper.cli --site dealer1 --site dealer2
```

### Command-Line Options

- `--site SITE`: Scrape a specific dealership site (can be used multiple times)
- `--all-sites`: Scrape all available dealership sites
- `--output PATH`: Output file path (default: `cars.csv`). Format auto-detected from extension (.json or .csv)
- `--format FORMAT`: Output format: `json`, `csv`, or `auto` (detect from extension). Default: `auto`
- `--config PATH`: Path to configuration file (JSON). CLI arguments override config file settings
- `--create-config PATH`: Create a default configuration file at the specified path and exit
- `--max-price AMOUNT`: Maximum price threshold in dollars (default: 60000)
- `--max-mileage MILES`: Maximum mileage for a car to be considered new (default: 100)
- `--include-used`: Include used cars (default: only new cars)
- `--include-non-electric`: Include non-electric cars (default: only electric)
- `--log-level LEVEL`: Set logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `--log-file PATH`: Optional file path to write logs to

### Examples

Scrape all sites with custom price limit:
```bash
python -m cars_scraper.cli --all-sites --max-price 50000 --output cheap_evs.json
```

Scrape and output to CSV:
```bash
python -m cars_scraper.cli --all-sites --output results.csv
```

Scrape specific sites and include used cars:
```bash
python -m cars_scraper.cli --site dealer1 --site dealer2 --include-used
```

Force CSV format regardless of file extension:
```bash
python -m cars_scraper.cli --all-sites --output data.txt --format csv
```

### Using Configuration Files

The scraper automatically looks for `scraper_config.json` in the current directory. If it exists, it will be used as the default configuration.

Create a configuration file to save your filtering preferences:

```bash
# Create the default config file (scraper_config.json)
python -m cars_scraper.cli --create-config scraper_config.json

# Or create a custom named config file
python -m cars_scraper.cli --create-config my_config.json
```

**Note**: If `scraper_config.json` exists in the current directory, it will be automatically loaded. You can override this by using `--config` to specify a different file.

Edit the config file to customize your filters:

```json
{
  "max_price": 50000,
  "max_mileage": 200,
  "new_only": true,
  "electric_only": true,
  "min_price": 30000,
  "makes": ["Tesla", "Hyundai", "Kia"],
  "exclude_makes": [],
  "states": ["OR"],
  "cities": ["Portland", "Beaverton"],
  "exclude_status": ["sold"],
  "output_path": "my_cars.csv",
  "output_format": "csv",
  "all_sites": true
}
```

Then use the config file:

```bash
# Use config file (CLI args override config settings)
python -m cars_scraper.cli --config my_config.json

# Override specific settings from config
python -m cars_scraper.cli --config my_config.json --max-price 55000
```

#### Configuration Options

**Filtering:**
- `max_price`: Maximum price (default: 60000)
- `min_price`: Minimum price (optional)
- `max_mileage`: Maximum mileage for "new" cars (default: 200)
- `new_only`: Only new cars (default: true)
- `electric_only`: Only electric vehicles (default: true)
- `fuel_types`: Specific fuel types to include (null = use electric_only setting)
- `min_year`: Minimum model year (optional)
- `max_year`: Maximum model year (optional)

**Make/Model Filters:**
- `makes`: List of allowed makes (null = all makes)
- `models`: List of allowed models (null = all models)
- `exclude_makes`: List of makes to exclude
- `exclude_models`: List of models to exclude

**Drivetrain Filters:**
- `drivetrains`: List of allowed drivetrains (null = all drivetrains). Examples: `["AWD", "FWD", "RWD", "4WD"]`
- `exclude_drivetrains`: List of drivetrains to exclude. Examples: `["FWD"]` to exclude front-wheel drive

**Dealer/Location Filters:**
- `dealers`: List of dealer names to include (null = all dealers)
- `exclude_dealers`: List of dealer names to exclude
- `cities`: List of cities to include (null = all cities)
- `states`: List of states to include (null = all states)

**Status Filters:**
- `availability_status`: List of allowed statuses (null = all except excluded)
- `exclude_status`: List of statuses to exclude (default: ["sold"])

**Output:**
- `output_path`: Output file path (default: "cars.csv")
- `output_format`: "json", "csv", or "auto" (default: "auto")

**Scraping:**
- `sites`: List of specific sites to scrape (null = use all_sites)
- `all_sites`: Scrape all available sites (default: true)

**Logging:**
- `log_level`: "DEBUG", "INFO", "WARNING", "ERROR" (default: "INFO")
- `log_file`: Optional log file path

## Output Format

The tool outputs a JSON file with comprehensive vehicle information:

```json
{
  "metadata": {
    "timestamp": "2024-01-15T10:30:00",
    "total_listings": 25,
    "source": "electric-car-scraper-cli"
  },
  "cars": [
    {
      "dealer_name": "Example Dealership",
      "dealer_website": "https://example.com",
      "vehicle_url": "https://example.com/car/123",
      "year": 2024,
      "make": "Tesla",
      "model": "Model 3",
      "trim": "Long Range",
      "new_used": "new",
      "fuel_type": "electric",
      "drivetrain": "AWD",
      "transmission": "Automatic",
      "body_style": "Sedan",
      "msrp": 42990.0,
      "sale_price": 38990.0,
      "total_price": 38990.0,
      "currency": "USD",
      "price_note": null,
      "vin": "5YJ3E1EA1KF123456",
      "stock_number": "ST12345",
      "mileage": 50,
      "mileage_units": "mi",
      "in_stock_status": "available",
      "exterior_color": "Pearl White",
      "interior_color": "Black",
      "dealer_location_city": "San Francisco",
      "dealer_location_state": "CA",
      "images": ["https://example.com/image1.jpg"],
      "description": "2024 Tesla Model 3 Long Range...",
      "features": ["Autopilot", "Premium Interior"],
      "scraped_at": "2024-01-15T10:30:00",
      "price": 38990.0,
      "is_electric": true,
      "url": "https://example.com/car/123",
      "dealership": "Example Dealership"
    }
  ]
}
```

### CSV Format

The tool can also output to CSV format, which is useful for spreadsheet applications and data analysis:

```bash
python -m cars_scraper.cli --all-sites --output cars.csv
```

The CSV includes all the same fields as JSON, with the following columns:
- `dealer_name`, `dealer_website`, `vehicle_url`
- `year`, `make`, `model`, `trim`
- `new_used`, `fuel_type`, `drivetrain`, `transmission`, `body_style`
- `msrp`, `sale_price`, `total_price`, `currency`, `price_note`
- `vin`, `stock_number`
- `mileage`, `mileage_units`, `in_stock_status`
- `exterior_color`, `interior_color`
- `dealer_location_city`, `dealer_location_state`
- `description`, `features` (semicolon-separated), `images` (semicolon-separated)
- `scraped_at`

**Note**: List fields (`features`, `images`) are joined with semicolons (`;`) in CSV format for compatibility with spreadsheet applications.

### CSV Example

Here's what a sample CSV output looks like:

```csv
dealer_name,dealer_website,vehicle_url,year,make,model,trim,new_used,fuel_type,drivetrain,transmission,body_style,msrp,sale_price,total_price,currency,price_note,vin,stock_number,mileage,mileage_units,in_stock_status,exterior_color,interior_color,dealer_location_city,dealer_location_state,description,features,images,scraped_at
Beaverton Kia,https://www.beavertonkia.com/,https://www.beavertonkia.com/inventory/ev6-12345,2024,Kia,EV6,GT-Line AWD,new,electric,AWD,Automatic,SUV,52490.0,48990.0,48990.0,USD,,5XYPG4C59MG123456,ST12345,12,mi,available,Glacier White,Black,Beaverton,OR,2024 Kia EV6 GT-Line AWD,Wireless Charging; Panoramic Sunroof; Heated Seats,https://www.beavertonkia.com/images/ev6-1.jpg; https://www.beavertonkia.com/images/ev6-2.jpg,2024-01-15T10:30:00
Beaverton Hyundai,https://www.beavertonhyundai.com/,https://www.beavertonhyundai.com/inventory/ioniq5-67890,2024,Hyundai,IONIQ 5,SEL,new,electric,AWD,Automatic,SUV,49950.0,46990.0,46990.0,USD,,KM8J3CA15PU678901,ST67890,5,mi,available,Cyber Gray,Black,Beaverton,OR,2024 Hyundai IONIQ 5 SEL,Ultra-Fast Charging; Digital Key; Premium Sound System,https://www.beavertonhyundai.com/images/ioniq5-1.jpg,2024-01-15T10:30:00
```

The CSV includes **30 columns** with all vehicle information. When opened in Excel, Google Sheets, or other spreadsheet applications, each column will be properly separated and you can easily:
- Sort by price, year, make, etc.
- Filter by dealer, city, state, drivetrain, etc.
- Analyze data using formulas and pivot tables
- Export to other formats if needed

## Adding New Dealership Scrapers

**Important**: Before you can scrape, you need to create and register scrapers for the dealership sites you want to scrape.

### Quick Start

1. Create a scraper file in `cars_scraper/scrapers/` (see example below)
2. Import and register it in `cars_scraper/scrapers/__init__.py`
3. The scraper will be automatically available when you run the CLI

### Example Scraper

To add a new dealership scraper, create a class that inherits from `DealershipScraper` and implement the required methods:

### Step 1: Check robots.txt and Terms of Service

Before implementing a scraper:
1. Check the site's robots.txt: `https://example.com/robots.txt`
2. Review the Terms of Service to ensure scraping is allowed
3. The scraper will automatically check robots.txt, but manual verification is recommended

### Step 2: Implement the Scraper

```python
from cars_scraper.scraper import DealershipScraper, VehicleSummary
from cars_scraper.models import CarListing
from cars_scraper.cli import register_scraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Optional

class MyDealershipScraper(DealershipScraper):
    def __init__(self):
        super().__init__(
            name="My Dealership",
            base_url="https://example.com",
            min_delay=1.0,  # Minimum delay between requests (seconds)
            max_delay=2.0,  # Maximum delay between requests (seconds)
            use_cache=True,  # Enable caching (default: True)
            check_robots=True  # Check robots.txt (default: True)
        )
    
    def get_listing_urls(self) -> List[str]:
        """Return list of all listing page URLs (handles pagination)."""
        # Example: return [f"{self.base_url}/inventory/new"]
        # Or handle pagination:
        urls = []
        for page in range(1, 10):  # Adjust based on site
            urls.append(f"{self.base_url}/inventory?page={page}")
        return urls
    
    def parse_list_page(self, html: BeautifulSoup, page_url: str) -> List[VehicleSummary]:
        """Parse listing page to extract vehicle summaries."""
        summaries = []
        # Find vehicle cards
        cards = html.select('.vehicle-card')  # Adjust selector for site
        
        for card in cards:
            # Extract detail URL
            link = card.find('a', href=True)
            if link:
                detail_url = urljoin(self.base_url, link['href'])
                title = link.get_text(strip=True)
                summaries.append(VehicleSummary(detail_url, title))
        
        return summaries
    
    def parse_detail_page(self, html: BeautifulSoup, detail_url: str) -> Optional[CarListing]:
        """Parse detail page to extract full vehicle information."""
        # Try JSON-LD first (most reliable)
        json_ld = self._extract_json_ld(html)
        
        # Extract data from JSON-LD or HTML
        # ... parsing logic ...
        
        return CarListing(
            dealer_name=self.name,
            dealer_website=self.base_url,
            vehicle_url=detail_url,
            year=2024,
            make="Tesla",
            model="Model 3",
            # ... other fields ...
        )

# Register the scraper
register_scraper("my_dealership", MyDealershipScraper)
```

### Step 3: Best Practices

1. **Use JSON-LD when available**: Check for structured data first using `_extract_json_ld()`
2. **Handle edge cases**: "Call for price", missing data, different page layouts
3. **Test thoroughly**: Verify VINs, prices, and other critical fields
4. **Respect rate limits**: The base class handles this, but be mindful of site-specific limits
5. **Log errors**: Use the logging system for debugging

### Architecture

The scraper uses a three-phase approach:
1. **Listing pages**: `get_listing_urls()` → `parse_list_page()` → `VehicleSummary` objects
2. **Detail pages**: Fetch each detail URL → `parse_detail_page()` → `CarListing` objects
3. **Filtering & output**: Apply filters and save to JSON

This architecture makes it easy to:
- Handle pagination
- Parse different page types separately
- Cache listing pages while refreshing detail pages
- Test individual components

## Project Structure

```
cars_scraper/
├── __init__.py          # Package initialization
├── cli.py               # CLI entry point
├── scraper.py           # Base scraper class with enhanced architecture
├── models.py            # Comprehensive data models
├── filters.py           # Filtering logic
├── utils.py             # JSON output utilities
├── robots.py            # Robots.txt checking
└── logging_config.py    # Logging configuration
requirements.txt         # Dependencies
README.md                # This file
```

## Requirements

- Python 3.8+
- requests
- beautifulsoup4
- lxml
- requests-cache (for automatic response caching)

## License

This project is provided as-is for educational and personal use.

