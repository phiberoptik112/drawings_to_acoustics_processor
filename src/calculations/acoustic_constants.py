"""
Acoustic Calculation Constants - Centralized definition of RT60 and acoustic constants
Replaces hardcoded values throughout the acoustic calculation system
"""

from typing import List, Dict

# =============================================================================
# RT60 (REVERBERATION TIME) CONSTANTS
# =============================================================================

# Sabine formula constant (imperial units: cubic feet and sabins)
# RT60 = SABINE_CONSTANT * V / A
# where V = volume (cubic feet), A = total absorption (sabins)
SABINE_CONSTANT_IMPERIAL: float = 0.049

# Sabine formula constant (metric units: cubic meters and metric sabins)
# RT60 = SABINE_CONSTANT_METRIC * V / A
SABINE_CONSTANT_METRIC: float = 0.161

# =============================================================================
# RT60 ERROR AND SENTINEL VALUES
# =============================================================================

# Sentinel value for invalid/infinite RT60 (used in calculations and results)
RT60_INVALID_VALUE: float = 999.9

# Tolerance for RT60 compliance checking (percentage of target)
RT60_TOLERANCE_PERCENT: float = 0.1  # 10% tolerance

# =============================================================================
# ABSORPTION COEFFICIENT LIMITS
# =============================================================================

# Maximum absorption coefficient (theoretically 1.0, practically capped at 0.99)
MAX_ABSORPTION_COEFFICIENT: float = 0.99

# Minimum valid absorption coefficient
MIN_ABSORPTION_COEFFICIENT: float = 0.01

# =============================================================================
# FREQUENCY BANDS FOR RT60 ANALYSIS
# =============================================================================

# Standard octave band center frequencies for RT60 analysis (Hz)
RT60_OCTAVE_FREQUENCIES: List[int] = [125, 250, 500, 1000, 2000, 4000]

# NRC (Noise Reduction Coefficient) averaging frequencies (Hz)
NRC_FREQUENCIES: List[int] = [250, 500, 1000, 2000]

# Number of frequency bands in RT60 analysis
NUM_RT60_FREQUENCY_BANDS: int = 6

# =============================================================================
# ROOM TYPE TARGET RT60 VALUES (seconds)
# =============================================================================

# Default target RT60 values by room type (LEED/ANSI standards)
TARGET_RT60_BY_ROOM_TYPE: Dict[str, float] = {
    'classroom': 0.6,
    'office': 0.8,
    'conference': 0.7,
    'auditorium': 1.2,
    'lecture_hall': 0.9,
    'hospital_room': 0.6,
    'library': 0.8,
    'lobby': 1.0,
    'restaurant': 0.9,
    'worship': 1.5,
    'studio': 0.3,
    'default': 0.8
}

# =============================================================================
# SURFACE AREA CALCULATION CONSTANTS
# =============================================================================

# Minimum valid room volume (cubic feet)
MIN_ROOM_VOLUME_FT3: float = 10.0

# Maximum valid room volume (cubic feet) - practical limit
MAX_ROOM_VOLUME_FT3: float = 1000000.0

# Minimum valid surface area (square feet)
MIN_SURFACE_AREA_FT2: float = 1.0

# Default ceiling height (feet) when not specified
DEFAULT_CEILING_HEIGHT_FT: float = 10.0

# =============================================================================
# ACOUSTIC ANALYSIS THRESHOLDS
# =============================================================================

# RT60 thresholds for quality assessment (seconds)
RT60_EXCELLENT_MAX: float = 0.5    # Excellent acoustic environment
RT60_GOOD_MAX: float = 0.8         # Good acoustic environment
RT60_ACCEPTABLE_MAX: float = 1.2   # Acceptable acoustic environment
RT60_POOR_MIN: float = 1.5         # Poor acoustic environment

# =============================================================================
# DOORS AND WINDOWS ABSORPTION
# =============================================================================

# Default absorption coefficient for standard glass windows
DEFAULT_GLASS_ABSORPTION: float = 0.04

# Default absorption coefficient for solid wood doors
DEFAULT_WOOD_DOOR_ABSORPTION: float = 0.06

# Default absorption coefficient for hollow core doors
DEFAULT_HOLLOW_DOOR_ABSORPTION: float = 0.10

# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def is_valid_absorption_coefficient(coeff: float) -> bool:
    """Check if absorption coefficient is within valid range"""
    return MIN_ABSORPTION_COEFFICIENT <= coeff <= MAX_ABSORPTION_COEFFICIENT


def is_valid_rt60_value(rt60: float) -> bool:
    """Check if RT60 value is valid (not the sentinel value)"""
    return rt60 > 0 and rt60 < RT60_INVALID_VALUE


def get_target_rt60_for_room_type(room_type: str) -> float:
    """Get target RT60 for a room type, defaulting to general office value"""
    return TARGET_RT60_BY_ROOM_TYPE.get(
        room_type.lower() if room_type else 'default',
        TARGET_RT60_BY_ROOM_TYPE['default']
    )


def calculate_nrc(coefficients: Dict[int, float]) -> float:
    """Calculate NRC from frequency-specific absorption coefficients"""
    nrc_sum = 0.0
    count = 0
    for freq in NRC_FREQUENCIES:
        if freq in coefficients:
            nrc_sum += coefficients[freq]
            count += 1
    return nrc_sum / count if count > 0 else 0.0
