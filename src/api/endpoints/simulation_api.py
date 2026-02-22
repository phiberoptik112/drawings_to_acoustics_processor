"""
Simulation Service (What-If Scenarios)

API service for simulating acoustic changes before applying them.
"""

from typing import Dict, List, Optional, Any
from copy import deepcopy

from src.api.schemas.common import OCTAVE_BANDS_6, OCTAVE_BANDS_8, APIError, ErrorCode
from src.api.schemas.rt60_schemas import (
    RT60CalculationRequest,
    RT60CalculationResponse,
    SurfaceDefinition,
)
from src.api.schemas.hvac_schemas import (
    HVACPathNoiseRequest,
    HVACPathNoiseResponse,
    PathElementInput,
)
from src.api.schemas.simulation_schemas import (
    MaterialChange,
    RT60MaterialChangeRequest,
    RT60MaterialChangeResponse,
    ChangeEffect,
    ElementModification,
    HVACPathModificationRequest,
    HVACPathModificationResponse,
    ElementModificationEffect,
    PathElementChangeRequest,
    ElementInsertion,
    ScenarioDefinition,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    ScenarioResult,
)
from src.api.endpoints.rt60_api import RT60CalculationService
from src.api.endpoints.hvac_api import HVACNoiseService


class SimulationService:
    """
    Simulation service for what-if acoustic analysis.

    Provides endpoints for testing changes before implementing:
    - RT60 material changes
    - HVAC path modifications
    - Path element additions/removals
    - Multi-scenario comparisons

    All methods are stateless and produce comparison results.
    """

    def __init__(self):
        """Initialize the simulation service."""
        self._rt60_service = None
        self._hvac_service = None

    def _get_rt60_service(self) -> RT60CalculationService:
        """Lazy load RT60 service."""
        if self._rt60_service is None:
            self._rt60_service = RT60CalculationService()
        return self._rt60_service

    def _get_hvac_service(self) -> HVACNoiseService:
        """Lazy load HVAC service."""
        if self._hvac_service is None:
            self._hvac_service = HVACNoiseService()
        return self._hvac_service

    def simulate_rt60_material_change(
        self,
        request: RT60MaterialChangeRequest
    ) -> RT60MaterialChangeResponse:
        """
        Simulate the effect of changing materials on RT60.

        Args:
            request: Material change request with baseline and changes

        Returns:
            RT60MaterialChangeResponse with comparison results
        """
        try:
            # Validate baseline
            if request.baseline_rt60_response.status == "error":
                return RT60MaterialChangeResponse(
                    status="error",
                    error=APIError(
                        error_code=ErrorCode.INCOMPATIBLE_BASELINE,
                        error_message="Baseline RT60 response has error status",
                        suggestion="Provide a successful baseline calculation"
                    )
                )

            # Build modified surfaces from baseline
            baseline_surfaces = []
            for surface in request.baseline_rt60_response.surface_analysis:
                baseline_surfaces.append(SurfaceDefinition(
                    surface_type=surface.surface_type,
                    material_key=surface.material_key,
                    area_sq_ft=surface.area_sq_ft,
                ))

            # Apply material changes
            modified_surfaces = deepcopy(baseline_surfaces)
            change_effects = []

            for change in request.material_changes:
                # Find and modify the surface
                for i, surface in enumerate(modified_surfaces):
                    if (surface.surface_type == change.surface_type and
                        surface.material_key == change.original_material_key):
                        modified_surfaces[i] = SurfaceDefinition(
                            surface_type=change.surface_type,
                            material_key=change.new_material_key,
                            area_sq_ft=change.area_sq_ft,
                        )
                        break

            # Calculate RT60 with modified surfaces
            rt60_service = self._get_rt60_service()
            simulated_request = RT60CalculationRequest(
                volume_cubic_feet=request.volume_cubic_feet,
                floor_area_sq_ft=request.floor_area_sq_ft,
                wall_area_sq_ft=request.wall_area_sq_ft,
                ceiling_area_sq_ft=request.ceiling_area_sq_ft,
                surfaces=modified_surfaces,
                calculation_method=request.baseline_rt60_response.calculation_method or "sabine",
            )

            simulated_response = rt60_service.calculate_rt60(simulated_request)

            if simulated_response.status == "error":
                return RT60MaterialChangeResponse(
                    status="error",
                    error=simulated_response.error
                )

            # Calculate deltas
            baseline_rt60 = request.baseline_rt60_response.rt60_by_frequency
            simulated_rt60 = simulated_response.rt60_by_frequency

            delta_rt60 = {}
            for freq in OCTAVE_BANDS_6:
                delta_rt60[freq] = round(
                    simulated_rt60.get(freq, 0) - baseline_rt60.get(freq, 0),
                    3
                )

            baseline_avg = request.baseline_rt60_response.average_rt60
            simulated_avg = simulated_response.average_rt60

            improvement_pct = 0.0
            if baseline_avg > 0:
                improvement_pct = round((baseline_avg - simulated_avg) / baseline_avg * 100, 1)

            # Build change effects
            for change in request.material_changes:
                change_effects.append(ChangeEffect(
                    surface_type=change.surface_type,
                    original_material=change.original_material_key,
                    new_material=change.new_material_key,
                    absorption_change_by_frequency={},  # Would need detailed calc
                    rt60_impact_by_frequency=delta_rt60,
                ))

            return RT60MaterialChangeResponse(
                status="success",
                baseline_rt60_by_frequency=baseline_rt60,
                simulated_rt60_by_frequency=simulated_rt60,
                delta_rt60_by_frequency=delta_rt60,
                baseline_average_rt60=baseline_avg,
                simulated_average_rt60=simulated_avg,
                improvement_percentage=improvement_pct,
                change_effects=change_effects,
            )

        except Exception as e:
            return RT60MaterialChangeResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"RT60 simulation failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def simulate_hvac_path_modification(
        self,
        request: HVACPathModificationRequest
    ) -> HVACPathModificationResponse:
        """
        Simulate the effect of modifying HVAC path elements.

        Args:
            request: Path modification request with baseline and changes

        Returns:
            HVACPathModificationResponse with comparison results
        """
        try:
            # Validate baseline
            if request.baseline_path_response.status == "error":
                return HVACPathModificationResponse(
                    status="error",
                    error=APIError(
                        error_code=ErrorCode.INCOMPATIBLE_BASELINE,
                        error_message="Baseline path response has error status",
                        suggestion="Provide a successful baseline calculation"
                    )
                )

            # Apply modifications to path elements
            modified_elements = deepcopy(request.original_path_elements)

            for mod in request.element_modifications:
                for i, elem in enumerate(modified_elements):
                    if elem.element_id == mod.element_id:
                        # Apply modifications
                        if mod.new_lining_thickness_inches is not None:
                            modified_elements[i].lining_thickness_inches = mod.new_lining_thickness_inches
                        if mod.new_width_inches is not None:
                            modified_elements[i].width_inches = mod.new_width_inches
                        if mod.new_height_inches is not None:
                            modified_elements[i].height_inches = mod.new_height_inches
                        if mod.new_diameter_inches is not None:
                            modified_elements[i].diameter_inches = mod.new_diameter_inches
                        if mod.new_length_ft is not None:
                            modified_elements[i].length_ft = mod.new_length_ft
                        if mod.add_turning_vanes is not None:
                            modified_elements[i].has_turning_vanes = mod.add_turning_vanes
                        if mod.new_flow_rate_cfm is not None:
                            modified_elements[i].flow_rate_cfm = mod.new_flow_rate_cfm
                        break

            # Calculate with modified elements
            hvac_service = self._get_hvac_service()
            simulated_request = HVACPathNoiseRequest(
                path_id=request.baseline_path_response.path_id + "_simulated",
                path_elements=modified_elements,
                receiver_room=request.receiver_room,
            )

            simulated_response = hvac_service.calculate_path_noise(simulated_request)

            if simulated_response.status == "error":
                return HVACPathModificationResponse(
                    status="error",
                    error=simulated_response.error
                )

            # Calculate deltas
            baseline_spectrum = request.baseline_path_response.terminal_spectrum
            simulated_spectrum = simulated_response.terminal_spectrum

            delta_spectrum = {}
            for freq in OCTAVE_BANDS_8:
                delta_spectrum[freq] = round(
                    simulated_spectrum.get(freq, 0) - baseline_spectrum.get(freq, 0),
                    1
                )

            noise_reduction = round(
                request.baseline_path_response.terminal_noise_dba - simulated_response.terminal_noise_dba,
                1
            )
            nc_improvement = request.baseline_path_response.nc_rating - simulated_response.nc_rating

            # Build element effects
            element_effects = []
            for mod in request.element_modifications:
                desc_parts = []
                if mod.new_lining_thickness_inches is not None:
                    desc_parts.append(f"lining: {mod.new_lining_thickness_inches}\"")
                if mod.new_width_inches is not None:
                    desc_parts.append(f"width: {mod.new_width_inches}\"")
                if mod.new_height_inches is not None:
                    desc_parts.append(f"height: {mod.new_height_inches}\"")
                if mod.add_turning_vanes:
                    desc_parts.append("added turning vanes")

                element_effects.append(ElementModificationEffect(
                    element_id=mod.element_id,
                    modification_description=", ".join(desc_parts) or "no changes",
                    attenuation_change_by_frequency={},  # Would need detailed calc
                    overall_impact_dba=noise_reduction,
                ))

            return HVACPathModificationResponse(
                status="success",
                baseline_terminal_noise_dba=request.baseline_path_response.terminal_noise_dba,
                simulated_terminal_noise_dba=simulated_response.terminal_noise_dba,
                noise_reduction_dba=noise_reduction,
                baseline_nc_rating=request.baseline_path_response.nc_rating,
                simulated_nc_rating=simulated_response.nc_rating,
                nc_improvement=nc_improvement,
                baseline_spectrum=baseline_spectrum,
                simulated_spectrum=simulated_spectrum,
                delta_spectrum=delta_spectrum,
                element_effects=element_effects,
            )

        except Exception as e:
            return HVACPathModificationResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"HVAC path simulation failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def simulate_path_element_change(
        self,
        request: PathElementChangeRequest
    ) -> HVACPathModificationResponse:
        """
        Simulate adding or removing path elements.

        Args:
            request: Path element change request

        Returns:
            HVACPathModificationResponse with comparison results
        """
        try:
            # Calculate baseline
            hvac_service = self._get_hvac_service()
            baseline_request = HVACPathNoiseRequest(
                path_id="baseline",
                path_elements=request.original_path_elements,
                receiver_room=request.receiver_room,
            )
            baseline_response = hvac_service.calculate_path_noise(baseline_request)

            if baseline_response.status == "error":
                return HVACPathModificationResponse(
                    status="error",
                    error=baseline_response.error
                )

            # Build modified element list
            modified_elements = deepcopy(request.original_path_elements)

            # Remove elements
            modified_elements = [
                e for e in modified_elements
                if e.element_id not in request.elements_to_remove
            ]

            # Add elements
            for insertion in request.elements_to_add:
                insert_idx = None
                for i, elem in enumerate(modified_elements):
                    if elem.element_id == insertion.insert_after_element_id:
                        insert_idx = i + 1
                        break
                if insert_idx is not None:
                    modified_elements.insert(insert_idx, insertion.new_element)
                else:
                    # Append to end if insert point not found
                    modified_elements.append(insertion.new_element)

            # Calculate with modified elements
            simulated_request = HVACPathNoiseRequest(
                path_id="simulated",
                path_elements=modified_elements,
                receiver_room=request.receiver_room,
            )
            simulated_response = hvac_service.calculate_path_noise(simulated_request)

            if simulated_response.status == "error":
                return HVACPathModificationResponse(
                    status="error",
                    error=simulated_response.error
                )

            # Calculate deltas
            baseline_spectrum = baseline_response.terminal_spectrum
            simulated_spectrum = simulated_response.terminal_spectrum

            delta_spectrum = {}
            for freq in OCTAVE_BANDS_8:
                delta_spectrum[freq] = round(
                    simulated_spectrum.get(freq, 0) - baseline_spectrum.get(freq, 0),
                    1
                )

            noise_reduction = round(
                baseline_response.terminal_noise_dba - simulated_response.terminal_noise_dba,
                1
            )
            nc_improvement = baseline_response.nc_rating - simulated_response.nc_rating

            # Build element effects
            element_effects = []
            for removal_id in request.elements_to_remove:
                element_effects.append(ElementModificationEffect(
                    element_id=removal_id,
                    modification_description="element removed",
                    attenuation_change_by_frequency={},
                    overall_impact_dba=noise_reduction / max(1, len(request.elements_to_remove)),
                ))
            for insertion in request.elements_to_add:
                element_effects.append(ElementModificationEffect(
                    element_id=insertion.new_element.element_id,
                    modification_description=f"added {insertion.new_element.element_type}",
                    attenuation_change_by_frequency={},
                    overall_impact_dba=noise_reduction / max(1, len(request.elements_to_add)),
                ))

            return HVACPathModificationResponse(
                status="success",
                baseline_terminal_noise_dba=baseline_response.terminal_noise_dba,
                simulated_terminal_noise_dba=simulated_response.terminal_noise_dba,
                noise_reduction_dba=noise_reduction,
                baseline_nc_rating=baseline_response.nc_rating,
                simulated_nc_rating=simulated_response.nc_rating,
                nc_improvement=nc_improvement,
                baseline_spectrum=baseline_spectrum,
                simulated_spectrum=simulated_spectrum,
                delta_spectrum=delta_spectrum,
                element_effects=element_effects,
            )

        except Exception as e:
            return HVACPathModificationResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Path element simulation failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def compare_scenarios(
        self,
        request: ScenarioComparisonRequest
    ) -> ScenarioComparisonResponse:
        """
        Compare multiple what-if scenarios side-by-side.

        Args:
            request: Scenario comparison request

        Returns:
            ScenarioComparisonResponse with all scenarios compared
        """
        try:
            scenario_results = []
            best_score = -1
            best_scenario_id = None

            # Build baseline summary
            baseline_summary = {}
            if request.scenario_type == "rt60":
                baseline = request.baseline
                if isinstance(baseline, RT60CalculationResponse):
                    baseline_summary = {
                        "average_rt60": baseline.average_rt60,
                        "rt60_by_frequency": baseline.rt60_by_frequency,
                        "calculation_method": baseline.calculation_method,
                    }
            else:  # hvac
                baseline = request.baseline
                if isinstance(baseline, HVACPathNoiseResponse):
                    baseline_summary = {
                        "terminal_noise_dba": baseline.terminal_noise_dba,
                        "nc_rating": baseline.nc_rating,
                        "terminal_spectrum": baseline.terminal_spectrum,
                    }

            # Process each scenario
            for scenario in request.scenarios:
                if request.scenario_type == "rt60":
                    # Run RT60 simulation
                    sim_request = RT60MaterialChangeRequest(
                        baseline_rt60_response=request.baseline,
                        volume_cubic_feet=request.volume_cubic_feet or 0,
                        floor_area_sq_ft=request.floor_area_sq_ft or 0,
                        wall_area_sq_ft=request.wall_area_sq_ft or 0,
                        ceiling_area_sq_ft=request.ceiling_area_sq_ft or 0,
                        material_changes=scenario.changes,
                    )
                    result = self.simulate_rt60_material_change(sim_request)

                    # Calculate improvement score
                    improvement_score = max(0, min(100, result.improvement_percentage * 2))

                    # Estimate cost based on number/magnitude of changes
                    num_changes = len(scenario.changes)
                    cost = "low" if num_changes == 1 else ("medium" if num_changes <= 3 else "high")

                else:  # hvac
                    # Run HVAC simulation
                    sim_request = HVACPathModificationRequest(
                        baseline_path_response=request.baseline,
                        original_path_elements=request.original_path_elements or [],
                        receiver_room=request.receiver_room,
                        element_modifications=scenario.changes,
                    )
                    result = self.simulate_hvac_path_modification(sim_request)

                    # Calculate improvement score based on noise reduction
                    improvement_score = min(100, max(0, result.noise_reduction_dba * 10))

                    # Estimate cost
                    num_changes = len(scenario.changes)
                    cost = "low" if num_changes == 1 else ("medium" if num_changes <= 3 else "high")

                scenario_results.append(ScenarioResult(
                    scenario_id=scenario.scenario_id,
                    scenario_name=scenario.scenario_name,
                    result=result,
                    improvement_score=round(improvement_score, 1),
                    cost_indicator=cost,
                ))

                if improvement_score > best_score:
                    best_score = improvement_score
                    best_scenario_id = scenario.scenario_id

            # Build comparison matrix
            comparison_matrix = {}
            for sr in scenario_results:
                comparison_matrix[sr.scenario_id] = {
                    "name": sr.scenario_name,
                    "improvement_score": sr.improvement_score,
                    "cost_indicator": sr.cost_indicator,
                }

            return ScenarioComparisonResponse(
                status="success",
                baseline_summary=baseline_summary,
                scenario_results=scenario_results,
                recommended_scenario_id=best_scenario_id,
                comparison_matrix=comparison_matrix,
            )

        except Exception as e:
            return ScenarioComparisonResponse(
                status="error",
                error=APIError(
                    error_code=ErrorCode.CALCULATION_ERROR,
                    error_message=f"Scenario comparison failed: {str(e)}",
                    suggestion="Check input values and try again"
                )
            )

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for this service's endpoints."""
        return {
            "simulate_rt60_material_change": {
                "description": "Simulate the effect of changing materials on RT60",
                "input": "RT60MaterialChangeRequest",
                "output": "RT60MaterialChangeResponse",
                "required_fields": [
                    "baseline_rt60_response",
                    "volume_cubic_feet",
                    "floor_area_sq_ft",
                    "wall_area_sq_ft",
                    "ceiling_area_sq_ft",
                    "material_changes"
                ]
            },
            "simulate_hvac_path_modification": {
                "description": "Simulate the effect of modifying HVAC path elements",
                "input": "HVACPathModificationRequest",
                "output": "HVACPathModificationResponse",
                "required_fields": [
                    "baseline_path_response",
                    "original_path_elements",
                    "element_modifications"
                ]
            },
            "simulate_path_element_change": {
                "description": "Simulate adding or removing path elements",
                "input": "PathElementChangeRequest",
                "output": "HVACPathModificationResponse",
                "required_fields": [
                    "original_path_elements",
                    "elements_to_add OR elements_to_remove"
                ]
            },
            "compare_scenarios": {
                "description": "Compare multiple what-if scenarios side-by-side",
                "input": "ScenarioComparisonRequest",
                "output": "ScenarioComparisonResponse",
                "required_fields": [
                    "scenario_type",
                    "baseline",
                    "scenarios"
                ]
            }
        }
