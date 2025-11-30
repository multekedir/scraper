"""
CLI interface for the electric car scraper.
"""

import argparse
import sys
import logging
import time
from pathlib import Path
from typing import List, Dict
from .scraper import DealershipScraper
from .filters import filter_cars
from .utils import save_to_json, save_to_csv, save_to_file, StreamingOutputWriter
from .deduplicate import deduplicate_listings
from .models import CarListing
from .logging_config import setup_logging
from .config import ScraperConfig
from .validator import ValidationReport

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

# Import scrapers to register them
try:
    from . import scrapers  # This will register all scrapers
except ImportError:
    pass  # No scrapers module yet


# Registry of available scrapers
SCRAPER_REGISTRY: Dict[str, type] = {}


def register_scraper(name: str, scraper_class: type):
    """Register a scraper class."""
    SCRAPER_REGISTRY[name] = scraper_class


def get_available_scrapers() -> List[str]:
    """Get list of available scraper names."""
    return list(SCRAPER_REGISTRY.keys())


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape dealership sites for new electric cars under $60,000",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all-sites
  %(prog)s --site dealer1 --site dealer2
  %(prog)s --all-sites --max-price 50000 --output results.json
        """
    )
    
    parser.add_argument(
        '--site',
        action='append',
        dest='sites',
        help='Specific dealership site to scrape (can be used multiple times)'
    )
    
    parser.add_argument(
        '--all-sites',
        action='store_true',
        help='Scrape all available dealership sites'
    )
    
    parser.add_argument(
        '--output',
        default='cars.csv',
        help='Output file path (default: cars.csv). Format auto-detected from extension (.json or .csv)'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'csv', 'auto'],
        default='auto',
        help='Output format: json, csv, or auto (detect from file extension). Default: auto'
    )
    
    parser.add_argument(
        '--max-price',
        type=float,
        default=60000,
        help='Maximum price threshold in dollars (default: 60000)'
    )
    
    parser.add_argument(
        '--max-mileage',
        type=int,
        default=100,
        help='Maximum mileage for a car to be considered new (default: 100)'
    )
    
    parser.add_argument(
        '--include-used',
        action='store_true',
        help='Include used cars (default: only new cars)'
    )
    
    parser.add_argument(
        '--include-non-electric',
        action='store_true',
        help='Include non-electric cars (default: only electric)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Optional file path to write logs to'
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration file (JSON). CLI arguments override config file settings.'
    )
    
    parser.add_argument(
        '--create-config',
        help='Create a default configuration file at the specified path and exit'
    )
    
    parser.add_argument(
        '--use-selenium',
        action='store_true',
        help='Use Selenium WebDriver for JavaScript-heavy sites (slower but handles dynamic content)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window when using Selenium (default: headless mode)'
    )
    
    args = parser.parse_args()
    
    # Handle --create-config
    if args.create_config:
        config = ScraperConfig.create_default(args.create_config)
        print(f"Created default configuration file: {args.create_config}")
        print("Edit this file to customize your filtering criteria.")
        sys.exit(0)
    
    # Set up basic logging first (before config loading, in case we need to log)
    # We'll reconfigure with config settings later
    setup_logging(level=logging.INFO, log_file=None)
    logger = logging.getLogger(__name__)
    
    # Load configuration file if provided, or try default location
    config = None
    default_config_path = 'scraper_config.json'
    
    if args.config:
        config_path = args.config
    elif Path(default_config_path).exists():
        # Auto-load default config if it exists
        config_path = default_config_path
        logger.info(f"Auto-loading default config from {default_config_path}")
    else:
        config_path = None
    
    if config_path:
        try:
            config = ScraperConfig.from_file(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Use default config (no file)
        config = ScraperConfig()
    
    # Override config with CLI arguments (CLI takes precedence)
    # Note: argparse defaults are applied, so we check if they differ from config defaults
    # For max_price and max_mileage, we always use CLI value if provided (since defaults match)
    config.max_price = args.max_price
    config.max_mileage = args.max_mileage
    if args.include_used:
        config.new_only = False
    if args.include_non_electric:
        config.electric_only = False
    if args.output != 'cars.csv':
        config.output_path = args.output
    if args.format != 'auto':
        config.output_format = args.format
    if args.log_level != 'INFO':
        config.log_level = args.log_level
    if args.log_file:
        config.log_file = args.log_file
    if args.sites:
        config.sites = args.sites
        config.all_sites = False
    if args.all_sites:
        config.all_sites = True
    
    # Reconfigure logging with final config settings
    log_level = getattr(logging, config.log_level)
    setup_logging(level=log_level, log_file=config.log_file)
    logger = logging.getLogger(__name__)
    
    # Log configuration details
    logger.info("=" * 60)
    logger.info("Starting Electric Car Scraper")
    logger.info("=" * 60)
    logger.info(f"Configuration loaded from: {config_path if config_path else 'defaults'}")
    logger.info("Filter Configuration:")
    logger.info(f"  - Electric only: {config.electric_only}")
    logger.info(f"  - New only: {config.new_only}")
    logger.info(f"  - Max price: ${config.max_price:,.0f}")
    if config.min_price:
        logger.info(f"  - Min price: ${config.min_price:,.0f}")
    logger.info(f"  - Max mileage: {config.max_mileage} miles")
    if config.fuel_types:
        logger.info(f"  - Fuel types: {config.fuel_types}")
    if config.makes:
        logger.info(f"  - Makes: {config.makes}")
    if config.exclude_makes:
        logger.info(f"  - Exclude makes: {config.exclude_makes}")
    if config.models:
        logger.info(f"  - Models: {config.models}")
    if config.exclude_models:
        logger.info(f"  - Exclude models: {config.exclude_models}")
    if config.drivetrains:
        logger.info(f"  - Drivetrains: {config.drivetrains}")
    if config.exclude_drivetrains:
        logger.info(f"  - Exclude drivetrains: {config.exclude_drivetrains}")
    if config.dealers:
        logger.info(f"  - Dealers: {config.dealers}")
    if config.exclude_dealers:
        logger.info(f"  - Exclude dealers: {config.exclude_dealers}")
    if config.cities:
        logger.info(f"  - Cities: {config.cities}")
    if config.states:
        logger.info(f"  - States: {config.states}")
    if config.availability_status:
        logger.info(f"  - Availability status: {config.availability_status}")
    if config.exclude_status:
        logger.info(f"  - Exclude status: {config.exclude_status}")
    if config.min_year:
        logger.info(f"  - Min year: {config.min_year}")
    if config.max_year:
        logger.info(f"  - Max year: {config.max_year}")
    logger.info(f"Output: {config.output_path} ({config.output_format})")
    logger.info("-" * 60)
    
    # Determine which sites to scrape
    available_scrapers = get_available_scrapers()
    all_cars: List[CarListing] = []
    use_generic_scraper = False
    
    # Default to generic scraper (always use it for --all-sites or when no sites specified)
    if config.all_sites:
        logger.info("Using generic scraper for all dealerships from CSV (--all-sites)")
        use_generic_scraper = True
    elif config.sites:
        # Use specific registered scrapers if they exist
        if available_scrapers:
            sites_to_scrape = config.sites
            # Validate sites
            invalid_sites = [site for site in sites_to_scrape if site not in available_scrapers]
            if invalid_sites:
                print(f"Error: Unknown sites: {', '.join(invalid_sites)}", file=sys.stderr)
                print(f"Available sites: {', '.join(available_scrapers)}", file=sys.stderr)
                logger.error(f"Invalid sites specified: {invalid_sites}")
                logger.info(f"Available sites: {available_scrapers}")
                sys.exit(1)
            use_generic_scraper = False
        else:
            # No registered scrapers, fall back to generic scraper
            logger.info("No registered scrapers found, using generic scraper for all dealerships from CSV")
            use_generic_scraper = True
    else:
        # No sites specified - default to generic scraper
        logger.info("No specific sites specified, using generic scraper for all dealerships from CSV")
        use_generic_scraper = True
    
    # Use generic scraper if needed
    if use_generic_scraper:
        from .scrapers.generic_scraper import MultiDealershipScraper
        
        # Find CSV file
        csv_path = Path("dealerships.csv")
        if not csv_path.exists():
            csv_path = Path("../dealerships.csv")
        if not csv_path.exists():
            # Try relative to script location
            script_dir = Path(__file__).parent.parent.parent
            csv_path = script_dir / "dealerships.csv"
        
        if not csv_path.exists():
            print("Error: dealerships.csv not found. Please ensure it's in the project root.", file=sys.stderr)
            logger.error("dealerships.csv not found")
            sys.exit(1)
        
        try:
            logger.info(f"Loading dealerships from {csv_path}")
            
            # Initialize streaming output writer
            streaming_writer = StreamingOutputWriter(
                output_path=config.output_path,
                format=config.output_format if config.output_format != 'auto' else None,
                append=False  # Start fresh, checkpoint handles resume
            )
            logger.info(f"Streaming output to {config.output_path} ({streaming_writer.format} format)")
            
            # Determine if we should use Selenium
            use_selenium = args.use_selenium
            headless = not args.no_headless  # Default to headless unless --no-headless is specified
            
            if use_selenium:
                logger.info(f"Using Selenium WebDriver (headless={headless})")
            
            # Use MultiDealershipScraper to scrape all (with checkpoint support and streaming)
            multi_scraper = MultiDealershipScraper(
                csv_path=str(csv_path),
                checkpoint_file=".scraper_checkpoint.json",
                resume=True,
                use_selenium=use_selenium,
                headless=headless
            )
            all_cars = multi_scraper.scrape_all(output_writer=streaming_writer)
            
            # Finalize output file
            streaming_writer.finalize()
            
            logger.info(f"Generic scraper collected {len(all_cars)} total listings")
            logger.info(f"Output saved to {config.output_path} ({streaming_writer.get_count()} listings)")
            sites_to_scrape = []  # Empty to skip the per-site loop
            
        except Exception as e:
            print(f"Error using generic scraper: {e}", file=sys.stderr)
            logger.error(f"Generic scraper failed: {e}", exc_info=True)
            sys.exit(1)
    else:
        # Use registered scrapers
        sites_to_scrape = config.sites
    
    # Scrape all selected sites (if using registered scrapers)
    if sites_to_scrape:  # Only if we have specific sites to scrape
        logger.info(f"Starting scrape of {len(sites_to_scrape)} site(s): {sites_to_scrape}")
        filter_summary = f"electric={config.electric_only}, new={config.new_only}, max_price=${config.max_price:,.0f}"
        if config.min_price:
            filter_summary += f", min_price=${config.min_price:,.0f}"
        if config.makes:
            filter_summary += f", makes={config.makes}"
        logger.info(f"Filters: {filter_summary}")
        print(f"Scraping {len(sites_to_scrape)} site(s)...")
        print(f"Filters: {filter_summary}")
        print("-" * 60)
        
        for site_name in tqdm(sites_to_scrape, desc="Scraping sites", disable=not TQDM_AVAILABLE):
            logger.info(f"Starting scrape: {site_name}")
            start_time = time.time()
            try:
                scraper_class = SCRAPER_REGISTRY[site_name]
                scraper = scraper_class()
                cars = scraper.scrape()
                all_cars.extend(cars)
                elapsed = time.time() - start_time
                logger.info(f"{site_name}: Found {len(cars)} listings in {elapsed:.2f} seconds")
                if cars:
                    logger.debug(f"{site_name}: Sample vehicles: {[f'{c.year} {c.make} {c.model}' for c in cars[:3]]}")
            except Exception as e:
                elapsed = time.time() - start_time
                error_msg = f"Error scraping {site_name}: {str(e)}"
                logger.error(f"{site_name}: Failed after {elapsed:.2f} seconds - {error_msg}", exc_info=True)
                continue
        
        print("-" * 60)
        print(f"Total listings found: {len(all_cars)}")
        logger.info(f"Total listings collected: {len(all_cars)} from {len(sites_to_scrape)} sites")
    else:
        # Using generic scraper - all_cars already populated
        print("-" * 60)
        print(f"Total listings found: {len(all_cars)}")
        logger.info(f"Total listings collected: {len(all_cars)} using generic scraper")
    
    if not all_cars:
        logger.warning("No vehicles found from any site")
        print("No cars found matching the criteria.")
        sys.exit(0)
    
    # Validate all scraped listings
    logger.info("Validating scraped data...")
    from .validator import DataValidator
    validation_report = ValidationReport()
    validated_cars = []
    
    for car in all_cars:
        is_valid, errors = DataValidator.validate_listing(car, strict=False)
        validation_report.add_result(car, is_valid, errors)
        if is_valid:
            validated_cars.append(car)
        else:
            # Log invalid listings
            error_msgs = [e for e in errors if not e.startswith("WARNING:")]
            if error_msgs:
                logger.debug(f"Invalid listing: {car.year} {car.make} {car.model} - {error_msgs[0]}")
    
    # Print validation report
    validation_report.print_report()
    
    # Use validated cars for filtering
    all_cars = validated_cars
    
    if not all_cars:
        logger.warning("No valid vehicles found after validation")
        print("No valid cars found after data validation.")
        sys.exit(0)
    
    # Remove duplicates (by VIN or URL)
    logger.info("Removing duplicate listings...")
    all_cars, dedup_stats = deduplicate_listings(all_cars, prefer_latest=True)
    
    total_duplicates = dedup_stats['duplicates_by_vin'] + dedup_stats['duplicates_by_url']
    if total_duplicates > 0:
        logger.info(f"Deduplication: Removed {total_duplicates} duplicates "
                   f"({dedup_stats['duplicates_by_vin']} by VIN, {dedup_stats['duplicates_by_url']} by URL)")
        logger.info(f"After deduplication: {len(all_cars)}/{dedup_stats['total']} unique listings")
        print(f"Removed {total_duplicates} duplicate listings ({dedup_stats['duplicates_by_vin']} by VIN, {dedup_stats['duplicates_by_url']} by URL)")
    else:
        logger.info("No duplicates found")
    
    if not all_cars:
        logger.warning("No vehicles found after deduplication")
        print("No unique cars found after deduplication.")
        sys.exit(0)
    
    # Log pre-filter statistics
    logger.info("Pre-filter Statistics:")
    if all_cars:
        prices = [car.price for car in all_cars if car.price > 0]
        if prices:
            logger.info(f"  - Price range: ${min(prices):,.0f} - ${max(prices):,.0f} (avg: ${sum(prices)/len(prices):,.0f})")
        makes_count = {}
        for car in all_cars:
            makes_count[car.make] = makes_count.get(car.make, 0) + 1
        logger.info(f"  - Makes found: {dict(sorted(makes_count.items(), key=lambda x: x[1], reverse=True)[:10])}")
        electric_count = sum(1 for car in all_cars if car.is_electric)
        logger.info(f"  - Electric vehicles: {electric_count}/{len(all_cars)} ({electric_count/len(all_cars)*100:.1f}%)")
        new_count = sum(1 for car in all_cars if car.new_used == "new")
        logger.info(f"  - New vehicles: {new_count}/{len(all_cars)} ({new_count/len(all_cars)*100:.1f}%)")
    
    # Apply filters using config
    logger.info("-" * 60)
    logger.info("Applying filters...")
    filtered_cars = filter_cars(
        all_cars,
        is_electric=config.electric_only,
        max_price=config.max_price,
        new_only=config.new_only,
        max_mileage=config.max_mileage,
        fuel_types=config.fuel_types,
        min_price=config.min_price,
        min_year=config.min_year,
        max_year=config.max_year,
        makes=config.makes,
        models=config.models,
        exclude_makes=config.exclude_makes,
        exclude_models=config.exclude_models,
        drivetrains=config.drivetrains,
        exclude_drivetrains=config.exclude_drivetrains,
        dealers=config.dealers,
        exclude_dealers=config.exclude_dealers,
        cities=config.cities,
        states=config.states,
        availability_status=config.availability_status,
        exclude_status=config.exclude_status,
    )
    
    print(f"Filtered listings: {len(filtered_cars)}")
    logger.info(f"Filtered results: {len(filtered_cars)}/{len(all_cars)} vehicles ({len(filtered_cars)/len(all_cars)*100:.1f}% passed filters)")
    
    # Log filter breakdown
    if filtered_cars:
        logger.info("Post-filter Statistics:")
        prices = [car.price for car in filtered_cars if car.price > 0]
        if prices:
            logger.info(f"  - Price range: ${min(prices):,.0f} - ${max(prices):,.0f} (avg: ${sum(prices)/len(prices):,.0f})")
        makes_count = {}
        for car in filtered_cars:
            makes_count[car.make] = makes_count.get(car.make, 0) + 1
        logger.info(f"  - Makes: {dict(sorted(makes_count.items(), key=lambda x: x[1], reverse=True))}")
        if config.drivetrains:
            drivetrain_count = {}
            for car in filtered_cars:
                dt = car.drivetrain or "Unknown"
                drivetrain_count[dt] = drivetrain_count.get(dt, 0) + 1
            logger.info(f"  - Drivetrains: {drivetrain_count}")
    
    # Save to file (JSON or CSV) - only if not using streaming output
    # Streaming output is already saved incrementally during scraping
    if filtered_cars and not use_generic_scraper:
        logger.info(f"Saving {len(filtered_cars)} vehicles to {config.output_path}")
        output_format = config.output_format if config.output_format != 'auto' else None
        save_to_file(filtered_cars, config.output_path, format=output_format)
        output_type = 'CSV' if config.output_path.endswith('.csv') or output_format == 'csv' else 'JSON'
        print(f"Results saved to {config.output_path} ({output_type})")
        logger.info(f"Successfully saved {len(filtered_cars)} vehicles to {config.output_path} ({output_type})")
    elif use_generic_scraper:
        # Streaming output already handled, just log
        logger.info(f"Results streamed to {config.output_path} during scraping")
        output_format = config.output_format if config.output_format != 'auto' else 'auto'
        print(f"Results streamed to {config.output_path} ({output_format} format)")
        
        # Print summary statistics
        if filtered_cars:
            prices = [car.price for car in filtered_cars]
            print(f"\nSummary:")
            print(f"  Average price: ${sum(prices) / len(prices):,.2f}")
            print(f"  Lowest price: ${min(prices):,.2f}")
            print(f"  Highest price: ${max(prices):,.2f}")
            
            # Group by make
            makes = {}
            for car in filtered_cars:
                makes[car.make] = makes.get(car.make, 0) + 1
            
            print(f"\nBy make:")
            for make, count in sorted(makes.items(), key=lambda x: x[1], reverse=True):
                print(f"  {make}: {count}")
                logger.info(f"  Make breakdown: {make} = {count}")
    else:
        print("No cars found matching the criteria.")
        logger.warning("No vehicles passed the filters")
    
    logger.info("=" * 60)
    logger.info("Scraping completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

