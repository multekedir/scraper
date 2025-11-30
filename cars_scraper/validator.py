"""
Data Validator - Add to cars_scraper/validator.py

Validates car listings before saving to prevent bad data.
"""

from typing import List, Tuple, Optional
from datetime import datetime
import re
from .models import CarListing


class DataValidator:
    """Validate car listings for data quality."""
    
    # Known electric vehicle makes/models
    ELECTRIC_MAKES = {
        'Tesla', 'Rivian', 'Lucid', 'Polestar', 'BYD', 'Nio', 'Xpeng',
        'Fisker', 'Lordstown', 'Canoo', 'Faraday Future'
    }
    
    ELECTRIC_MODELS = {
        'Model S', 'Model 3', 'Model X', 'Model Y',  # Tesla
        'R1T', 'R1S',  # Rivian
        'Air',  # Lucid
        'Polestar 2', 'Polestar 3', 'Polestar 4',
        'Mustang Mach-E', 'F-150 Lightning',  # Ford
        'Bolt', 'Bolt EUV', 'Blazer EV', 'Equinox EV', 'Silverado EV',  # Chevy
        'IONIQ 5', 'IONIQ 6', 'Kona Electric',  # Hyundai
        'EV6', 'EV9', 'Niro EV',  # Kia
        'Ariya',  # Nissan
        'ID.4', 'ID.Buzz',  # VW
        'e-tron', 'Q4 e-tron', 'e-tron GT',  # Audi
        'EQE', 'EQS', 'EQB', 'EQC',  # Mercedes
        'iX', 'i4', 'iX1', 'i5', 'i7',  # BMW
        'Lyriq',  # Cadillac
        'Blazer EV', 'Equinox EV',  # GMC
        'bZ4X',  # Toyota
        'Solterra',  # Subaru
        'Prologue',  # Honda
        'ZDX',  # Acura
        'RZ',  # Lexus
    }
    
    @staticmethod
    def validate_listing(car: CarListing, strict: bool = False) -> Tuple[bool, List[str]]:
        """
        Validate a car listing.
        
        Args:
            car: CarListing to validate
            strict: If True, apply stricter validation rules
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        warnings = []
        
        # ===== CRITICAL VALIDATIONS (always fail) =====
        
        # Required fields
        if not car.make or car.make == "Unknown":
            errors.append("Missing or unknown make")
        if not car.model or car.model == "Unknown":
            errors.append("Missing or unknown model")
        
        # Year validation
        current_year = datetime.now().year
        if car.year < 2015:
            errors.append(f"Year too old for electric vehicle: {car.year}")
        elif car.year > current_year + 2:
            errors.append(f"Year too far in future: {car.year}")
        
        # Price validation
        if not car.price or car.price <= 0:
            if strict:
                errors.append("Missing or zero price")
            else:
                warnings.append("Missing price - may be 'call for price' listing")
        elif car.price < 5000:
            errors.append(f"Suspiciously low price: ${car.price:,.0f}")
        elif car.price > 250000:
            errors.append(f"Price exceeds maximum for target vehicles: ${car.price:,.0f}")
        
        # URL validation
        if not car.vehicle_url or not car.vehicle_url.startswith('http'):
            errors.append("Invalid or missing vehicle URL")
        
        # Dealer validation
        if not car.dealer_name:
            errors.append("Missing dealer name")
        if not car.dealer_website or not car.dealer_website.startswith('http'):
            errors.append("Invalid dealer website")
        
        # ===== ELECTRIC VEHICLE VALIDATION =====
        
        # Check if actually electric
        is_likely_electric = DataValidator._is_likely_electric(car)
        if not is_likely_electric:
            errors.append(f"Vehicle does not appear to be electric: {car.year} {car.make} {car.model}")
        
        # Fuel type validation
        if car.fuel_type:
            fuel_lower = car.fuel_type.lower()
            non_electric_fuels = ['gasoline', 'gas', 'diesel', 'flex', 'e85']
            if any(fuel in fuel_lower for fuel in non_electric_fuels):
                # Check if it's a hybrid
                if 'hybrid' not in fuel_lower and 'phev' not in fuel_lower:
                    errors.append(f"Non-electric fuel type: {car.fuel_type}")
        
        # ===== DATA QUALITY WARNINGS =====
        
        # VIN validation
        if car.vin:
            if not DataValidator._is_valid_vin(car.vin):
                warnings.append(f"Invalid VIN format: {car.vin}")
        else:
            if strict:
                warnings.append("Missing VIN (harder to verify uniqueness)")
        
        # Mileage sanity checks
        if car.mileage is not None:
            if car.new_used == "new" and car.mileage > 500:
                warnings.append(f"High mileage for new car: {car.mileage}")
            if car.mileage > 300000:
                errors.append(f"Extremely high mileage: {car.mileage:,}")
            if car.mileage < 0:
                errors.append(f"Negative mileage: {car.mileage}")
        
        # Condition validation
        if car.new_used not in ["new", "used", "cpo"]:
            warnings.append(f"Unusual condition value: {car.new_used}")
        
        # Price reasonableness for make/model
        if car.price > 0:
            price_warnings = DataValidator._validate_price_for_model(car)
            warnings.extend(price_warnings)
        
        # Check for placeholder/test data
        if DataValidator._looks_like_test_data(car):
            errors.append("Appears to be test/placeholder data")
        
        # ===== FINAL DECISION =====
        
        is_valid = len(errors) == 0
        all_issues = errors + [f"WARNING: {w}" for w in warnings]
        
        return is_valid, all_issues
    
    @staticmethod
    def _is_likely_electric(car: CarListing) -> bool:
        """Check if car is likely an electric vehicle."""
        # Check make
        if car.make in DataValidator.ELECTRIC_MAKES:
            return True
        
        # Check model
        if car.model in DataValidator.ELECTRIC_MODELS:
            return True
        
        # Check model contains electric keywords
        model_lower = (car.model or "").lower()
        electric_keywords = ['electric', 'ev', 'e-tron', 'eq', 'id.', 'i4', 'ix', 'ioniq', 'mach-e', 'lightning', 'bolt', 'leaf']
        if any(kw in model_lower for kw in electric_keywords):
            return True
        
        # Check fuel type
        if car.fuel_type:
            fuel_lower = car.fuel_type.lower()
            if any(kw in fuel_lower for kw in ['electric', 'ev', 'bev', 'phev', 'plug']):
                return True
        
        # Check is_electric property
        if car.is_electric:
            return True
        
        return False
    
    @staticmethod
    def _is_valid_vin(vin: str) -> bool:
        """Validate VIN format."""
        if not vin:
            return False
        
        # VIN must be exactly 17 characters
        if len(vin) != 17:
            return False
        
        # VIN can only contain certain characters (no I, O, Q)
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            return False
        
        return True
    
    @staticmethod
    def _validate_price_for_model(car: CarListing) -> List[str]:
        """Check if price is reasonable for the make/model."""
        warnings = []
        
        # Known price ranges for popular EVs (approximate MSRP ranges)
        price_ranges = {
            'Tesla': {
                'Model 3': (35000, 55000),
                'Model Y': (40000, 65000),
                'Model S': (75000, 120000),
                'Model X': (80000, 120000),
            },
            'Hyundai': {
                'IONIQ 5': (40000, 60000),
                'IONIQ 6': (42000, 62000),
                'Kona Electric': (33000, 45000),
            },
            'Kia': {
                'EV6': (42000, 65000),
                'EV9': (55000, 75000),
                'Niro EV': (39000, 50000),
            },
            'Ford': {
                'Mustang Mach-E': (40000, 65000),
                'F-150 Lightning': (50000, 95000),
            },
            'Chevrolet': {
                'Bolt': (25000, 35000),
                'Bolt EUV': (28000, 38000),
                'Blazer EV': (45000, 65000),
                'Equinox EV': (30000, 50000),
            },
        }
        
        if car.make in price_ranges and car.model in price_ranges[car.make]:
            min_price, max_price = price_ranges[car.make][car.model]
            
            # Allow 20% variance for used, options, etc.
            min_price = min_price * 0.6  # Used can be 40% less
            max_price = max_price * 1.3  # Options can add 30%
            
            if car.price < min_price:
                warnings.append(f"Price ${car.price:,.0f} seems low for {car.make} {car.model} (typical: ${min_price:,.0f}-${max_price:,.0f})")
            elif car.price > max_price:
                warnings.append(f"Price ${car.price:,.0f} seems high for {car.make} {car.model} (typical: ${min_price:,.0f}-${max_price:,.0f})")
        
        return warnings
    
    @staticmethod
    def _looks_like_test_data(car: CarListing) -> bool:
        """Check if listing appears to be test/placeholder data."""
        test_indicators = [
            'test', 'example', 'sample', 'placeholder', 'demo',
            'xxx', 'zzz', 'abc123', '000000', '999999'
        ]
        
        # Check various fields
        fields_to_check = [
            car.make, car.model, car.trim, car.dealer_name,
            car.vin, car.stock_number, car.exterior_color
        ]
        
        for field in fields_to_check:
            if field:
                field_lower = str(field).lower()
                if any(indicator in field_lower for indicator in test_indicators):
                    return True
        
        return False


class ValidationReport:
    """Generate validation report for a batch of listings."""
    
    def __init__(self):
        self.total = 0
        self.valid = 0
        self.invalid = 0
        self.issues = {}
    
    def add_result(self, car: CarListing, is_valid: bool, errors: List[str]):
        """Add validation result."""
        self.total += 1
        if is_valid:
            self.valid += 1
        else:
            self.invalid += 1
            
            # Track error frequency
            for error in errors:
                # Clean error (remove specific values)
                clean_error = re.sub(r'\$[\d,]+', '$X', error)
                clean_error = re.sub(r'\d{4}', 'YYYY', clean_error)
                
                if clean_error not in self.issues:
                    self.issues[clean_error] = 0
                self.issues[clean_error] += 1
    
    def print_report(self):
        """Print validation report."""
        print("\n" + "="*80)
        print("DATA VALIDATION REPORT")
        print("="*80)
        print(f"Total listings: {self.total}")
        print(f"✅ Valid: {self.valid} ({self.valid/self.total*100:.1f}%)" if self.total > 0 else "✅ Valid: 0")
        print(f"❌ Invalid: {self.invalid} ({self.invalid/self.total*100:.1f}%)" if self.total > 0 else "❌ Invalid: 0")
        
        if self.issues:
            print(f"\nTop issues found:")
            sorted_issues = sorted(self.issues.items(), key=lambda x: x[1], reverse=True)
            for issue, count in sorted_issues[:10]:
                print(f"  • {issue}: {count} occurrences")
        
        print("="*80 + "\n")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == '__main__':
    print(__doc__)
    print("\nTo use in your scraper:")
    print("""
# In parse_detail_page or scrape method:

from .validator import DataValidator, ValidationReport



report = ValidationReport()



for summary in summaries:

    listing = self.parse_detail_page(detail_html, summary.detail_url)

    if listing:

        is_valid, errors = DataValidator.validate_listing(listing)

        report.add_result(listing, is_valid, errors)

        

        if is_valid:

            all_listings.append(listing)

        else:

            logger.warning(f"Invalid listing: {listing.year} {listing.make} {listing.model}")

            for error in errors:

                logger.warning(f"  - {error}")



report.print_report()

    """)
    print("\nThis will:")
    print("  • Validate all scraped data")
    print("  • Filter out non-electric vehicles")
    print("  • Catch price/mileage anomalies")
    print("  • Check VIN format")
    print("  • Generate quality report")

