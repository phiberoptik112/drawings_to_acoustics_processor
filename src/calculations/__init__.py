"""
Acoustic calculation engines for RT60 and noise analysis
"""

from .rt60_calculator import RT60Calculator, calculate_simple_rt60, get_material_absorption_coeff
from .enhanced_rt60_calculator import EnhancedRT60Calculator
from .hvac_noise_engine import NoiseCalculator
from .hvac_path_calculator import HVACPathCalculator, PathAnalysisResult
from .hvac_noise_engine import HVACNoiseEngine, PathElement, PathResult, NCRatingAnalyzer, NCAnalysisResult, OctaveBandData
from .treatment_analyzer import TreatmentAnalyzer
from .surface_area_calculator import SurfaceAreaCalculator
# Common utilities (imported first for use by other modules)
from .acoustic_utilities import (
    AcousticConstants, SpectrumProcessor, FrequencyBandManager, NCRatingUtils,
    calculate_dba_from_spectrum, combine_noise_levels, calculate_nc_rating, get_nc_description
)
from .circular_duct_calculations import CircularDuctCalculator
from .rectangular_duct_calculations import RectangularDuctCalculator
from .flex_duct_calculations import FlexDuctCalculator
from .elbow_turning_vane_generated_noise_calculations import ElbowTurningVaneCalculator
from .junction_elbow_generated_noise_calculations import JunctionElbowNoiseCalculator
from .receiver_room_sound_correction_calculations import ReceiverRoomSoundCorrection
from .rectangular_elbows_calculations import RectangularElbowsCalculator

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
    'get_nc_description'
]