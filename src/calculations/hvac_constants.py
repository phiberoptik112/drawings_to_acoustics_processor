"""
HVAC Calculation Constants - Centralized definition of all magic numbers
Replaces hardcoded values throughout the HVAC calculation system
"""

from typing import List

# =============================================================================
# ACOUSTIC FREQUENCY CONSTANTS
# =============================================================================

# Standard octave band center frequencies (Hz)
OCTAVE_BAND_FREQUENCIES: List[int] = [63, 125, 250, 500, 1000, 2000, 4000, 8000]

# Number of octave bands in standard analysis
NUM_OCTAVE_BANDS: int = 8

# Frequency band labels for JSON/dict storage
FREQUENCY_BAND_LABELS: List[str] = ["63", "125", "250", "500", "1000", "2000", "4000", "8000"]

# Default spectrum for initialization
DEFAULT_SPECTRUM_LEVELS: List[float] = [50.0] * NUM_OCTAVE_BANDS

# =============================================================================
# NOISE CRITERIA (NC) CONSTANTS
# =============================================================================

# NC rating range limits
MIN_NC_RATING: int = 15
MAX_NC_RATING: int = 65
DEFAULT_NC_RATING: int = 30

# NC curve data (dB levels at each frequency for each NC rating)
NC_CURVE_DATA = {
    15: [47, 36, 29, 22, 17, 14, 12, 11],
    20: [51, 40, 33, 26, 22, 19, 17, 16],
    25: [54, 44, 37, 31, 27, 24, 22, 21],
    30: [57, 48, 41, 35, 31, 29, 28, 27],
    35: [60, 52, 45, 40, 36, 34, 33, 32],
    40: [64, 56, 50, 45, 41, 39, 38, 37],
    45: [67, 60, 54, 49, 46, 44, 43, 42],
    50: [71, 64, 58, 54, 51, 49, 48, 47],
    55: [74, 67, 62, 58, 56, 54, 53, 52],
    60: [77, 71, 67, 63, 61, 59, 58, 57],
    65: [80, 75, 71, 68, 66, 64, 63, 62]
}

# =============================================================================
# DUCT SYSTEM CONSTANTS
# =============================================================================

# Default duct dimensions (inches)
DEFAULT_DUCT_WIDTH_IN: float = 12.0
DEFAULT_DUCT_HEIGHT_IN: float = 8.0
DEFAULT_ROUND_DIAMETER_IN: float = 12.0

# Default duct properties
DEFAULT_DUCT_LINING_THICKNESS_IN: float = 0.0
DEFAULT_FLOW_VELOCITY_FPM: float = 800.0
DEFAULT_PRESSURE_DROP_INWG: float = 0.0

# =============================================================================
# CFM (AIRFLOW) CONSTANTS
# =============================================================================

# Default CFM values by component type
DEFAULT_CFM_VALUES = {
    'ahu': 5000.0,        # Air Handling Unit - typical building AHU
    'fan': 2000.0,        # Exhaust/Supply Fan
    'vav': 500.0,         # Variable Air Volume box
    'diffuser': 150.0,    # Supply air diffuser
    'grille': 200.0,      # Return air grille
    'damper': 100.0,      # Volume damper (minimal flow)
    'silencer': 1000.0,   # Duct silencer (pass-through)
    'coil': 800.0,        # Heating/cooling coil
    'elbow': 100.0,       # Duct elbow (minimal restriction)
    'branch': 300.0,      # Duct branch/tee
    'doas': 3000.0,       # Dedicated Outdoor Air System
    'rtu': 4000.0,        # Rooftop Unit
    'rf': 2500.0,         # Return Fan
    'sf': 2500.0,         # Supply Fan
}

# CFM validation ranges (min, max) by component type
CFM_VALIDATION_RANGES = {
    'ahu': (500.0, 50000.0),
    'fan': (100.0, 20000.0),
    'vav': (50.0, 2000.0),
    'diffuser': (25.0, 500.0),
    'grille': (50.0, 1000.0),
    'damper': (10.0, 5000.0),
    'silencer': (100.0, 10000.0),
    'coil': (100.0, 5000.0),
    'elbow': (10.0, 10000.0),
    'branch': (50.0, 5000.0),
    'doas': (500.0, 20000.0),
    'rtu': (1000.0, 30000.0),
    'rf': (500.0, 15000.0),
    'sf': (500.0, 15000.0),
}

# General fallback CFM for unknown components
DEFAULT_CFM_FALLBACK: float = 1000.0

# CFM calculation limits
MAX_CFM_VALUE: float = 100000.0
MIN_CFM_VALUE: float = 10.0

# Duct material constants
SHEET_METAL_DENSITY_LB_FT3: float = 490.0  # Steel sheet metal
FIBERGLASS_DENSITY_LB_FT3: float = 0.6     # Fiberglass lining

# =============================================================================
# CALCULATION LIMITS AND VALIDATION
# =============================================================================

# Physical limits for validation
MAX_DUCT_DIMENSION_IN: float = 120.0      # 10 feet maximum
MIN_DUCT_DIMENSION_IN: float = 4.0        # 4 inch minimum
MAX_FLOW_VELOCITY_FPM: float = 4000.0     # 4000 FPM maximum
MIN_FLOW_VELOCITY_FPM: float = 100.0      # 100 FPM minimum
MAX_DUCT_LENGTH_FT: float = 1000.0        # 1000 feet maximum
MIN_DUCT_LENGTH_FT: float = 0.1           # 0.1 feet minimum

# Sound level limits
MAX_SOUND_LEVEL_DB: float = 120.0         # 120 dB maximum
MIN_SOUND_LEVEL_DB: float = 0.0           # 0 dB minimum
HEARING_DAMAGE_THRESHOLD_DB: float = 85.0 # OSHA limit

# =============================================================================
# PATH ANALYSIS CONSTANTS
# =============================================================================

# Maximum path elements for validation
MAX_PATH_ELEMENTS: int = 50
MAX_SEGMENTS_PER_PATH: int = 25
MAX_FITTINGS_PER_SEGMENT: int = 10

# Default source noise levels by component type
DEFAULT_COMPONENT_NOISE_LEVELS = {
    'ahu': 85.0,      # Air Handling Unit
    'fan': 80.0,      # Fan
    'vav': 45.0,      # Variable Air Volume box
    'diffuser': 35.0, # Diffuser
    'grille': 30.0,   # Return grille
    'damper': 25.0,   # Damper
    'silencer': 20.0  # Silencer
}

# =============================================================================
# FITTING NOISE ADJUSTMENTS
# =============================================================================

# Standard fitting noise adjustments (dB)
FITTING_NOISE_ADJUSTMENTS = {
    'elbow_90': 3.0,
    'elbow_45': 1.5,
    'tee_branch': 6.0,
    'tee_straight': 3.0,
    'transition': 2.0,
    'damper': 5.0,
    'silencer': -15.0,  # Negative because it reduces noise
    'diffuser': 8.0
}

# =============================================================================
# MATHEMATICAL CONSTANTS
# =============================================================================

# Mathematical constants for calculations
PI: float = 3.141592653589793
SOUND_SPEED_FT_S: float = 1125.0          # Speed of sound at room temperature
AIR_DENSITY_LB_FT3: float = 0.075         # Standard air density

# Conversion factors
INCHES_PER_FOOT: float = 12.0
SQUARE_INCHES_PER_SQUARE_FOOT: float = 144.0
PASCALS_PER_INWG: float = 248.84          # Inches of water gauge to Pascals

# =============================================================================
# CALCULATION ITERATION LIMITS
# =============================================================================

# Maximum iterations for iterative calculations
MAX_CALCULATION_ITERATIONS: int = 100
CONVERGENCE_TOLERANCE: float = 0.01        # dB tolerance for convergence
DEFAULT_ITERATION_LIMIT: int = 50

# =============================================================================
# TERMINAL EFFECT CONSTANTS
# =============================================================================

# End reflection loss constants
DEFAULT_ERL_COEFFICIENT: float = 10.0     # Default end reflection loss
ROOM_ABSORPTION_COEFFICIENT: float = 0.2  # Default room absorption
DEFAULT_ROOM_VOLUME_FT3: float = 1000.0   # Default room volume

# =============================================================================
# ENVIRONMENTAL CONSTANTS
# =============================================================================

# Standard atmospheric conditions
STANDARD_TEMPERATURE_F: float = 70.0      # Room temperature
STANDARD_PRESSURE_PSIA: float = 14.7      # Sea level pressure
STANDARD_HUMIDITY_PERCENT: float = 50.0   # Relative humidity

# =============================================================================
# VALIDATION AND ERROR HANDLING
# =============================================================================

# Thresholds for warnings and errors
HIGH_NOISE_WARNING_DB: float = 60.0       # Warn if noise exceeds this
VERY_HIGH_NOISE_ERROR_DB: float = 80.0    # Error if noise exceeds this
HIGH_VELOCITY_WARNING_FPM: float = 2000.0 # Warn if velocity exceeds this

# Default values for missing data
DEFAULT_MISSING_VALUE: float = 0.0
DEFAULT_UNKNOWN_STRING: str = "unknown"

# =============================================================================
# DEBUG AND LOGGING CONSTANTS
# =============================================================================

# Debug output formatting
DEBUG_DECIMAL_PLACES: int = 1             # Decimal places for debug output
MAX_DEBUG_ARRAY_LENGTH: int = 20          # Max items to show in debug arrays

# =============================================================================
# UNIT CONVERSION HELPERS
# =============================================================================

def inches_to_feet(inches: float) -> float:
    """Convert inches to feet"""
    return inches / INCHES_PER_FOOT

def feet_to_inches(feet: float) -> float:
    """Convert feet to inches"""
    return feet * INCHES_PER_FOOT

def square_inches_to_square_feet(sq_in: float) -> float:
    """Convert square inches to square feet"""
    return sq_in / SQUARE_INCHES_PER_SQUARE_FOOT

def circular_area_from_diameter(diameter_in: float) -> float:
    """Calculate circular area from diameter in inches, return square feet"""
    radius_ft = inches_to_feet(diameter_in) / 2.0
    return PI * radius_ft * radius_ft

def rectangular_area_from_dimensions(width_in: float, height_in: float) -> float:
    """Calculate rectangular area from dimensions in inches, return square feet"""
    width_ft = inches_to_feet(width_in)
    height_ft = inches_to_feet(height_in)
    return width_ft * height_ft

# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def is_valid_frequency_spectrum(spectrum: List[float]) -> bool:
    """Check if spectrum has correct number of frequency bands"""
    return (isinstance(spectrum, list) and 
            len(spectrum) == NUM_OCTAVE_BANDS and 
            all(isinstance(level, (int, float)) for level in spectrum))

def is_valid_sound_level(level: float) -> bool:
    """Check if sound level is within reasonable range"""
    return MIN_SOUND_LEVEL_DB <= level <= MAX_SOUND_LEVEL_DB

def is_valid_nc_rating(nc: int) -> bool:
    """Check if NC rating is within valid range"""
    return MIN_NC_RATING <= nc <= MAX_NC_RATING

def is_valid_cfm_value(cfm: float, component_type: str = None) -> bool:
    """Check if CFM value is within reasonable range for component type"""
    if not (MIN_CFM_VALUE <= cfm <= MAX_CFM_VALUE):
        return False
    
    if component_type and component_type.lower() in CFM_VALIDATION_RANGES:
        min_cfm, max_cfm = CFM_VALIDATION_RANGES[component_type.lower()]
        return min_cfm <= cfm <= max_cfm
    
    return True

def get_default_cfm_for_component(component_type: str) -> float:
    """Get default CFM value for a component type"""
    return DEFAULT_CFM_VALUES.get(component_type.lower(), DEFAULT_CFM_FALLBACK)