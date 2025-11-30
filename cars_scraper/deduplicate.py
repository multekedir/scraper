"""
Deduplication utilities for removing duplicate car listings.
"""

from typing import List, Dict, Tuple
import logging
from .models import CarListing

logger = logging.getLogger(__name__)


def deduplicate_listings(cars: List[CarListing], prefer_latest: bool = True) -> Tuple[List[CarListing], Dict[str, int]]:
    """
    Remove duplicate listings based on VIN or URL.
    
    Args:
        cars: List of CarListing objects
        prefer_latest: If True, keep the listing with the most recent scraped_at timestamp
    
    Returns:
        Tuple of (deduplicated_list, stats_dict) where stats contains:
        - 'total': Total listings before deduplication
        - 'duplicates_by_vin': Number of duplicates removed by VIN
        - 'duplicates_by_url': Number of duplicates removed by URL
        - 'final': Final count after deduplication
    """
    if not cars:
        return [], {
            'total': 0,
            'duplicates_by_vin': 0,
            'duplicates_by_url': 0,
            'final': 0
        }
    
    stats = {
        'total': len(cars),
        'duplicates_by_vin': 0,
        'duplicates_by_url': 0,
        'final': 0
    }
    
    # Track seen VINs and URLs - map to the best listing (latest if prefer_latest)
    seen_by_vin: Dict[str, CarListing] = {}
    seen_by_url: Dict[str, CarListing] = {}
    deduplicated: List[CarListing] = []
    
    for car in cars:
        is_duplicate = False
        
        # Check for duplicate by VIN (most reliable)
        if car.vin:
            vin_normalized = car.vin.strip().upper()
            if vin_normalized in seen_by_vin:
                existing = seen_by_vin[vin_normalized]
                # Decide which one to keep
                if prefer_latest and car.scraped_at and existing.scraped_at:
                    if car.scraped_at > existing.scraped_at:
                        # Replace with newer one
                        seen_by_vin[vin_normalized] = car
                        # Remove old one from deduplicated list
                        if existing in deduplicated:
                            deduplicated.remove(existing)
                        deduplicated.append(car)
                    # Otherwise keep existing, skip this one
                else:
                    # Keep first one (existing), skip this one
                    pass
                is_duplicate = True
                stats['duplicates_by_vin'] += 1
                logger.debug(f"Duplicate VIN found: {vin_normalized} - {car.vehicle_url}")
            else:
                seen_by_vin[vin_normalized] = car
        
        # Check for duplicate by URL (fallback if no VIN)
        if not is_duplicate and car.vehicle_url:
            url_normalized = car.vehicle_url.strip().lower()
            if url_normalized in seen_by_url:
                existing = seen_by_url[url_normalized]
                # Decide which one to keep
                if prefer_latest and car.scraped_at and existing.scraped_at:
                    if car.scraped_at > existing.scraped_at:
                        # Replace with newer one
                        seen_by_url[url_normalized] = car
                        # Remove old one from deduplicated list
                        if existing in deduplicated:
                            deduplicated.remove(existing)
                        deduplicated.append(car)
                    # Otherwise keep existing, skip this one
                else:
                    # Keep first one (existing), skip this one
                    pass
                is_duplicate = True
                stats['duplicates_by_url'] += 1
                logger.debug(f"Duplicate URL found: {url_normalized}")
            else:
                seen_by_url[url_normalized] = car
        
        # Add to deduplicated list if not a duplicate
        if not is_duplicate:
            deduplicated.append(car)
    
    stats['final'] = len(deduplicated)
    
    return deduplicated, stats


def deduplicate_by_vin_only(cars: List[CarListing]) -> Tuple[List[CarListing], int]:
    """
    Remove duplicates based on VIN only (more strict).
    
    Args:
        cars: List of CarListing objects
    
    Returns:
        Tuple of (deduplicated_list, duplicates_removed_count)
    """
    if not cars:
        return [], 0
    
    seen_vins: Dict[str, CarListing] = {}
    deduplicated: List[CarListing] = []
    duplicates_removed = 0
    
    for car in cars:
        if car.vin:
            vin_normalized = car.vin.strip().upper()
            if vin_normalized not in seen_vins:
                seen_vins[vin_normalized] = car
                deduplicated.append(car)
            else:
                duplicates_removed += 1
                logger.debug(f"Duplicate VIN removed: {vin_normalized}")
        else:
            # If no VIN, keep it (can't deduplicate without VIN)
            deduplicated.append(car)
    
    return deduplicated, duplicates_removed


def deduplicate_by_url_only(cars: List[CarListing]) -> Tuple[List[CarListing], int]:
    """
    Remove duplicates based on URL only.
    
    Args:
        cars: List of CarListing objects
    
    Returns:
        Tuple of (deduplicated_list, duplicates_removed_count)
    """
    if not cars:
        return [], 0
    
    seen_urls: Dict[str, CarListing] = {}
    deduplicated: List[CarListing] = []
    duplicates_removed = 0
    
    for car in cars:
        if car.vehicle_url:
            url_normalized = car.vehicle_url.strip().lower()
            if url_normalized not in seen_urls:
                seen_urls[url_normalized] = car
                deduplicated.append(car)
            else:
                duplicates_removed += 1
                logger.debug(f"Duplicate URL removed: {url_normalized}")
        else:
            # If no URL, keep it (can't deduplicate without URL)
            deduplicated.append(car)
    
    return deduplicated, duplicates_removed

