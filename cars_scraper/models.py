"""
Data models for car listings.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class CarListing:
    """Represents a car listing from a dealership with comprehensive vehicle information."""
    
    # Required core fields
    dealer_name: str
    dealer_website: str
    vehicle_url: str
    year: int
    make: str
    model: str
    
    # Optional but important fields
    trim: Optional[str] = None
    new_used: str = "new"  # "new", "used", "cpo"
    fuel_type: Optional[str] = None  # "electric", "hybrid", "gasoline", "diesel", "phev", "bev"
    drivetrain: Optional[str] = None  # "FWD", "RWD", "AWD"
    transmission: Optional[str] = None
    body_style: Optional[str] = None  # "SUV", "sedan", "truck", etc.
    
    # Pricing
    msrp: Optional[float] = None
    sale_price: Optional[float] = None
    total_price: Optional[float] = None
    currency: str = "USD"
    price_note: Optional[str] = None  # e.g., "call_for_price"
    
    # Vehicle identification
    vin: Optional[str] = None
    stock_number: Optional[str] = None
    
    # Condition and status
    mileage: Optional[int] = None
    mileage_units: str = "mi"  # "mi" or "km"
    in_stock_status: Optional[str] = None  # "available", "in_transit", "sold", "reserved"
    
    # Appearance
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    
    # Location
    dealer_location_city: Optional[str] = None
    dealer_location_state: Optional[str] = None
    
    # Additional data
    images: list[str] = field(default_factory=list)
    description: Optional[str] = None
    features: list[str] = field(default_factory=list)
    
    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    
    # Legacy compatibility fields (computed properties)
    @property
    def url(self) -> str:
        """Legacy compatibility: vehicle_url."""
        return self.vehicle_url
    
    @property
    def dealership(self) -> str:
        """Legacy compatibility: dealer_name."""
        return self.dealer_name
    
    @property
    def price(self) -> float:
        """Legacy compatibility: returns sale_price, total_price, or msrp in that order."""
        if self.sale_price:
            return self.sale_price
        if self.total_price:
            return self.total_price
        if self.msrp:
            return self.msrp
        return 0.0
    
    @property
    def is_electric(self) -> bool:
        """Legacy compatibility: checks if fuel_type indicates electric."""
        if not self.fuel_type:
            return False
        fuel_lower = self.fuel_type.lower()
        return fuel_lower in ["electric", "ev", "bev", "phev", "plug-in", "plugin"]
    
    def __post_init__(self):
        """Validate the car listing data."""
        if not self.dealer_name or not isinstance(self.dealer_name, str):
            raise ValueError("dealer_name must be a non-empty string")
        if not self.dealer_website or not isinstance(self.dealer_website, str):
            raise ValueError("dealer_website must be a non-empty string")
        if not self.vehicle_url or not isinstance(self.vehicle_url, str):
            raise ValueError("vehicle_url must be a non-empty string")
        if not self.make or not isinstance(self.make, str):
            raise ValueError("make must be a non-empty string")
        if not self.model or not isinstance(self.model, str):
            raise ValueError("model must be a non-empty string")
        if not isinstance(self.year, int) or self.year < 1900 or self.year > datetime.now().year + 1:
            raise ValueError(f"year must be a valid year between 1900 and {datetime.now().year + 1}")
        if self.new_used not in ["new", "used", "cpo"]:
            raise ValueError("new_used must be one of: 'new', 'used', 'cpo'")
        if self.mileage is not None and (not isinstance(self.mileage, int) or self.mileage < 0):
            raise ValueError("mileage must be a non-negative integer or None")
        if self.msrp is not None and (not isinstance(self.msrp, (int, float)) or self.msrp < 0):
            raise ValueError("msrp must be a non-negative number or None")
        if self.sale_price is not None and (not isinstance(self.sale_price, (int, float)) or self.sale_price < 0):
            raise ValueError("sale_price must be a non-negative number or None")
        if self.total_price is not None and (not isinstance(self.total_price, (int, float)) or self.total_price < 0):
            raise ValueError("total_price must be a non-negative number or None")
    
    def to_dict(self) -> dict:
        """Convert the car listing to a dictionary."""
        return {
            "dealer_name": self.dealer_name,
            "dealer_website": self.dealer_website,
            "vehicle_url": self.vehicle_url,
            "year": self.year,
            "make": self.make,
            "model": self.model,
            "trim": self.trim,
            "new_used": self.new_used,
            "fuel_type": self.fuel_type,
            "drivetrain": self.drivetrain,
            "transmission": self.transmission,
            "body_style": self.body_style,
            "msrp": self.msrp,
            "sale_price": self.sale_price,
            "total_price": self.total_price,
            "currency": self.currency,
            "price_note": self.price_note,
            "vin": self.vin,
            "stock_number": self.stock_number,
            "mileage": self.mileage,
            "mileage_units": self.mileage_units,
            "in_stock_status": self.in_stock_status,
            "exterior_color": self.exterior_color,
            "interior_color": self.interior_color,
            "dealer_location_city": self.dealer_location_city,
            "dealer_location_state": self.dealer_location_state,
            "images": self.images,
            "description": self.description,
            "features": self.features,
            "scraped_at": self.scraped_at.isoformat(),
            # Legacy compatibility fields
            "price": self.price,
            "is_electric": self.is_electric,
            "url": self.url,
            "dealership": self.dealership,
        }
    
    def is_new(self, max_mileage: int = 200) -> bool:
        """Check if the car is considered new (low mileage)."""
        if self.new_used == "new":
            if self.mileage is None:
                # If mileage is not provided, assume it's new if year is current or next year
                current_year = datetime.now().year
                return self.year >= current_year - 1
            return self.mileage <= max_mileage
        return False

