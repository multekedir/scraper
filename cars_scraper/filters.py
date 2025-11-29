"""
Filtering logic for car listings.
"""

from typing import List, Optional
from datetime import datetime
from .models import CarListing


def filter_cars(
    cars: List[CarListing],
    is_electric: bool = True,
    max_price: float = 60000,
    new_only: bool = True,
    max_mileage: int = 200,
    fuel_types: Optional[List[str]] = None,
    min_price: Optional[float] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    makes: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    exclude_makes: Optional[List[str]] = None,
    exclude_models: Optional[List[str]] = None,
    drivetrains: Optional[List[str]] = None,
    exclude_drivetrains: Optional[List[str]] = None,
    dealers: Optional[List[str]] = None,
    exclude_dealers: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    states: Optional[List[str]] = None,
    availability_status: Optional[List[str]] = None,
    exclude_status: Optional[List[str]] = None,
) -> List[CarListing]:
    """
    Filter car listings based on comprehensive criteria.
    
    Args:
        cars: List of car listings to filter
        is_electric: Filter for electric cars only (default: True)
        max_price: Maximum price threshold (default: 60000)
        new_only: Filter for new cars only (default: True)
        max_mileage: Maximum mileage for a car to be considered new (default: 200)
        fuel_types: List of allowed fuel types (e.g., ["electric", "bev", "phev"]). 
                    If None and is_electric=True, uses default electric types.
        min_price: Minimum price threshold (optional)
        min_year: Minimum model year (optional)
        max_year: Maximum model year (optional)
        makes: List of allowed makes (None = all makes)
        models: List of allowed models (None = all models)
        exclude_makes: List of makes to exclude
        exclude_models: List of models to exclude
        drivetrains: List of allowed drivetrains (None = all drivetrains). Examples: ["AWD", "FWD", "RWD", "4WD"]
        exclude_drivetrains: List of drivetrains to exclude
        dealers: List of dealer names to include (None = all dealers)
        exclude_dealers: List of dealer names to exclude
        cities: List of cities to include (None = all cities)
        states: List of states to include (None = all states)
        availability_status: List of allowed statuses (None = all except excluded)
        exclude_status: List of statuses to exclude (default: ['sold'])
    
    Returns:
        Filtered list of car listings
    """
    if fuel_types is None and is_electric:
        fuel_types = ["electric", "ev", "bev", "phev", "plug-in", "plugin"]
    
    if exclude_makes is None:
        exclude_makes = []
    if exclude_models is None:
        exclude_models = []
    if exclude_drivetrains is None:
        exclude_drivetrains = []
    if exclude_dealers is None:
        exclude_dealers = []
    if exclude_status is None:
        exclude_status = ['sold']
    
    filtered = []
    
    for car in cars:
        # Check fuel type requirement
        if is_electric:
            if fuel_types:
                if not car.fuel_type or car.fuel_type.lower() not in [ft.lower() for ft in fuel_types]:
                    # Fallback to legacy is_electric property
                    if not car.is_electric:
                        continue
            elif not car.is_electric:
                continue
        
        # Check price requirements
        car_price = car.price
        if car_price > max_price:
            continue
        if min_price is not None and car_price < min_price:
            continue
        
        # Check year requirements
        if min_year is not None and car.year < min_year:
            continue
        if max_year is not None and car.year > max_year:
            continue
        
        # Check make/model filters
        if makes is not None and car.make not in makes:
            continue
        if models is not None and car.model not in models:
            continue
        if car.make in exclude_makes:
            continue
        if car.model in exclude_models:
            continue
        
        # Check drivetrain filters
        if drivetrains is not None and car.drivetrain:
            # Normalize drivetrain for comparison (case-insensitive)
            car_dt = car.drivetrain.upper() if car.drivetrain else None
            allowed_dts = [dt.upper() for dt in drivetrains]
            if car_dt not in allowed_dts:
                continue
        if exclude_drivetrains and car.drivetrain:
            car_dt = car.drivetrain.upper() if car.drivetrain else None
            excluded_dts = [dt.upper() for dt in exclude_drivetrains]
            if car_dt in excluded_dts:
                continue
        
        # Check dealer filters
        if dealers is not None and car.dealer_name not in dealers:
            continue
        if car.dealer_name in exclude_dealers:
            continue
        
        # Check location filters
        if cities is not None and car.dealer_location_city:
            if car.dealer_location_city not in cities:
                continue
        if states is not None and car.dealer_location_state:
            if car.dealer_location_state not in states:
                continue
        
        # Check availability status
        if car.in_stock_status in exclude_status:
            continue
        if availability_status is not None:
            if not car.in_stock_status or car.in_stock_status not in availability_status:
                continue
        
        # Check new car requirement
        if new_only:
            if car.new_used != "new":
                continue
            if not car.is_new(max_mileage):
                continue
        
        filtered.append(car)
    
    return filtered


def get_current_year() -> int:
    """Get the current year."""
    return datetime.now().year

