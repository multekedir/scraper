"""
Field keywords for identifying and extracting vehicle data from dealership pages.
"""

FIELD_KEYWORDS = {
    "name": [  # year / make / model / trim
        # usually in the main H1/H2 on detail pages and card titles on listing pages
        # you don't search for these literally, you just grab the big heading
        # but you can sanity-check it with:
        "New",
        "Used",
        "Certified",
    ],
    "price": [
        "MSRP",
        "Internet Price",
        "Sale Price",
        "Our Price",
        "Dealer Price",
        "No Bull Price",
        "One Price",
        "E-Price",
        "Request ePrice",
        "$",  # generic, but useful combined with the others
    ],
    "vin": [
        "VIN",
        "Vin:",
        "Vehicle Identification Number",
    ],
    "stock_number": [
        "Stock #",
        "Stock:",
        "Stock Number",
        "Stk #",
    ],
    "mileage": [
        "Mileage",
        "Odometer",
        "Miles",
        "mi.",
    ],
    "condition": [  # new vs used vs CPO
        "Condition",
        "New",
        "Used",
        "Pre-Owned",
        "Certified Pre-Owned",
        "CPO",
    ],
    "fuel_type": [
        "Fuel Type",
        "Fuel",
        "Engine",          # often 'Engine: Electric Motor'
        "Hybrid",
        "Plug-In Hybrid",
        "PHEV",
        "Electric",
        "EV",
        "Battery Electric",
        "BEV",
    ],
    "availability": [
        "In Stock",
        "Available",
        "In Transit",
        "On the Way",
        "Sold",
        "Reserved",
        "Order Yours",
    ],
    "body_style": [
        "Body Style",
        "Body:",
        "Sedan",
        "SUV",
        "Truck",
        "Hatchback",
        "Wagon",
    ],
    "colors": [
        "Exterior Color",
        "Interior Color",
        "Ext. Color",
        "Int. Color",
        "Exterior:",
        "Interior:",
    ],
}

# Helper function to get keywords for a field
def get_keywords(field_name: str) -> list:
    """Get keywords for a specific field."""
    return FIELD_KEYWORDS.get(field_name, [])

# Helper function to check if text contains any keyword for a field
def contains_keyword(text: str, field_name: str, case_sensitive: bool = False) -> bool:
    """Check if text contains any keyword for a field."""
    if not text:
        return False
    
    keywords = get_keywords(field_name)
    if not keywords:
        return False
    
    if not case_sensitive:
        text = text.lower()
        keywords = [kw.lower() for kw in keywords]
    
    return any(keyword in text for keyword in keywords)
