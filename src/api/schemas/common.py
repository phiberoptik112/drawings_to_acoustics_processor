"""
Common Schema Definitions

Shared types, constants, and base classes used across the API.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any
from enum import Enum


# Octave band frequency constants
OCTAVE_BANDS_6 = (125, 250, 500, 1000, 2000, 4000)  # RT60 frequencies
OCTAVE_BANDS_8 = (63, 125, 250, 500, 1000, 2000, 4000, 8000)  # HVAC/NC frequencies

# Surface types
SURFACE_TYPES = Literal["ceiling", "wall", "floor", "door", "window"]

# Duct shapes
DUCT_SHAPES = Literal["rectangular", "circular"]

# Duct types
DUCT_TYPES = Literal["sheet_metal", "fiberglass", "flexible"]

# Element types
ELEMENT_TYPES = Literal["source", "duct", "elbow", "junction", "flex_duct", "terminal"]

# Calculation methods
CALCULATION_METHODS = Literal["sabine", "eyring"]

# Room types for compliance checking
ROOM_TYPES = Literal[
    "conference",
    "classroom",
    "office_private",
    "office_open",
    "auditorium",
    "worship",
    "restaurant",
    "healthcare_patient",
    "healthcare_public",
    "residential",
    "custom"
]


class StatusEnum(str, Enum):
    """API response status"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class OctaveBandData6:
    """6-band octave data for RT60 calculations (125Hz - 4000Hz)"""
    freq_125: float = 0.0
    freq_250: float = 0.0
    freq_500: float = 0.0
    freq_1000: float = 0.0
    freq_2000: float = 0.0
    freq_4000: float = 0.0

    def to_dict(self) -> Dict[int, float]:
        """Convert to frequency-keyed dictionary"""
        return {
            125: self.freq_125,
            250: self.freq_250,
            500: self.freq_500,
            1000: self.freq_1000,
            2000: self.freq_2000,
            4000: self.freq_4000,
        }

    @classmethod
    def from_dict(cls, data: Dict[int, float]) -> "OctaveBandData6":
        """Create from frequency-keyed dictionary"""
        return cls(
            freq_125=data.get(125, 0.0),
            freq_250=data.get(250, 0.0),
            freq_500=data.get(500, 0.0),
            freq_1000=data.get(1000, 0.0),
            freq_2000=data.get(2000, 0.0),
            freq_4000=data.get(4000, 0.0),
        )


@dataclass
class OctaveBandData8:
    """8-band octave data for HVAC/NC calculations (63Hz - 8000Hz)"""
    freq_63: float = 0.0
    freq_125: float = 0.0
    freq_250: float = 0.0
    freq_500: float = 0.0
    freq_1000: float = 0.0
    freq_2000: float = 0.0
    freq_4000: float = 0.0
    freq_8000: float = 0.0

    def to_dict(self) -> Dict[int, float]:
        """Convert to frequency-keyed dictionary"""
        return {
            63: self.freq_63,
            125: self.freq_125,
            250: self.freq_250,
            500: self.freq_500,
            1000: self.freq_1000,
            2000: self.freq_2000,
            4000: self.freq_4000,
            8000: self.freq_8000,
        }

    def to_list(self) -> List[float]:
        """Convert to ordered list"""
        return [
            self.freq_63, self.freq_125, self.freq_250, self.freq_500,
            self.freq_1000, self.freq_2000, self.freq_4000, self.freq_8000
        ]

    @classmethod
    def from_dict(cls, data: Dict[int, float]) -> "OctaveBandData8":
        """Create from frequency-keyed dictionary"""
        return cls(
            freq_63=data.get(63, 0.0),
            freq_125=data.get(125, 0.0),
            freq_250=data.get(250, 0.0),
            freq_500=data.get(500, 0.0),
            freq_1000=data.get(1000, 0.0),
            freq_2000=data.get(2000, 0.0),
            freq_4000=data.get(4000, 0.0),
            freq_8000=data.get(8000, 0.0),
        )

    @classmethod
    def from_list(cls, data: List[float]) -> "OctaveBandData8":
        """Create from ordered list [63, 125, 250, 500, 1000, 2000, 4000, 8000]"""
        if len(data) != 8:
            raise ValueError(f"Expected 8 values, got {len(data)}")
        return cls(
            freq_63=data[0],
            freq_125=data[1],
            freq_250=data[2],
            freq_500=data[3],
            freq_1000=data[4],
            freq_2000=data[5],
            freq_4000=data[6],
            freq_8000=data[7],
        )


@dataclass
class ValidationError:
    """Single field validation error"""
    field_path: str
    error_message: str
    expected_type: Optional[str] = None
    actual_value: Optional[Any] = None


@dataclass
class APIError:
    """
    Standardized API error response.

    For strict validation, all errors include:
    - error_code: Machine-readable code for programmatic handling
    - error_message: Human-readable description
    - field_errors: Specific errors by field path
    - missing_fields: List of required fields that were not provided
    - suggestion: How to fix the error
    """
    error_code: str
    error_message: str
    field_errors: Dict[str, str] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "field_errors": self.field_errors,
            "missing_fields": self.missing_fields,
            "suggestion": self.suggestion,
        }


# Error codes
class ErrorCode:
    """Standard API error codes"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELDS = "MISSING_REQUIRED_FIELDS"
    INVALID_VALUE = "INVALID_VALUE"
    MATERIAL_NOT_FOUND = "MATERIAL_NOT_FOUND"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    INVALID_FREQUENCY = "INVALID_FREQUENCY"
    CALCULATION_ERROR = "CALCULATION_ERROR"
    PATH_INVALID = "PATH_INVALID"
    NO_SOURCE_ELEMENT = "NO_SOURCE_ELEMENT"
    INCOMPATIBLE_BASELINE = "INCOMPATIBLE_BASELINE"


# Room type target RT60 values (seconds)
ROOM_TYPE_TARGETS = {
    "conference": {"target_rt60": 0.6, "tolerance": 0.1, "description": "Conference room"},
    "classroom": {"target_rt60": 0.6, "tolerance": 0.1, "description": "Classroom"},
    "office_private": {"target_rt60": 0.6, "tolerance": 0.15, "description": "Private office"},
    "office_open": {"target_rt60": 0.5, "tolerance": 0.1, "description": "Open office"},
    "auditorium": {"target_rt60": 1.2, "tolerance": 0.2, "description": "Auditorium/lecture hall"},
    "worship": {"target_rt60": 1.5, "tolerance": 0.3, "description": "Place of worship"},
    "restaurant": {"target_rt60": 0.7, "tolerance": 0.15, "description": "Restaurant"},
    "healthcare_patient": {"target_rt60": 0.6, "tolerance": 0.1, "description": "Healthcare patient room"},
    "healthcare_public": {"target_rt60": 0.8, "tolerance": 0.15, "description": "Healthcare public area"},
    "residential": {"target_rt60": 0.5, "tolerance": 0.1, "description": "Residential"},
}

# Space type NC rating targets
SPACE_TYPE_NC_TARGETS = {
    "private_office": {"recommended": 30, "maximum": 40},
    "conference_room": {"recommended": 25, "maximum": 35},
    "classroom": {"recommended": 25, "maximum": 30},
    "open_office": {"recommended": 35, "maximum": 45},
    "library": {"recommended": 30, "maximum": 35},
    "auditorium": {"recommended": 20, "maximum": 25},
    "theater": {"recommended": 20, "maximum": 25},
    "hospital_patient": {"recommended": 25, "maximum": 35},
    "hospital_operating": {"recommended": 25, "maximum": 30},
    "residence": {"recommended": 30, "maximum": 40},
    "restaurant": {"recommended": 40, "maximum": 50},
    "retail": {"recommended": 40, "maximum": 50},
    "warehouse": {"recommended": 50, "maximum": 65},
}
