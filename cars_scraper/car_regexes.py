"""
Regular expressions for extracting vehicle data from dealership pages.
"""

import re


# ==============
# BASIC HELPERS
# ==============

def first_group(pattern, text, flags=0):
    """
    Return the first matched group(1) for a compiled pattern or pattern string.
    None if no match.
    """
    if isinstance(pattern, str):
        regex = re.compile(pattern, flags)
    else:
        regex = pattern
    m = regex.search(text)
    return m.group(1).strip() if m else None


# =====================
# VIN (17-char standard)
# =====================

VIN_REGEX = re.compile(
    r"\b([A-HJ-NPR-Z0-9]{17})\b"
)

# Example use:
# vin = first_group(VIN_REGEX, page_text)


# =====================
# PRICE (USD with $)
# =====================

# Matches things like:
# $32,995   $32995   $32,995.00
PRICE_REGEX = re.compile(
    r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]{2})?)"
)

# Example:
# price_str = first_group(PRICE_REGEX, text)  # string like "32,995" or "32995.00"


# ==========================
# MILEAGE (number + miles/mi)
# ==========================

# Matches:
# 12,345 mi
# 5 miles
MILEAGE_REGEX = re.compile(
    r"\b([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*(?:mi|miles?)\b",
    re.IGNORECASE,
)

# Example:
# mileage_str = first_group(MILEAGE_REGEX, text)


# ====================
# STOCK NUMBER
# ====================

# Looks for labels like "Stock # ABC123"
STOCK_REGEX = re.compile(
    r"(?:Stock\s*(?:#|Number|No\.?)\s*[:#]?\s*([A-Za-z0-9\-]+))",
    re.IGNORECASE,
)

# Example:
# stock = first_group(STOCK_REGEX, text)


# ====================
# CONDITION (New/Used)
# ====================

CONDITION_REGEX = re.compile(
    r"\b(New|Used|Pre[-\s]?Owned|Certified Pre[-\s]?Owned|CPO)\b",
    re.IGNORECASE,
)

# Example:
# condition_raw = first_group(CONDITION_REGEX, text)


# ====================
# AVAILABILITY
# ====================

AVAILABILITY_REGEX = re.compile(
    r"\b("
    r"In Stock|Available|In Transit|On the Way|Sold|Reserved|"
    r"Coming Soon|Arriving Soon|Order Yours"
    r")\b",
    re.IGNORECASE,
)

# Example:
# availability_raw = first_group(AVAILABILITY_REGEX, text)


# ====================
# BODY STYLE
# ====================

# Try to capture "Body Style: SUV" or similar.
BODY_STYLE_LABEL_REGEX = re.compile(
    r"Body\s*Style[:\s]*([A-Za-z0-9 \-/]+)",
    re.IGNORECASE,
)

# Fallback generic styles:
BODY_STYLE_VALUE_REGEX = re.compile(
    r"\b(SUV|Sedan|Truck|Pickup|Van|Hatchback|Wagon|Crossover|Sport Utility)\b",
    re.IGNORECASE,
)

# Example:
# body_style = first_group(BODY_STYLE_LABEL_REGEX, text) or first_group(BODY_STYLE_VALUE_REGEX, text)


# ====================
# COLORS
# ====================

EXTERIOR_COLOR_REGEX = re.compile(
    r"(?:Exterior\s*Color|Ext\.?\s*Color)[:\s]*([A-Za-z0-9 /&\-]+)",
    re.IGNORECASE,
)

INTERIOR_COLOR_REGEX = re.compile(
    r"(?:Interior\s*Color|Int\.?\s*Color)[:\s]*([A-Za-z0-9 /&\-]+)",
    re.IGNORECASE,
)

# Example:
# ext_color = first_group(EXTERIOR_COLOR_REGEX, text)
# int_color = first_group(INTERIOR_COLOR_REGEX, text)


# ====================
# TRANSMISSION
# ====================

TRANSMISSION_REGEX = re.compile(
    r"(?:Transmission|Trans\.?)[:\s]*([A-Za-z0-9 \-/]+)",
    re.IGNORECASE,
)

# Example:
# transmission = first_group(TRANSMISSION_REGEX, text)


# ====================
# ENGINE (helps EV detect)
# ====================

ENGINE_REGEX = re.compile(
    r"(?:Engine|Motor)[:\s]*([A-Za-z0-9 .+/&\-]+)",
    re.IGNORECASE,
)

# Example:
# engine_raw = first_group(ENGINE_REGEX, text)


# ====================
# FUEL TYPE (label & value)
# ====================

FUEL_TYPE_LABEL_REGEX = re.compile(
    r"(?:Fuel\s*Type|Fuel)[:\s]*([A-Za-z0-9 /+\-]+)",
    re.IGNORECASE,
)

# Generic "fuel" words for backup:
FUEL_TYPE_VALUE_REGEX = re.compile(
    r"\b("
    r"Electric|EV|BEV|Hybrid|Plug[-\s]?In Hybrid|PHEV|"
    r"Gasoline|Gas|Diesel|Flex Fuel"
    r")\b",
    re.IGNORECASE,
)

# Example:
# fuel_raw = first_group(FUEL_TYPE_LABEL_REGEX, text) or first_group(FUEL_TYPE_VALUE_REGEX, text)


# ====================
# DRIVETRAIN / DRIVE TYPE
# ====================

DRIVETRAIN_REGEX = re.compile(
    r"\b("
    r"AWD|FWD|RWD|4WD|4x4|"
    r"All[-\s]?Wheel Drive|Front[-\s]?Wheel Drive|Rear[-\s]?Wheel Drive|Four[-\s]?Wheel Drive|"
    r"4MATIC|4MOTION|Quattro|xDrive"
    r")\b",
    re.IGNORECASE,
)

DRIVETRAIN_LABEL_REGEX = re.compile(
    r"(?:Drivetrain|Drive\s*Type|Drive|Driveline|Powertrain)[:\s]*([A-Za-z0-9 \-/]+)",
    re.IGNORECASE,
)

DRIVETRAIN_NORMALIZE = {
    "awd": "AWD",
    "all wheel drive": "AWD",
    "all-wheel drive": "AWD",
    "xdrive": "AWD",
    "4matic": "AWD",
    "4motion": "AWD",
    "quattro": "AWD",

    "fwd": "FWD",
    "front wheel drive": "FWD",
    "front-wheel drive": "FWD",

    "rwd": "RWD",
    "rear wheel drive": "RWD",
    "rear-wheel drive": "RWD",

    "4wd": "4WD",
    "4x4": "4WD",
    "four wheel drive": "4WD",
    "four-wheel drive": "4WD",
}


def normalize_drivetrain(raw):
    if not raw:
        return None
    t = raw.lower().strip()
    t = t.replace("-", " ")
    if t in DRIVETRAIN_NORMALIZE:
        return DRIVETRAIN_NORMALIZE[t]
    for key, val in DRIVETRAIN_NORMALIZE.items():
        if key in t:
            return val
    return None


# Example:
# dt_raw = first_group(DRIVETRAIN_LABEL_REGEX, text) or first_group(DRIVETRAIN_REGEX, text)
# drivetrain = normalize_drivetrain(dt_raw)


# ====================
# PRICE HELPERS
# ====================

def parse_price_to_int(price_str):
    """
    Turn '32,995.00' or '32995' into 32995 (int).
    Returns None if it can't parse.
    """
    if not price_str:
        return None
    s = price_str.strip().replace(",", "")
    try:
        # keep as int dollars
        return int(float(s))
    except ValueError:
        return None


# ====================
# ELECTRIC / EV DETECTION
# ====================

EV_KEYWORDS_REGEX = re.compile(
    r"\b("
    r"Electric|EV|BEV|Battery Electric|Zero Emission|ZEV|"
    r"Plug[-\s]?In Hybrid|PHEV"
    r")\b",
    re.IGNORECASE,
)


def is_electric(text):
    """
    Rough heuristic: true if any EV-related keyword appears.
    """
    return EV_KEYWORDS_REGEX.search(text or "") is not None

