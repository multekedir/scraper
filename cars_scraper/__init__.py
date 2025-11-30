"""
Electric Car Scraper CLI - A tool to scrape dealership sites for electric cars.
"""

__version__ = "0.2.0"

from .models import CarListing
from .filters import filter_cars
from .scraper import DealershipScraper, VehicleSummary
from .utils import save_to_json, load_from_json, save_to_csv, load_from_csv, save_to_file
from .robots import RobotsChecker
from .logging_config import setup_logging
from .config import ScraperConfig
from .field_keywords import FIELD_KEYWORDS, get_keywords, contains_keyword
from .validator import DataValidator, ValidationReport
from .checkpoint import CheckpointManager
from .utils import StreamingOutputWriter
from .deduplicate import deduplicate_listings, deduplicate_by_vin_only, deduplicate_by_url_only
from .selenium_driver import SeleniumDriver
from .selenium_scraper import SeleniumDealershipScraper
from .car_regexes import (
    first_group, VIN_REGEX, PRICE_REGEX, MILEAGE_REGEX, STOCK_REGEX,
    CONDITION_REGEX, AVAILABILITY_REGEX, normalize_drivetrain, parse_price_to_int,
    is_electric as regex_is_electric
)

__all__ = [
    "CarListing",
    "filter_cars",
    "DealershipScraper",
    "VehicleSummary",
    "save_to_json",
    "load_from_json",
    "save_to_csv",
    "load_from_csv",
    "save_to_file",
    "RobotsChecker",
    "setup_logging",
    "ScraperConfig",
    "FIELD_KEYWORDS",
    "get_keywords",
    "contains_keyword",
    "first_group",
    "VIN_REGEX",
    "PRICE_REGEX",
    "MILEAGE_REGEX",
    "STOCK_REGEX",
    "normalize_drivetrain",
    "parse_price_to_int",
    "regex_is_electric",
    "DataValidator",
    "ValidationReport",
    "CheckpointManager",
    "StreamingOutputWriter",
    "deduplicate_listings",
    "deduplicate_by_vin_only",
    "deduplicate_by_url_only",
    "SeleniumDriver",
    "SeleniumDealershipScraper"
]

