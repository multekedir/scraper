"""
Checkpoint System - Resume scraping after crashes/failures

Saves progress periodically and allows resuming from the last checkpoint.
"""

import json
import logging
from pathlib import Path
from typing import List, Set, Optional
from datetime import datetime
from .models import CarListing
from .utils import save_to_json, load_from_json

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint saving and loading for scraping operations."""
    
    def __init__(self, checkpoint_file: str = ".scraper_checkpoint.json"):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_file: Path to checkpoint file
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.completed_dealerships: Set[str] = set()
        self.scraped_listings: List[CarListing] = []
        self.start_time: Optional[datetime] = None
        self.last_update: Optional[datetime] = None
        
    def load(self) -> bool:
        """
        Load checkpoint from file.
        
        Returns:
            True if checkpoint was loaded, False if no checkpoint exists
        """
        if not self.checkpoint_file.exists():
            logger.info("No checkpoint found, starting fresh")
            return False
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load completed dealerships
            self.completed_dealerships = set(data.get('completed_dealerships', []))
            
            # Load scraped listings
            listings_data = data.get('scraped_listings', [])
            self.scraped_listings = []
            for listing_dict in listings_data:
                # Convert scraped_at from ISO string to datetime if present
                if 'scraped_at' in listing_dict and isinstance(listing_dict['scraped_at'], str):
                    listing_dict['scraped_at'] = datetime.fromisoformat(listing_dict['scraped_at'])
                self.scraped_listings.append(CarListing(**listing_dict))
            
            # Load timestamps
            if 'start_time' in data:
                self.start_time = datetime.fromisoformat(data['start_time'])
            if 'last_update' in data:
                self.last_update = datetime.fromisoformat(data['last_update'])
            
            logger.info(f"Loaded checkpoint: {len(self.completed_dealerships)} dealerships completed, "
                       f"{len(self.scraped_listings)} listings scraped")
            if self.last_update:
                logger.info(f"Last update: {self.last_update}")
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}, starting fresh")
            return False
    
    def save(self, completed_dealerships: Set[str], scraped_listings: List[CarListing]):
        """
        Save checkpoint to file.
        
        Args:
            completed_dealerships: Set of completed dealership names/IDs
            scraped_listings: List of scraped CarListing objects
        """
        self.completed_dealerships = completed_dealerships
        self.scraped_listings = scraped_listings
        self.last_update = datetime.now()
        
        if self.start_time is None:
            self.start_time = self.last_update
        
        try:
            # Convert listings to dict format
            listings_data = []
            for listing in scraped_listings:
                listing_dict = {
                    'dealer_name': listing.dealer_name,
                    'dealer_website': listing.dealer_website,
                    'vehicle_url': listing.vehicle_url,
                    'year': listing.year,
                    'make': listing.make,
                    'model': listing.model,
                    'trim': listing.trim,
                    'new_used': listing.new_used,
                    'fuel_type': listing.fuel_type,
                    'drivetrain': listing.drivetrain,
                    'transmission': listing.transmission,
                    'body_style': listing.body_style,
                    'msrp': listing.msrp,
                    'sale_price': listing.sale_price,
                    'total_price': listing.total_price,
                    'currency': listing.currency,
                    'price_note': listing.price_note,
                    'vin': listing.vin,
                    'stock_number': listing.stock_number,
                    'mileage': listing.mileage,
                    'mileage_units': listing.mileage_units,
                    'in_stock_status': listing.in_stock_status,
                    'exterior_color': listing.exterior_color,
                    'interior_color': listing.interior_color,
                    'dealer_location_city': listing.dealer_location_city,
                    'dealer_location_state': listing.dealer_location_state,
                    'images': listing.images,
                    'description': listing.description,
                    'features': listing.features,
                    'scraped_at': listing.scraped_at.isoformat() if listing.scraped_at else None,
                }
                listings_data.append(listing_dict)
            
            checkpoint_data = {
                'completed_dealerships': list(completed_dealerships),
                'scraped_listings': listings_data,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'last_update': self.last_update.isoformat(),
                'version': '1.0'
            }
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.checkpoint_file)
            logger.debug(f"Checkpoint saved: {len(completed_dealerships)} dealerships, {len(scraped_listings)} listings")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}", exc_info=True)
    
    def is_completed(self, dealership_name: str) -> bool:
        """
        Check if a dealership has been completed.
        
        Args:
            dealership_name: Name of the dealership to check
            
        Returns:
            True if dealership is already completed
        """
        return dealership_name in self.completed_dealerships
    
    def add_listing(self, listing: CarListing):
        """Add a scraped listing to the checkpoint."""
        self.scraped_listings.append(listing)
    
    def mark_completed(self, dealership_name: str):
        """Mark a dealership as completed."""
        self.completed_dealerships.add(dealership_name)
    
    def get_progress(self) -> dict:
        """
        Get progress information.
        
        Returns:
            Dictionary with progress stats
        """
        return {
            'completed_dealerships': len(self.completed_dealerships),
            'scraped_listings': len(self.scraped_listings),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update': self.last_update.isoformat() if self.last_update else None,
        }
    
    def clear(self):
        """Clear checkpoint (start fresh)."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        self.completed_dealerships = set()
        self.scraped_listings = []
        self.start_time = None
        self.last_update = None
        logger.info("Checkpoint cleared")
    
    def get_listings(self) -> List[CarListing]:
        """Get all scraped listings from checkpoint."""
        return self.scraped_listings.copy()

