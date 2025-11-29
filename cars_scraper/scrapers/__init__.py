"""
Site-specific scrapers for dealerships.
Import scrapers here to register them.
"""

# Import the generic scraper which auto-registers all dealerships from CSV
from .generic_scraper import (
    GenericDealershipScraper,
    MultiDealershipScraper,
    register_all_dealership_scrapers
)

# This will automatically register scrapers for all dealerships in dealerships.csv

