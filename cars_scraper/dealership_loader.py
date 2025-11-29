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
    
    def __init__(self, name: str, website: str, city: str):
        self.name = name
        self.website = website.rstrip('/')
        self.city = city
    
    def __repr__(self):
        return f"DealershipInfo(name='{self.name}', website='{self.website}', city='{self.city}')"


def load_dealerships_from_csv(csv_path: str) -> List[DealershipInfo]:
    """
    Load dealership information from a CSV file.
    
    Expected CSV format:
        Dealership Name,Website,City
    
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
            
            # Validate headers
            expected_headers = ['Dealership Name', 'Website', 'City']
            if not all(header in reader.fieldnames for header in expected_headers):
                raise ValueError(f"CSV must contain columns: {', '.join(expected_headers)}")
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                name = row.get('Dealership Name', '').strip()
                website = row.get('Website', '').strip()
                city = row.get('City', '').strip()
                
                if not name or not website:
                    logger.warning(f"Skipping row {row_num}: missing name or website")
                    continue
                
                if not website.startswith(('http://', 'https://')):
                    logger.warning(f"Row {row_num}: website '{website}' doesn't start with http:// or https://")
                    continue
                
                dealerships.append(DealershipInfo(name, website, city))
        
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

