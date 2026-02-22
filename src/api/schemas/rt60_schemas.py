"""
RT60 Calculation Schemas

Request and response dataclasses for RT60 (reverberation time) calculations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any


@dataclass
class SurfaceDefinition:
    """
    Definition of a surface with its material assignment.

    All fields are required for strict validation.
    """
    surface_type: Literal["ceiling", "wall", "floor", "door", "window"]
    material_key: str  # Key from materials database
    area_sq_ft: float

    # Optional: direct absorption coefficients for custom materials
    # If provided, these override the material_key lookup
    custom_coefficients: Optional[Dict[int, float]] = None  # {125: 0.2, 250: 0.3, ...}


@dataclass
class SurfaceAnalysis:
    """
    Analysis of an individual surface's contribution to room absorption.
    """
    surface_type: str
    material_name: str
    material_key: str
    area_sq_ft: float
    nrc: float  # Noise Reduction Coefficient
    absorption_by_frequency: Dict[int, float]  # Absorption in sabins per frequency
    contribution_percentage: float  # Percentage of total absorption


@dataclass
class RT60CalculationRequest:
    """
    Request for RT60 reverberation time calculation.

    All geometry and surface fields are required.
    """
    # Required geometry
    volume_cubic_feet: float
    floor_area_sq_ft: float
    wall_area_sq_ft: float
    ceiling_area_sq_ft: float

    # Required surfaces (must cover all surface area)
    surfaces: List[SurfaceDefinition]

    # Calculation options
    calculation_method: Literal["sabine", "eyring"] = "sabine"
    include_frequency_analysis: bool = True
    debug_mode: bool = False


@dataclass
class RT60CalculationResponse:
    """
    Response from RT60 calculation.
    """
    status: Literal["success", "error", "warning"]

    # Primary results
    rt60_by_frequency: Dict[int, float] = field(default_factory=dict)  # {125: 1.2, ...}
    average_rt60: float = 0.0
    calculation_method: str = ""

    # Detailed breakdown
    total_absorption_by_frequency: Dict[int, float] = field(default_factory=dict)
    surface_analysis: List[SurfaceAnalysis] = field(default_factory=list)

    # Metadata
    total_surface_area_sq_ft: float = 0.0
    average_absorption_coefficient: float = 0.0
    volume_cubic_feet: float = 0.0

    # Warnings and errors
    warnings: List[str] = field(default_factory=list)
    error: Optional[Any] = None  # APIError if status is "error"
    debug_info: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        result = {
            "status": self.status,
            "rt60_by_frequency": self.rt60_by_frequency,
            "average_rt60": self.average_rt60,
            "calculation_method": self.calculation_method,
            "total_absorption_by_frequency": self.total_absorption_by_frequency,
            "surface_analysis": [
                {
                    "surface_type": s.surface_type,
                    "material_name": s.material_name,
                    "material_key": s.material_key,
                    "area_sq_ft": s.area_sq_ft,
                    "nrc": s.nrc,
                    "absorption_by_frequency": s.absorption_by_frequency,
                    "contribution_percentage": s.contribution_percentage,
                }
                for s in self.surface_analysis
            ],
            "total_surface_area_sq_ft": self.total_surface_area_sq_ft,
            "average_absorption_coefficient": self.average_absorption_coefficient,
            "volume_cubic_feet": self.volume_cubic_feet,
            "warnings": self.warnings,
        }
        if self.error:
            result["error"] = self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error
        if self.debug_info:
            result["debug_info"] = self.debug_info
        return result


@dataclass
class FrequencyCompliance:
    """Compliance status for a single frequency band."""
    frequency_hz: int
    current_rt60: float
    target_rt60: float
    tolerance: float
    is_compliant: bool
    deviation: float  # Positive = over target, negative = under


@dataclass
class RT60ComplianceRequest:
    """
    Request for RT60 compliance analysis.
    """
    # RT60 values (from previous calculation or measured)
    rt60_by_frequency: Dict[int, float]

    # Target specification (one of these is required)
    target_rt60: Optional[float] = None
    tolerance: float = 0.1
    room_type: Optional[str] = None  # Uses preset targets


@dataclass
class ComplianceRecommendation:
    """A recommendation for achieving compliance."""
    priority: Literal["critical", "high", "medium", "low"]
    frequency_hz: Optional[int]  # None if general recommendation
    recommendation_type: str  # "increase_absorption", "decrease_absorption", etc.
    message: str


@dataclass
class RT60ComplianceResponse:
    """
    Response from RT60 compliance analysis.
    """
    status: Literal["success", "error"]

    # Overall compliance
    overall_compliance: bool = False

    # Per-frequency compliance
    compliance_by_frequency: Dict[int, FrequencyCompliance] = field(default_factory=dict)

    # Summary
    frequencies_passing: int = 0
    frequencies_failing: int = 0
    compliance_notes: str = ""

    # Target info
    target_rt60: float = 0.0
    tolerance: float = 0.0
    room_type: Optional[str] = None

    # Recommendations if non-compliant
    recommendations: List[ComplianceRecommendation] = field(default_factory=list)

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "overall_compliance": self.overall_compliance,
            "compliance_by_frequency": {
                freq: {
                    "frequency_hz": c.frequency_hz,
                    "current_rt60": c.current_rt60,
                    "target_rt60": c.target_rt60,
                    "tolerance": c.tolerance,
                    "is_compliant": c.is_compliant,
                    "deviation": c.deviation,
                }
                for freq, c in self.compliance_by_frequency.items()
            },
            "frequencies_passing": self.frequencies_passing,
            "frequencies_failing": self.frequencies_failing,
            "compliance_notes": self.compliance_notes,
            "target_rt60": self.target_rt60,
            "tolerance": self.tolerance,
            "room_type": self.room_type,
            "recommendations": [
                {
                    "priority": r.priority,
                    "frequency_hz": r.frequency_hz,
                    "recommendation_type": r.recommendation_type,
                    "message": r.message,
                }
                for r in self.recommendations
            ],
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }


@dataclass
class TreatableSurface:
    """Surface available for acoustic treatment."""
    surface_type: Literal["ceiling", "wall", "floor"]
    available_area_sq_ft: float
    current_material_key: Optional[str] = None


@dataclass
class MaterialSuggestion:
    """A suggested material change."""
    material_key: str
    material_name: str
    category: str
    nrc: float
    absorption_coefficients: Dict[int, float]
    expected_rt60_change: Dict[int, float]  # Per-frequency change (negative = reduction)
    effectiveness_score: float  # 0-100 score


@dataclass
class SurfaceRecommendation:
    """Recommendations for a single surface type."""
    surface_type: str
    current_material: Optional[str]
    available_area_sq_ft: float
    recommended_materials: List[MaterialSuggestion]


@dataclass
class MaterialRecommendationRequest:
    """
    Request for material recommendations to achieve target RT60.
    """
    # Current state
    volume_cubic_feet: float
    current_rt60_by_frequency: Dict[int, float]
    target_rt60: float

    # Surfaces available for treatment
    treatable_surfaces: List[TreatableSurface]

    # Options
    max_recommendations: int = 5
    preferred_categories: Optional[List[str]] = None  # Filter by category


@dataclass
class TreatmentStrategy:
    """A combined treatment strategy using multiple surfaces."""
    strategy_id: str
    strategy_name: str
    changes: List[Dict[str, Any]]  # List of {surface_type, material_key, area}
    expected_average_rt60: float
    expected_rt60_by_frequency: Dict[int, float]
    effectiveness_score: float
    cost_indicator: Literal["low", "medium", "high"]


@dataclass
class MaterialRecommendationResponse:
    """
    Response with material recommendations.
    """
    status: Literal["success", "error", "no_treatment_needed"]

    # Gap analysis
    treatment_needed: bool = False
    current_average_rt60: float = 0.0
    target_rt60: float = 0.0
    absorption_gap_sabins: float = 0.0  # Additional absorption needed

    # Per-surface recommendations
    surface_recommendations: List[SurfaceRecommendation] = field(default_factory=list)

    # Combined strategies
    treatment_strategies: List[TreatmentStrategy] = field(default_factory=list)

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "treatment_needed": self.treatment_needed,
            "current_average_rt60": self.current_average_rt60,
            "target_rt60": self.target_rt60,
            "absorption_gap_sabins": self.absorption_gap_sabins,
            "surface_recommendations": [
                {
                    "surface_type": sr.surface_type,
                    "current_material": sr.current_material,
                    "available_area_sq_ft": sr.available_area_sq_ft,
                    "recommended_materials": [
                        {
                            "material_key": m.material_key,
                            "material_name": m.material_name,
                            "category": m.category,
                            "nrc": m.nrc,
                            "absorption_coefficients": m.absorption_coefficients,
                            "expected_rt60_change": m.expected_rt60_change,
                            "effectiveness_score": m.effectiveness_score,
                        }
                        for m in sr.recommended_materials
                    ],
                }
                for sr in self.surface_recommendations
            ],
            "treatment_strategies": [
                {
                    "strategy_id": ts.strategy_id,
                    "strategy_name": ts.strategy_name,
                    "changes": ts.changes,
                    "expected_average_rt60": ts.expected_average_rt60,
                    "expected_rt60_by_frequency": ts.expected_rt60_by_frequency,
                    "effectiveness_score": ts.effectiveness_score,
                    "cost_indicator": ts.cost_indicator,
                }
                for ts in self.treatment_strategies
            ],
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }
