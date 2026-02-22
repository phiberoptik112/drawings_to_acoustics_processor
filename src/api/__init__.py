"""
Acoustic Analysis API for LLM Agentic Workflows

This module provides a stateless, pure Python API for operating and testing
acoustic calculations. Designed for LLM agent consumption with strict validation,
clear schemas, and composable operations.

Main Entry Point:
    from src.api import AcousticAnalysisAPI

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

from src.api.facade import AcousticAnalysisAPI
from src.api.endpoints.rt60_api import RT60CalculationService
from src.api.endpoints.hvac_api import HVACNoiseService
from src.api.endpoints.materials_api import MaterialsService
from src.api.endpoints.simulation_api import SimulationService

__all__ = [
    'AcousticAnalysisAPI',
    'RT60CalculationService',
    'HVACNoiseService',
    'MaterialsService',
    'SimulationService',
]
