"""
Acoustic calculation engines for RT60 and noise analysis

Note: Some imports are done lazily to avoid circular import issues.
"""

# Import modules that don't have circular dependencies first
from .acoustic_utilities import (
    AcousticConstants, SpectrumProcessor, FrequencyBandManager, NCRatingUtils,
    calculate_dba_from_spectrum, combine_noise_levels, calculate_nc_rating, get_nc_description
)

# Import standardized result types
from .result_types import (
    ResultStatus, CalculationResult, PathCreationResult, ValidationResult,
    OperationResult, SurfaceData, RT60Result, NCAnalysisData
)


# Lazy loading function to avoid circular imports
def __getattr__(name):
    """Lazy load modules to avoid circular imports."""
    if name == 'RT60Calculator':
        from .rt60_calculator import RT60Calculator
        return RT60Calculator
    elif name == 'calculate_simple_rt60':
        from .rt60_calculator import calculate_simple_rt60
        return calculate_simple_rt60
    elif name == 'get_material_absorption_coeff':
        from .rt60_calculator import get_material_absorption_coeff
        return get_material_absorption_coeff
    elif name == 'EnhancedRT60Calculator':
        from .enhanced_rt60_calculator import EnhancedRT60Calculator
        return EnhancedRT60Calculator
    elif name == 'NoiseCalculator':
        from .hvac_noise_engine import NoiseCalculator
        return NoiseCalculator
    elif name == 'HVACNoiseEngine':
        from .hvac_noise_engine import HVACNoiseEngine
        return HVACNoiseEngine
    elif name == 'PathElement':
        from .hvac_noise_engine import PathElement
        return PathElement
    elif name == 'PathResult':
        from .hvac_noise_engine import PathResult
        return PathResult
    elif name == 'NCRatingAnalyzer':
        from .hvac_noise_engine import NCRatingAnalyzer
        return NCRatingAnalyzer
    elif name == 'NCAnalysisResult':
        from .hvac_noise_engine import NCAnalysisResult
        return NCAnalysisResult
    elif name == 'OctaveBandData':
        from .hvac_noise_engine import OctaveBandData
        return OctaveBandData
    elif name == 'HVACPathCalculator':
        from .hvac_path_calculator import HVACPathCalculator
        return HVACPathCalculator
    elif name == 'PathAnalysisResult':
        from .hvac_path_calculator import PathAnalysisResult
        return PathAnalysisResult
    elif name == 'TreatmentAnalyzer':
        from .treatment_analyzer import TreatmentAnalyzer
        return TreatmentAnalyzer
    elif name == 'SurfaceAreaCalculator':
        from .surface_area_calculator import SurfaceAreaCalculator
        return SurfaceAreaCalculator
    elif name == 'CircularDuctCalculator':
        from .circular_duct_calculations import CircularDuctCalculator
        return CircularDuctCalculator
    elif name == 'RectangularDuctCalculator':
        from .rectangular_duct_calculations import RectangularDuctCalculator
        return RectangularDuctCalculator
    elif name == 'FlexDuctCalculator':
        from .flex_duct_calculations import FlexDuctCalculator
        return FlexDuctCalculator
    elif name == 'ElbowTurningVaneCalculator':
        from .elbow_turning_vane_generated_noise_calculations import ElbowTurningVaneCalculator
        return ElbowTurningVaneCalculator
    elif name == 'JunctionElbowNoiseCalculator':
        from .junction_elbow_generated_noise_calculations import JunctionElbowNoiseCalculator
        return JunctionElbowNoiseCalculator
    elif name == 'ReceiverRoomSoundCorrection':
        from .receiver_room_sound_correction_calculations import ReceiverRoomSoundCorrection
        return ReceiverRoomSoundCorrection
    elif name == 'RectangularElbowsCalculator':
        from .rectangular_elbows_calculations import RectangularElbowsCalculator
        return RectangularElbowsCalculator
    raise AttributeError(f"module 'src.calculations' has no attribute '{name}'")

__all__ = [
    # Core calculators
    'RT60Calculator',
    'EnhancedRT60Calculator',
    'calculate_simple_rt60',
    'get_material_absorption_coeff',
    'NoiseCalculator',
    'HVACPathCalculator',
    'HVACNoiseEngine',
    'PathElement',
    'PathResult',
    'PathAnalysisResult',
    'NCRatingAnalyzer',
    'NCAnalysisResult',
    'OctaveBandData',
    'TreatmentAnalyzer',
    'SurfaceAreaCalculator',
    # Specialized duct calculators
    'CircularDuctCalculator',
    'RectangularDuctCalculator',
    'FlexDuctCalculator',
    'ElbowTurningVaneCalculator',
    'JunctionElbowNoiseCalculator',
    'ReceiverRoomSoundCorrection',
    'RectangularElbowsCalculator',
    # Common utilities
    'AcousticConstants',
    'SpectrumProcessor',
    'FrequencyBandManager',
    'NCRatingUtils',
    'calculate_dba_from_spectrum',
    'combine_noise_levels',
    'calculate_nc_rating',
    'get_nc_description',
    # Standardized result types
    'ResultStatus',
    'CalculationResult',
    'PathCreationResult',
    'ValidationResult',
    'OperationResult',
    'SurfaceData',
    'RT60Result',
    'NCAnalysisData'
]