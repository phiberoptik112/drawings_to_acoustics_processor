"""
Simulation Schemas (What-If Scenarios)

Request and response dataclasses for acoustic simulation endpoints.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any, Union

from src.api.schemas.rt60_schemas import RT60CalculationResponse
from src.api.schemas.hvac_schemas import (
    HVACPathNoiseResponse,
    PathElementInput,
    ReceiverRoomInput,
)


# ============================================================================
# RT60 Material Change Simulation
# ============================================================================

@dataclass
class MaterialChange:
    """Specification for a material change."""
    surface_type: Literal["ceiling", "wall", "floor"]
    original_material_key: str
    new_material_key: str
    area_sq_ft: float  # Area affected by change


@dataclass
class ChangeEffect:
    """Effect of a single material change."""
    surface_type: str
    original_material: str
    new_material: str
    absorption_change_by_frequency: Dict[int, float]  # Per-frequency change in sabins
    rt60_impact_by_frequency: Dict[int, float]  # Per-frequency RT60 change


@dataclass
class RT60MaterialChangeRequest:
    """
    Request for simulating RT60 material changes.

    Uses a baseline RT60 calculation result to simulate the effect
    of changing materials without re-specifying the entire space.
    """
    # Baseline from previous calculation
    baseline_rt60_response: RT60CalculationResponse

    # Original space geometry (needed for recalculation)
    volume_cubic_feet: float
    floor_area_sq_ft: float
    wall_area_sq_ft: float
    ceiling_area_sq_ft: float

    # Changes to simulate
    material_changes: List[MaterialChange]


@dataclass
class RT60MaterialChangeResponse:
    """Response from RT60 material change simulation."""
    status: Literal["success", "error"]

    # Comparison
    baseline_rt60_by_frequency: Dict[int, float] = field(default_factory=dict)
    simulated_rt60_by_frequency: Dict[int, float] = field(default_factory=dict)
    delta_rt60_by_frequency: Dict[int, float] = field(default_factory=dict)  # Positive = increased RT60

    # Summary
    baseline_average_rt60: float = 0.0
    simulated_average_rt60: float = 0.0
    improvement_percentage: float = 0.0  # Negative = worse

    # Per-change breakdown
    change_effects: List[ChangeEffect] = field(default_factory=list)

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "baseline_rt60_by_frequency": self.baseline_rt60_by_frequency,
            "simulated_rt60_by_frequency": self.simulated_rt60_by_frequency,
            "delta_rt60_by_frequency": self.delta_rt60_by_frequency,
            "baseline_average_rt60": self.baseline_average_rt60,
            "simulated_average_rt60": self.simulated_average_rt60,
            "improvement_percentage": self.improvement_percentage,
            "change_effects": [
                {
                    "surface_type": ce.surface_type,
                    "original_material": ce.original_material,
                    "new_material": ce.new_material,
                    "absorption_change_by_frequency": ce.absorption_change_by_frequency,
                    "rt60_impact_by_frequency": ce.rt60_impact_by_frequency,
                }
                for ce in self.change_effects
            ],
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }


# ============================================================================
# HVAC Path Modification Simulation
# ============================================================================

@dataclass
class ElementModification:
    """Specification for modifying an existing path element."""
    element_id: str

    # Properties to change (None = keep original)
    new_lining_thickness_inches: Optional[float] = None
    new_width_inches: Optional[float] = None
    new_height_inches: Optional[float] = None
    new_diameter_inches: Optional[float] = None
    new_length_ft: Optional[float] = None
    add_turning_vanes: Optional[bool] = None
    new_flow_rate_cfm: Optional[float] = None


@dataclass
class ElementModificationEffect:
    """Effect of modifying a single element."""
    element_id: str
    modification_description: str
    attenuation_change_by_frequency: Dict[int, float]
    overall_impact_dba: float


@dataclass
class HVACPathModificationRequest:
    """
    Request for simulating HVAC path modifications.

    Uses a baseline path calculation to simulate the effect
    of modifying duct properties.
    """
    # Baseline from previous calculation
    baseline_path_response: HVACPathNoiseResponse

    # Original path elements (needed for recalculation)
    original_path_elements: List[PathElementInput]

    # Receiver room (if applicable)
    receiver_room: Optional[ReceiverRoomInput] = None

    # Modifications by element_id
    element_modifications: List[ElementModification] = field(default_factory=list)


@dataclass
class HVACPathModificationResponse:
    """Response from HVAC path modification simulation."""
    status: Literal["success", "error"]

    # Comparison
    baseline_terminal_noise_dba: float = 0.0
    simulated_terminal_noise_dba: float = 0.0
    noise_reduction_dba: float = 0.0  # Positive = quieter

    baseline_nc_rating: int = 0
    simulated_nc_rating: int = 0
    nc_improvement: int = 0  # Positive = better (lower NC)

    # Spectrum comparison
    baseline_spectrum: Dict[int, float] = field(default_factory=dict)
    simulated_spectrum: Dict[int, float] = field(default_factory=dict)
    delta_spectrum: Dict[int, float] = field(default_factory=dict)

    # Per-element effects
    element_effects: List[ElementModificationEffect] = field(default_factory=list)

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "baseline_terminal_noise_dba": self.baseline_terminal_noise_dba,
            "simulated_terminal_noise_dba": self.simulated_terminal_noise_dba,
            "noise_reduction_dba": self.noise_reduction_dba,
            "baseline_nc_rating": self.baseline_nc_rating,
            "simulated_nc_rating": self.simulated_nc_rating,
            "nc_improvement": self.nc_improvement,
            "baseline_spectrum": self.baseline_spectrum,
            "simulated_spectrum": self.simulated_spectrum,
            "delta_spectrum": self.delta_spectrum,
            "element_effects": [
                {
                    "element_id": ee.element_id,
                    "modification_description": ee.modification_description,
                    "attenuation_change_by_frequency": ee.attenuation_change_by_frequency,
                    "overall_impact_dba": ee.overall_impact_dba,
                }
                for ee in self.element_effects
            ],
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }


# ============================================================================
# Path Element Add/Remove Simulation
# ============================================================================

@dataclass
class ElementInsertion:
    """Specification for adding a new element to a path."""
    new_element: PathElementInput
    insert_after_element_id: str  # Position in path


@dataclass
class PathElementChangeRequest:
    """
    Request for simulating adding/removing path elements.

    Useful for testing silencer insertion, elbow removal, etc.
    """
    # Original path elements
    original_path_elements: List[PathElementInput]

    # Receiver room
    receiver_room: Optional[ReceiverRoomInput] = None

    # Changes
    elements_to_add: List[ElementInsertion] = field(default_factory=list)
    elements_to_remove: List[str] = field(default_factory=list)  # element_ids


# Response is same as HVACPathModificationResponse


# ============================================================================
# Multi-Scenario Comparison
# ============================================================================

@dataclass
class ScenarioDefinition:
    """Definition of a what-if scenario."""
    scenario_id: str
    scenario_name: str
    changes: Union[List[MaterialChange], List[ElementModification]]


@dataclass
class ScenarioResult:
    """Result of a single scenario."""
    scenario_id: str
    scenario_name: str
    result: Union[RT60MaterialChangeResponse, HVACPathModificationResponse]
    improvement_score: float  # Normalized 0-100
    cost_indicator: Literal["low", "medium", "high"]


@dataclass
class ScenarioComparisonRequest:
    """
    Request for comparing multiple what-if scenarios side-by-side.
    """
    scenario_type: Literal["rt60", "hvac"]

    # Baseline (from previous calculation)
    baseline: Union[RT60CalculationResponse, HVACPathNoiseResponse]

    # For RT60 scenarios
    volume_cubic_feet: Optional[float] = None
    floor_area_sq_ft: Optional[float] = None
    wall_area_sq_ft: Optional[float] = None
    ceiling_area_sq_ft: Optional[float] = None

    # For HVAC scenarios
    original_path_elements: Optional[List[PathElementInput]] = None
    receiver_room: Optional[ReceiverRoomInput] = None

    # Scenarios to compare
    scenarios: List[ScenarioDefinition] = field(default_factory=list)


@dataclass
class ScenarioComparisonResponse:
    """Response from multi-scenario comparison."""
    status: Literal["success", "error"]

    # Baseline summary
    baseline_summary: Dict[str, Any] = field(default_factory=dict)

    # Results per scenario
    scenario_results: List[ScenarioResult] = field(default_factory=list)

    # Analysis
    recommended_scenario_id: Optional[str] = None  # Best improvement
    comparison_matrix: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Error
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "status": self.status,
            "baseline_summary": self.baseline_summary,
            "scenario_results": [
                {
                    "scenario_id": sr.scenario_id,
                    "scenario_name": sr.scenario_name,
                    "result": sr.result.to_dict() if hasattr(sr.result, 'to_dict') else sr.result,
                    "improvement_score": sr.improvement_score,
                    "cost_indicator": sr.cost_indicator,
                }
                for sr in self.scenario_results
            ],
            "recommended_scenario_id": self.recommended_scenario_id,
            "comparison_matrix": self.comparison_matrix,
            "error": self.error.to_dict() if hasattr(self.error, 'to_dict') else self.error,
        }
