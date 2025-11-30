"""
Utility to load dealership information from CSV files.
"""

import csv
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DealershipInfo:
    """Information about a dealership."""
    
    def __init__(self, id: str, name: str, base_url: str, new_inventory_url: Optional[str] = None, city: Optional[str] = None):
        self.id = id
        self.name = name
        self.website = base_url.rstrip('/')
        self.base_url = base_url.rstrip('/')
        self.new_inventory_url = new_inventory_url.rstrip('/') if new_inventory_url else None
        self.city = city or ""  # Optional for backward compatibility
    
    def __repr__(self):
        return f"DealershipInfo(id='{self.id}', name='{self.name}', base_url='{self.base_url}', new_inventory_url='{self.new_inventory_url}')"


def load_dealerships_from_csv(csv_path: str) -> List[DealershipInfo]:
    """
    Load dealership information from a CSV file.
    
    Supports two CSV formats:
    1. New format: id,name,base_url,new_inventory_url
    2. Legacy format: Dealership Name,Website,City
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        List of DealershipInfo objects
    
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    dealerships = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check which format we're using
            is_new_format = 'id' in reader.fieldnames and 'name' in reader.fieldnames and 'base_url' in reader.fieldnames
            is_legacy_format = 'Dealership Name' in reader.fieldnames and 'Website' in reader.fieldnames
            
            if not is_new_format and not is_legacy_format:
                raise ValueError("CSV must contain either (id,name,base_url) or (Dealership Name,Website) columns")
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                if is_new_format:
                    # New format: id,name,base_url,new_inventory_url
                    dealer_id = row.get('id', '').strip()
                    name = row.get('name', '').strip()
                    base_url = row.get('base_url', '').strip()
                    new_inventory_url = row.get('new_inventory_url', '').strip() or None
                    city = row.get('city', '').strip() or None
                    
                    if not dealer_id or not name or not base_url:
                        logger.warning(f"Skipping row {row_num}: missing id, name, or base_url")
                        continue
                    
                    if not base_url.startswith(('http://', 'https://')):
                        logger.warning(f"Row {row_num}: base_url '{base_url}' doesn't start with http:// or https://")
                        continue
                    
                    dealerships.append(DealershipInfo(dealer_id, name, base_url, new_inventory_url, city))
                else:
                    # Legacy format: Dealership Name,Website,City
                    name = row.get('Dealership Name', '').strip()
                    website = row.get('Website', '').strip()
                    city = row.get('City', '').strip()
                    
                    if not name or not website:
                        logger.warning(f"Skipping row {row_num}: missing name or website")
                        continue
                    
                    if not website.startswith(('http://', 'https://')):
                        logger.warning(f"Row {row_num}: website '{website}' doesn't start with http:// or https://")
                        continue
                    
                    # Generate ID from name for legacy format
                    dealer_id = name.lower().replace(' ', '_').replace(',', '').replace('(', '').replace(')', '')
                    dealerships.append(DealershipInfo(dealer_id, name, website, None, city))
        
        logger.info(f"Loaded {len(dealerships)} dealerships from {csv_path}")
        return dealerships
    
    except csv.Error as e:
        raise ValueError(f"Error parsing CSV file: {e}")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")


def get_dealership_by_name(dealerships: List[DealershipInfo], name: str) -> Optional[DealershipInfo]:
    """Get a dealership by name (case-insensitive partial match)."""
    name_lower = name.lower()
    for dealer in dealerships:
        if name_lower in dealer.name.lower():
            return dealer
    return None


def get_dealerships_by_city(dealerships: List[DealershipInfo], city: str) -> List[DealershipInfo]:
    """Get all dealerships in a specific city (case-insensitive)."""
    city_lower = city.lower()
    return [d for d in dealerships if city_lower in d.city.lower()]

