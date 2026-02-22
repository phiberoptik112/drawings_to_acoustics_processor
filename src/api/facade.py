"""
Acoustic Analysis API Facade

Unified entry point for LLM agentic workflows.
"""

from typing import Dict, Any

from src.api.endpoints.rt60_api import RT60CalculationService
from src.api.endpoints.hvac_api import HVACNoiseService
from src.api.endpoints.materials_api import MaterialsService
from src.api.endpoints.simulation_api import SimulationService

from src.api.schemas.rt60_schemas import (
    RT60CalculationRequest,
    RT60CalculationResponse,
    RT60ComplianceRequest,
    RT60ComplianceResponse,
    MaterialRecommendationRequest,
    MaterialRecommendationResponse,
)
from src.api.schemas.hvac_schemas import (
    HVACPathNoiseRequest,
    HVACPathNoiseResponse,
    CombinedReceiverNoiseRequest,
    CombinedReceiverNoiseResponse,
    NCComplianceRequest,
    NCComplianceResponse,
)


class AcousticAnalysisAPI:
    """
    Unified API facade for acoustic analysis.

    This is the main entry point for LLM agentic workflows.
    Provides access to all acoustic calculation services through
    a single, well-organized interface.

    Usage:
        api = AcousticAnalysisAPI()

        # Get schema for LLM discovery
        schema = api.get_api_schema()

        # RT60 calculations
        result = api.rt60.calculate_rt60(request)

        # HVAC noise calculations
        result = api.hvac.calculate_path_noise(request)

        # Material lookups
        materials = api.materials.search_materials(request)

        # What-if simulations
        result = api.simulation.simulate_rt60_material_change(request)
    """

    def __init__(self):
        """Initialize all service instances."""
        self.rt60 = RT60CalculationService()
        self.hvac = HVACNoiseService()
        self.materials = MaterialsService()
        self.simulation = SimulationService()

    def get_api_schema(self) -> Dict[str, Any]:
        """
        Return complete JSON schema for all API endpoints.

        This is intended for LLM discovery - allows agents to
        understand available operations and required parameters.

        Returns:
            Dict with schema information for all services
        """
        return {
            "api_version": "1.0.0",
            "description": "Acoustic Analysis API for LLM agentic workflows",
            "design_principles": [
                "Stateless: Each call receives all required data",
                "Strict validation: Missing physics-relevant fields are rejected",
                "Composable: Outputs feed into subsequent operations",
                "Debug mode: Optional verbose output for reasoning"
            ],
            "services": {
                "rt60": {
                    "description": "RT60 reverberation time calculations",
                    "endpoints": self.rt60.get_schema()
                },
                "hvac": {
                    "description": "HVAC path noise calculations",
                    "endpoints": self.hvac.get_schema()
                },
                "materials": {
                    "description": "Acoustic materials database access",
                    "endpoints": self.materials.get_schema()
                },
                "simulation": {
                    "description": "What-if scenario simulations",
                    "endpoints": self.simulation.get_schema()
                }
            },
            "frequency_bands": {
                "rt60": [125, 250, 500, 1000, 2000, 4000],
                "hvac_nc": [63, 125, 250, 500, 1000, 2000, 4000, 8000]
            },
            "units": {
                "dimensions": "inches",
                "length": "feet",
                "area": "square feet",
                "volume": "cubic feet",
                "noise": "dB(A)",
                "absorption": "sabins",
                "flow_rate": "CFM",
                "velocity": "FPM"
            }
        }

    def analyze_room_acoustics(
        self,
        request: RT60CalculationRequest,
        check_compliance: bool = True,
        room_type: str = None
    ) -> Dict[str, Any]:
        """
        Combined RT60 calculation + compliance analysis in one call.

        This is a convenience method that performs both RT60 calculation
        and compliance checking in a single operation.

        Args:
            request: RT60 calculation request
            check_compliance: Whether to also run compliance analysis
            room_type: Room type for compliance targets (optional)

        Returns:
            Dict with calculation and compliance results
        """
        # Calculate RT60
        calc_result = self.rt60.calculate_rt60(request)

        if calc_result.status == "error":
            return {
                "status": "error",
                "calculation": calc_result.to_dict(),
                "compliance": None
            }

        result = {
            "status": "success",
            "calculation": calc_result.to_dict(),
            "compliance": None
        }

        # Run compliance check if requested
        if check_compliance:
            compliance_request = RT60ComplianceRequest(
                rt60_by_frequency=calc_result.rt60_by_frequency,
                room_type=room_type or "conference"  # Default to conference room
            )
            compliance_result = self.rt60.analyze_compliance(compliance_request)
            result["compliance"] = compliance_result.to_dict()

        return result

    def analyze_hvac_path(
        self,
        request: HVACPathNoiseRequest,
        check_nc_compliance: bool = True,
        space_type: str = None
    ) -> Dict[str, Any]:
        """
        Combined path noise calculation + NC compliance in one call.

        This is a convenience method that performs both path noise calculation
        and NC compliance checking in a single operation.

        Args:
            request: HVAC path noise request
            check_nc_compliance: Whether to also run NC compliance analysis
            space_type: Space type for NC targets (optional)

        Returns:
            Dict with calculation and compliance results
        """
        # Calculate path noise
        calc_result = self.hvac.calculate_path_noise(request)

        if calc_result.status == "error":
            return {
                "status": "error",
                "calculation": calc_result.to_dict(),
                "compliance": None
            }

        result = {
            "status": "success",
            "calculation": calc_result.to_dict(),
            "compliance": None
        }

        # Run NC compliance check if requested
        if check_nc_compliance:
            compliance_request = NCComplianceRequest(
                octave_band_levels=calc_result.terminal_spectrum,
                space_type=space_type or "private_office"  # Default
            )
            compliance_result = self.hvac.analyze_nc_compliance(compliance_request)
            result["compliance"] = compliance_result.to_dict()

        return result

    def analyze_combined_receiver(
        self,
        request: CombinedReceiverNoiseRequest,
        check_nc_compliance: bool = True,
        space_type: str = None
    ) -> Dict[str, Any]:
        """
        Combined multi-path receiver analysis + NC compliance.

        Use this when a space has multiple HVAC paths serving it.

        Args:
            request: Combined receiver noise request
            check_nc_compliance: Whether to also run NC compliance analysis
            space_type: Space type for NC targets (optional)

        Returns:
            Dict with combined calculation and compliance results
        """
        # Calculate combined noise
        calc_result = self.hvac.calculate_combined_receiver_noise(request)

        if calc_result.status == "error":
            return {
                "status": "error",
                "calculation": calc_result.to_dict(),
                "compliance": None
            }

        result = {
            "status": "success",
            "calculation": calc_result.to_dict(),
            "compliance": None
        }

        # Run NC compliance check if requested
        if check_nc_compliance:
            compliance_request = NCComplianceRequest(
                octave_band_levels=calc_result.combined_spectrum,
                space_type=space_type or "private_office"
            )
            compliance_result = self.hvac.analyze_nc_compliance(compliance_request)
            result["compliance"] = compliance_result.to_dict()

        return result

    def get_quick_start_examples(self) -> Dict[str, Any]:
        """
        Return example requests for each endpoint.

        Useful for LLM agents to understand expected input formats.
        """
        return {
            "rt60_calculation": {
                "description": "Calculate RT60 for a conference room",
                "example_request": {
                    "volume_cubic_feet": 12000,
                    "floor_area_sq_ft": 1200,
                    "wall_area_sq_ft": 1600,
                    "ceiling_area_sq_ft": 1200,
                    "surfaces": [
                        {"surface_type": "ceiling", "material_key": "acoustic_tile_nrc_70", "area_sq_ft": 1200},
                        {"surface_type": "wall", "material_key": "painted_drywall", "area_sq_ft": 1600},
                        {"surface_type": "floor", "material_key": "carpet_heavy_pad", "area_sq_ft": 1200}
                    ],
                    "calculation_method": "sabine"
                }
            },
            "hvac_path_noise": {
                "description": "Calculate noise through an HVAC supply path",
                "example_request": {
                    "path_id": "supply_path_1",
                    "path_elements": [
                        {
                            "element_type": "source",
                            "element_id": "ahu_1",
                            "source_noise_dba": 65
                        },
                        {
                            "element_type": "duct",
                            "element_id": "main_duct_1",
                            "length_ft": 50,
                            "duct_shape": "rectangular",
                            "width_inches": 24,
                            "height_inches": 16,
                            "duct_type": "sheet_metal",
                            "lining_thickness_inches": 1.0,
                            "flow_rate_cfm": 2000
                        },
                        {
                            "element_type": "terminal",
                            "element_id": "diffuser_1"
                        }
                    ],
                    "receiver_room": {
                        "room_volume_cubic_ft": 12000,
                        "room_absorption_sabins": 400,
                        "distance_from_terminal_ft": 8.0,
                        "termination_type": "flush"
                    }
                }
            },
            "material_search": {
                "description": "Search for high-absorption ceiling materials",
                "example_request": {
                    "category": "ceiling",
                    "min_nrc": 0.75,
                    "limit": 10
                }
            },
            "simulation": {
                "description": "Simulate adding duct lining",
                "note": "Requires baseline_path_response from calculate_path_noise",
                "example_modification": {
                    "element_id": "main_duct_1",
                    "new_lining_thickness_inches": 2.0
                }
            }
        }
