"""
HVAC Noise Calculation Schemas

Request and response dataclasses for HVAC path noise calculations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any


@dataclass
class PathElementInput:
    """
    Input specification for an HVAC path element.

    Required fields depend on element_type:
    - source: source_noise_dba OR source_octave_bands
    - duct: length_ft, duct_shape, dimensions, duct_type, lining_thickness_inches, flow_rate_cfm
    - elbow: fitting_type, dimensions, has_turning_vanes
    - junction: fitting_type, dimensions
    - flex_duct: length_ft, diameter_inches
    - terminal: (no additional required fields)
    """
    element_type: Literal["source", "duct", "elbow", "junction", "flex_duct", "terminal"]
    element_id: str

    # Source properties (required for element_type="source")
    source_noise_dba: Optional[float] = None
    source_octave_bands: Optional[Dict[int, float]] = None  # {63: 55, 125: 52, ...}

    # Duct properties (required for element_type="duct" or "flex_duct")
    length_ft: Optional[float] = None
    duct_shape: Optional[Literal["rectangular", "circular"]] = None
    width_inches: Optional[float] = None   # For rectangular
    height_inches: Optional[float] = None  # For rectangular
    diameter_inches: Optional[float] = None  # For circular
    duct_type: Optional[Literal["sheet_metal", "fiberglass", "flexible"]] = None
    lining_thickness_inches: Optional[float] = None
    flow_rate_cfm: Optional[float] = None
    flow_velocity_fpm: Optional[float] = None

    # Fitting properties (required for element_type="elbow" or "junction")
    fitting_type: Optional[str] = None  # "elbow_90", "elbow_45", "tee_branch", "x_junction", etc.
    has_turning_vanes: Optional[bool] = None
    vane_chord_length_inches: Optional[float] = None
    num_vanes: Optional[int] = None

    # Pressure properties (optional)
    pressure_drop_in_wg: Optional[float] = None


@dataclass
class ReceiverRoomInput:
    """
    Receiver room parameters for room correction calculations.

    All fields are required for room correction.
    """
    room_volume_cubic_ft: float
    room_absorption_sabins: float
    distance_from_terminal_ft: float = 5.0
    termination_type: Literal["flush", "free"] = "flush"


@dataclass
class ElementResult:
    """Result for a single path element."""
    element_id: str
    element_type: str
    element_order: int

    # Noise levels
    noise_before_dba: float
    noise_after_dba: float

    # Attenuation/generation by frequency
    attenuation_spectrum: Dict[int, float]  # Positive = attenuation
    generated_noise_spectrum: Dict[int, float]  # Noise added by element

    # NC tracking
    nc_before: int
    nc_after: int


@dataclass
class HVACPathNoiseRequest:
    """
    Request for HVAC path noise calculation.

    Path elements must be ordered from source to terminal.
    First element must be type "source".
    """
    path_id: str = "path_1"
    path_elements: List[PathElementInput] = field(default_factory=list)
    receiver_room: Optional[ReceiverRoomInput] = None
    debug_mode: bool = False
    include_element_breakdown: bool = True


@dataclass
class HVACPathNoiseResponse:
    """Response from HVAC path noise calculation."""
    status: Literal["success", "error", "warning"]

    # Primary results
    path_id: str = ""
    source_noise_dba: float = 0.0
    terminal_noise_dba: float = 0.0
    total_attenuation_dba: float = 0.0
    nc_rating: int = 0

    # Octave band spectrum at terminal (8 bands)
    terminal_spectrum: Dict[int, float] = field(default_factory=dict)

    # Per-element breakdown (if requested)
    element_results: Optional[List[ElementResult]] = None

    # Validation
    calculation_valid: bool = True

    # Warnings and errors
    warnings: List[str] = field(default_factory=list)
    error: Optional[Any] = None
    debug_log: Optional[List[Dict]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        result = {
            "status": self.status,
            "path_id": self.path_id,
            "source_noise_dba": self.source_noise_dba,
            "terminal_noise_dba": self.terminal_noise_dba,
            "total_attenuation_dba": self.total_attenuation_dba,
            "nc_rating": self.nc_rating,
            "terminal_spectrum": self.terminal_spectrum,
            "calculation_valid": self.calculation_valid,
            "warnings": self.warnings,
        }
        if self.element_results:
            result["element_results"] = [
                {
                    "element_id": er.element_id,
                    "element_type": er.element_type,
                    "element_order": er.element_order,
                    "noise_before_dba": er.noise_before_dba,
                    "noise_after_dba": er.noise_after_dba,
                    "attenuation_spectrum": er.attenuation_spectrum,
                    "generated_noise_spectrum": er.generated_noise_spectrum,
                    "nc_before": er.nc_before,
                    "nc_after": er.nc_after,
                }
                for er in self.element_results
            ]
        if self.error:
            result["error"] = self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error
        if self.debug_log:
            result["debug_log"] = self.debug_log
        return result


@dataclass
class PathContribution:
    """Contribution of a single path to combined receiver noise."""
    path_id: str
    noise_dba: float
    contribution_percentage: float  # Percentage of total energy


@dataclass
class CombinedReceiverNoiseRequest:
    """
    Request for combining multiple HVAC path results at a single receiver.

    Used when a space has multiple supply/return paths.
    """
    receiver_space_id: str
    path_results: List[HVACPathNoiseResponse]  # Results from calculate_path_noise()

    # Receiver room parameters
    room_volume_cubic_ft: float
    room_absorption_sabins: float


@dataclass
class CombinedReceiverNoiseResponse:
    """Response from combined receiver noise calculation."""
    status: Literal["success", "error"]

    # Combined results
    combined_spectrum: Dict[int, float] = field(default_factory=dict)  # Log-sum of all paths
    combined_noise_dba: float = 0.0
    combined_nc_rating: int = 0

    # Path contributions
    path_contributions: List[PathContribution] = field(default_factory=list)
    dominant_path_id: str = ""  # Path contributing most noise
    num_paths_combined: int = 0

    # Warnings and errors
    warnings: List[str] = field(default_factory=list)
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "combined_spectrum": self.combined_spectrum,
            "combined_noise_dba": self.combined_noise_dba,
            "combined_nc_rating": self.combined_nc_rating,
            "path_contributions": [
                {
                    "path_id": pc.path_id,
                    "noise_dba": pc.noise_dba,
                    "contribution_percentage": pc.contribution_percentage,
                }
                for pc in self.path_contributions
            ],
            "dominant_path_id": self.dominant_path_id,
            "num_paths_combined": self.num_paths_combined,
            "warnings": self.warnings,
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }


@dataclass
class FrequencyExceedance:
    """NC curve exceedance at a frequency."""
    frequency_hz: int
    measured_level_db: float
    nc_curve_limit_db: float
    exceedance_db: float


@dataclass
class NCComplianceRequest:
    """
    Request for NC compliance analysis.

    Provide either octave_band_levels or dba_level.
    """
    # Noise data (from path calculation or measured)
    octave_band_levels: Optional[Dict[int, float]] = None  # {63: 35, 125: 38, ...}
    dba_level: Optional[float] = None  # Alternative: estimate from dB(A)

    # Target criteria (at least one required)
    target_nc: Optional[int] = None
    space_type: Optional[str] = None  # "private_office", "classroom", etc.


@dataclass
class NCComplianceResponse:
    """Response from NC compliance analysis."""
    status: Literal["success", "error"]

    # Determined NC rating
    nc_rating: int = 0
    overall_dba: float = 0.0

    # Compliance assessment
    meets_criteria: bool = False
    target_nc: int = 0
    recommended_nc: int = 0  # For space type
    maximum_nc: int = 0  # For space type

    # Per-frequency analysis
    exceedances: List[FrequencyExceedance] = field(default_factory=list)

    # Recommendations
    compliance_status: Literal["Excellent", "Acceptable", "Non-compliant"] = "Non-compliant"
    improvement_needed_nc_points: int = 0
    noise_control_recommendations: List[str] = field(default_factory=list)

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "nc_rating": self.nc_rating,
            "overall_dba": self.overall_dba,
            "meets_criteria": self.meets_criteria,
            "target_nc": self.target_nc,
            "recommended_nc": self.recommended_nc,
            "maximum_nc": self.maximum_nc,
            "exceedances": [
                {
                    "frequency_hz": e.frequency_hz,
                    "measured_level_db": e.measured_level_db,
                    "nc_curve_limit_db": e.nc_curve_limit_db,
                    "exceedance_db": e.exceedance_db,
                }
                for e in self.exceedances
            ],
            "compliance_status": self.compliance_status,
            "improvement_needed_nc_points": self.improvement_needed_nc_points,
            "noise_control_recommendations": self.noise_control_recommendations,
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }


@dataclass
class ElementAttenuationRequest:
    """
    Request for single element attenuation calculation.

    Useful for what-if analysis of individual components.
    """
    element_type: Literal["duct", "elbow", "flex_duct"]

    # Duct properties
    length_ft: float
    duct_shape: Literal["rectangular", "circular"]
    width_inches: Optional[float] = None
    height_inches: Optional[float] = None
    diameter_inches: Optional[float] = None
    duct_type: Literal["sheet_metal", "fiberglass"] = "sheet_metal"
    lining_thickness_inches: float = 0.0

    # Flow (for generated noise)
    flow_rate_cfm: Optional[float] = None


@dataclass
class ElementAttenuationResponse:
    """Response with element attenuation data."""
    status: Literal["success", "error"]

    # Attenuation by frequency
    attenuation_spectrum: Dict[int, float] = field(default_factory=dict)  # dB attenuation per frequency
    total_attenuation_dba: float = 0.0

    # Generated noise (if applicable)
    generated_noise_spectrum: Optional[Dict[int, float]] = None
    generated_noise_dba: Optional[float] = None

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        result = {
            "status": self.status,
            "attenuation_spectrum": self.attenuation_spectrum,
            "total_attenuation_dba": self.total_attenuation_dba,
        }
        if self.generated_noise_spectrum:
            result["generated_noise_spectrum"] = self.generated_noise_spectrum
        if self.generated_noise_dba is not None:
            result["generated_noise_dba"] = self.generated_noise_dba
        if self.error:
            result["error"] = self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error
        return result
