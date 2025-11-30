"""
Utility functions for JSON and CSV output and validation.
"""

import json
import csv
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .models import CarListing


def save_to_json(cars: List[CarListing], output_path: str = "cars.json", pretty: bool = True) -> None:
    """
    Save car listings to a JSON file.
    
    Args:
        cars: List of CarListing objects to save
        output_path: Path to output JSON file (default: "cars.json")
        pretty: Whether to pretty-print the JSON (default: True)
    """
    data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_listings": len(cars),
            "source": "electric-car-scraper-cli"
        },
        "cars": [car.to_dict() for car in cars]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)


def load_from_json(input_path: str) -> List[CarListing]:
    """
    Load car listings from a JSON file.
    
    Args:
        input_path: Path to input JSON file
    
    Returns:
        List of CarListing objects
    """
    from datetime import datetime
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cars = []
    for car_dict in data.get("cars", []):
        # Convert scraped_at from ISO string to datetime if present
        if 'scraped_at' in car_dict and isinstance(car_dict['scraped_at'], str):
            car_dict['scraped_at'] = datetime.fromisoformat(car_dict['scraped_at'])
        cars.append(CarListing(**car_dict))
    
    return cars


def save_to_csv(cars: List[CarListing], output_path: str = "cars.csv") -> None:
    """
    Save car listings to a CSV file.
    
    Args:
        cars: List of CarListing objects to save
        output_path: Path to output CSV file (default: "cars.csv")
    """
    if not cars:
        # Create empty CSV with headers
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=_get_csv_fieldnames())
            writer.writeheader()
        return
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = _get_csv_fieldnames()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for car in cars:
            row = _car_to_csv_row(car)
            writer.writerow(row)


def _get_csv_fieldnames() -> List[str]:
    """Get CSV column names."""
    return [
        'dealer_name',
        'dealer_website',
        'vehicle_url',
        'year',
        'make',
        'model',
        'trim',
        'new_used',
        'fuel_type',
        'drivetrain',
        'transmission',
        'body_style',
        'msrp',
        'sale_price',
        'total_price',
        'currency',
        'price_note',
        'vin',
        'stock_number',
        'mileage',
        'mileage_units',
        'in_stock_status',
        'exterior_color',
        'interior_color',
        'dealer_location_city',
        'dealer_location_state',
        'description',
        'features',  # Will be joined with semicolon
        'images',    # Will be joined with semicolon
        'scraped_at',
    ]


def _car_to_csv_row(car: CarListing) -> dict:
    """Convert CarListing to CSV row dictionary."""
    return {
        'dealer_name': car.dealer_name or '',
        'dealer_website': car.dealer_website or '',
        'vehicle_url': car.vehicle_url or '',
        'year': car.year or '',
        'make': car.make or '',
        'model': car.model or '',
        'trim': car.trim or '',
        'new_used': car.new_used or '',
        'fuel_type': car.fuel_type or '',
        'drivetrain': car.drivetrain or '',
        'transmission': car.transmission or '',
        'body_style': car.body_style or '',
        'msrp': car.msrp if car.msrp is not None else '',
        'sale_price': car.sale_price if car.sale_price is not None else '',
        'total_price': car.total_price if car.total_price is not None else '',
        'currency': car.currency or '',
        'price_note': car.price_note or '',
        'vin': car.vin or '',
        'stock_number': car.stock_number or '',
        'mileage': car.mileage if car.mileage is not None else '',
        'mileage_units': car.mileage_units or '',
        'in_stock_status': car.in_stock_status or '',
        'exterior_color': car.exterior_color or '',
        'interior_color': car.interior_color or '',
        'dealer_location_city': car.dealer_location_city or '',
        'dealer_location_state': car.dealer_location_state or '',
        'description': (car.description or '').replace('\n', ' ').replace('\r', ' '),
        'features': '; '.join(car.features) if car.features else '',
        'images': '; '.join(car.images) if car.images else '',
        'scraped_at': car.scraped_at.isoformat() if car.scraped_at else '',
    }


def load_from_csv(input_path: str) -> List[CarListing]:
    """
    Load car listings from a CSV file.
    
    Args:
        input_path: Path to input CSV file
    
    Returns:
        List of CarListing objects
    """
    cars = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Convert CSV row back to CarListing
            car_dict = {
                'dealer_name': row.get('dealer_name', ''),
                'dealer_website': row.get('dealer_website', ''),
                'vehicle_url': row.get('vehicle_url', ''),
                'year': int(row['year']) if row.get('year') else datetime.now().year,
                'make': row.get('make', ''),
                'model': row.get('model', ''),
                'trim': row.get('trim') or None,
                'new_used': row.get('new_used', 'new'),
                'fuel_type': row.get('fuel_type') or None,
                'drivetrain': row.get('drivetrain') or None,
                'transmission': row.get('transmission') or None,
                'body_style': row.get('body_style') or None,
                'msrp': float(row['msrp']) if row.get('msrp') else None,
                'sale_price': float(row['sale_price']) if row.get('sale_price') else None,
                'total_price': float(row['total_price']) if row.get('total_price') else None,
                'currency': row.get('currency', 'USD'),
                'price_note': row.get('price_note') or None,
                'vin': row.get('vin') or None,
                'stock_number': row.get('stock_number') or None,
                'mileage': int(row['mileage']) if row.get('mileage') else None,
                'mileage_units': row.get('mileage_units', 'mi'),
                'in_stock_status': row.get('in_stock_status') or None,
                'exterior_color': row.get('exterior_color') or None,
                'interior_color': row.get('interior_color') or None,
                'dealer_location_city': row.get('dealer_location_city') or None,
                'dealer_location_state': row.get('dealer_location_state') or None,
                'description': row.get('description') or None,
                'features': [f.strip() for f in row.get('features', '').split(';') if f.strip()],
                'images': [img.strip() for img in row.get('images', '').split(';') if img.strip()],
            }
            
            # Handle scraped_at
            if row.get('scraped_at'):
                try:
                    car_dict['scraped_at'] = datetime.fromisoformat(row['scraped_at'])
                except ValueError:
                    car_dict['scraped_at'] = datetime.now()
            else:
                car_dict['scraped_at'] = datetime.now()
            
            try:
                cars.append(CarListing(**car_dict))
            except Exception as e:
                # Skip invalid rows
                continue
    
    return cars


def save_to_file(cars: List[CarListing], output_path: str, format: Optional[str] = None) -> None:
    """
    Save car listings to a file, auto-detecting format from extension or using specified format.
    
    Args:
        cars: List of CarListing objects to save
        output_path: Path to output file
        format: Optional format override ('json' or 'csv'). If None, detected from file extension.
    """
    if format is None:
        # Auto-detect from file extension
        ext = Path(output_path).suffix.lower()
        if ext == '.csv':
            format = 'csv'
        elif ext in ['.json', '.jsonl']:
            format = 'json'
        else:
            # Default to JSON
            format = 'json'
    
    if format.lower() == 'csv':
        save_to_csv(cars, output_path)
    else:
        save_to_json(cars, output_path, pretty=True)


class StreamingOutputWriter:
    """
    Streams output incrementally to prevent data loss and memory issues.
    Saves results after each batch instead of waiting until the end.
    """
    
    def __init__(self, output_path: str, format: Optional[str] = None, append: bool = False):
        """
        Initialize streaming output writer.
        
        Args:
            output_path: Path to output file
            format: Output format ('json', 'csv', 'jsonl', or None for auto-detect)
            append: Whether to append to existing file (default: False)
        """
        self.output_path = Path(output_path)
        self.append = append
        
        # Auto-detect format if not specified
        if format is None:
            ext = self.output_path.suffix.lower()
            if ext == '.csv':
                self.format = 'csv'
            elif ext == '.jsonl':
                self.format = 'jsonl'
            elif ext == '.json':
                self.format = 'json'
            else:
                self.format = 'json'
        else:
            self.format = format.lower()
        
        # Initialize file based on format
        self._initialize_file()
    
    def _initialize_file(self):
        """Initialize output file with headers/metadata."""
        if self.append and self.output_path.exists():
            # File exists, don't overwrite headers
            return
        
        if self.format == 'csv':
            # Write CSV header
            with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=_get_csv_fieldnames())
                writer.writeheader()
        elif self.format == 'json':
            # Write JSON array start
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write('{\n')
                f.write('  "metadata": {\n')
                f.write(f'    "timestamp": "{datetime.now().isoformat()}",\n')
                f.write('    "source": "electric-car-scraper-cli",\n')
                f.write('    "streaming": true\n')
                f.write('  },\n')
                f.write('  "cars": [\n')
        elif self.format == 'jsonl':
            # JSONL doesn't need initialization, just append lines
            pass
    
    def append_cars(self, cars: List[CarListing]):
        """
        Append cars to output file incrementally.
        
        Args:
            cars: List of CarListing objects to append
        """
        if not cars:
            return
        
        if self.format == 'csv':
            # Append rows to CSV
            with open(self.output_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=_get_csv_fieldnames())
                for car in cars:
                    writer.writerow(_car_to_csv_row(car))
        
        elif self.format == 'jsonl':
            # Append JSON lines (one JSON object per line)
            with open(self.output_path, 'a', encoding='utf-8') as f:
                for car in cars:
                    json.dump(car.to_dict(), f, ensure_ascii=False)
                    f.write('\n')
        
        elif self.format == 'json':
            # Append to JSON array
            with open(self.output_path, 'r+', encoding='utf-8') as f:
                # Read existing content
                content = f.read()
                
                # Check if we need to add comma (if array is not empty)
                needs_comma = not content.rstrip().endswith('[\n')
                
                # Remove closing brackets/braces
                content = content.rstrip()
                if content.endswith('\n  ]\n}'):
                    content = content[:-7]  # Remove '\n  ]\n}'
                elif content.endswith(']'):
                    content = content[:-1]  # Remove ']'
                
                # Write back without closing
                f.seek(0)
                f.truncate()
                f.write(content)
                
                # Add comma if needed
                if needs_comma:
                    f.write(',\n')
                
                # Append new cars
                for i, car in enumerate(cars):
                    if i > 0:
                        f.write(',\n')
                    car_json = json.dumps(car.to_dict(), indent=4, ensure_ascii=False)
                    # Indent each line
                    for line in car_json.split('\n'):
                        f.write('    ' + line + '\n')
                
                # Close array and object
                f.write('  ]\n}')
    
    def finalize(self):
        """Finalize output file (close JSON arrays, etc.)."""
        if self.format == 'json':
            # Ensure JSON is properly closed
            with open(self.output_path, 'r+', encoding='utf-8') as f:
                content = f.read()
                if not content.rstrip().endswith('}'):
                    # Add closing if missing
                    f.seek(0, 2)  # Go to end
                    if not content.rstrip().endswith(']'):
                        f.write('\n  ]\n}')
                    else:
                        f.write('\n}')
    
    def get_count(self) -> int:
        """
        Get current count of saved listings.
        
        Returns:
            Number of listings in output file
        """
        if not self.output_path.exists():
            return 0
        
        try:
            if self.format == 'csv':
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    return sum(1 for _ in f) - 1  # Subtract header
            elif self.format == 'jsonl':
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    return sum(1 for _ in f)
            elif self.format == 'json':
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return len(data.get('cars', []))
        except Exception:
            return 0
        
        return 0

