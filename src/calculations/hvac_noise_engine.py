"""
HVAC Noise Calculation Engine - Unified system for HVAC acoustic analysis
Integrates all specialized calculators for complete path analysis
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
import warnings

# Import all specialized calculators
from .circular_duct_calculations import CircularDuctCalculator
from .rectangular_duct_calculations import RectangularDuctCalculator
from .flex_duct_calculations import FlexDuctCalculator
from .elbow_turning_vane_generated_noise_calculations import ElbowTurningVaneCalculator
from .junction_elbow_generated_noise_calculations import JunctionElbowNoiseCalculator
from .receiver_room_sound_correction_calculations import ReceiverRoomSoundCorrection
# TODO: Create unlined_rectangular_duct_calculations.py
# from .unlined_rectangular_duct_calculations import UnlinedRectangularDuctCalculator


@dataclass
class PathElement:
    """Standardized path element data structure"""
    element_type: str  # 'duct', 'elbow', 'junction', 'flex_duct', 'terminal', 'source'
    element_id: str
    length: float = 0.0  # feet
    width: float = 0.0   # inches
    height: float = 0.0  # inches
    diameter: float = 0.0  # inches
    duct_shape: str = 'rectangular'  # 'rectangular', 'circular'
    duct_type: str = 'sheet_metal'  # 'sheet_metal', 'fiberglass', 'flexible'
    lining_thickness: float = 0.0  # inches
    flow_rate: float = 0.0  # cfm
    flow_velocity: float = 0.0  # fpm
    pressure_drop: float = 0.0  # in. w.g.
    # For elbows and junctions
    vane_chord_length: float = 0.0  # inches
    num_vanes: int = 0
    # For room correction
    room_volume: float = 0.0  # cubic feet
    room_absorption: float = 0.0  # sabins
    # Noise properties
    source_noise_level: float = 0.0  # dB(A)
    octave_band_levels: Optional[List[float]] = None  # 8-band spectrum


@dataclass
class PathResult:
    """Complete path analysis result"""
    path_id: str
    source_noise_dba: float
    terminal_noise_dba: float
    total_attenuation_dba: float
    nc_rating: int
    octave_band_spectrum: List[float]  # 8-band spectrum at terminal
    element_results: List[Dict]
    warnings: List[str]
    calculation_valid: bool
    error_message: Optional[str] = None


class HVACNoiseEngine:
    """
    Unified HVAC noise calculation engine that integrates all specialized calculators
    """
    
    # Standard frequency bands (Hz)
    FREQUENCY_BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    
    # NC curves for rating calculation
    NC_CURVES = {
        15: [47, 36, 29, 22, 17, 14, 12, 11],
        20: [51, 40, 33, 26, 22, 19, 17, 16], 
        25: [54, 44, 37, 31, 27, 24, 22, 21],
        30: [57, 48, 41, 35, 31, 29, 28, 27],
        35: [60, 52, 45, 40, 36, 34, 33, 32],
        40: [64, 56, 50, 45, 41, 39, 38, 37],
        45: [67, 60, 54, 49, 46, 44, 43, 42],
        50: [71, 64, 58, 54, 51, 49, 48, 47],
        55: [74, 67, 62, 58, 56, 54, 53, 52],
        60: [77, 71, 67, 63, 61, 59, 58, 57],
        65: [80, 75, 71, 68, 66, 64, 63, 62]
    }
    
    def __init__(self):
        """Initialize the noise engine with all calculators"""
        self.circular_calc = CircularDuctCalculator()
        self.rectangular_calc = RectangularDuctCalculator()
        self.flex_calc = FlexDuctCalculator()
        self.elbow_calc = ElbowTurningVaneCalculator()
        self.junction_calc = JunctionElbowNoiseCalculator()
        self.room_calc = ReceiverRoomSoundCorrection()
        self.unlined_rect_calc = None # UnlinedRectangularDuctCalculator() # TODO: Initialize this
        
    def calculate_path_noise(self, path_elements: List[PathElement], 
                           path_id: str = "path_1") -> PathResult:
        """
        Calculate complete noise transmission through HVAC path
        
        Args:
            path_elements: List of PathElement objects defining the path
            path_id: Unique identifier for the path
            
        Returns:
            PathResult with complete analysis
        """
        try:
            warnings_list = []
            element_results = []
            
            # Validate path
            if not path_elements:
                return PathResult(
                    path_id=path_id,
                    source_noise_dba=0.0,
                    terminal_noise_dba=0.0,
                    total_attenuation_dba=0.0,
                    nc_rating=0,
                    octave_band_spectrum=[0.0] * 8,
                    element_results=[],
                    warnings=["No path elements provided"],
                    calculation_valid=False,
                    error_message="Empty path"
                )
            
            # Find source element
            source_element = None
            for element in path_elements:
                if element.element_type == 'source':
                    source_element = element
                    break
            
            if not source_element:
                warnings_list.append("No source element found, using default 50 dB(A)")
                current_spectrum = [50.0] * 8  # Default spectrum
                current_dba = 50.0
            else:
                if source_element.octave_band_levels:
                    current_spectrum = source_element.octave_band_levels.copy()
                    current_dba = source_element.source_noise_level
                else:
                    # Estimate spectrum from A-weighted level
                    current_spectrum = self._estimate_spectrum_from_dba(source_element.source_noise_level)
                    current_dba = source_element.source_noise_level

            # Add a pseudo element result for the Source so UI numbering starts at 1
            try:
                source_result = {
                    'element_id': getattr(source_element, 'element_id', 'source_1'),
                    'element_type': 'source',
                    'element_order': 0,
                    'segment_number': 1,
                    'noise_before': current_dba,
                    'noise_after': current_dba,
                    'noise_after_dba': current_dba,
                    'noise_after_spectrum': current_spectrum.copy(),
                    'nc_rating': self._calculate_nc_rating(current_spectrum),
                }
                element_results.append(source_result)
            except Exception:
                pass
            
            # Process each element in the path
            total_attenuation_dba = 0.0
            
            for i, element in enumerate(path_elements):
                if element.element_type == 'source':
                    continue  # Already processed
                
                # Capture noise before this element for legacy UI
                noise_before_dba = current_dba
                element_result = self._calculate_element_effect(element, current_spectrum, current_dba)
                element_result['element_id'] = element.element_id
                element_result['element_type'] = element.element_type
                element_result['element_order'] = i
                # Maintain legacy compatibility: some UI expects 'segment_number'
                # Use 1-based index for human-readable ordering
                element_result['segment_number'] = i + 1
                
                # Apply the effect
                if element_result.get('attenuation_spectrum'):
                    attenuation_spectrum = element_result['attenuation_spectrum']
                    if isinstance(attenuation_spectrum, list):
                        # Apply attenuation (subtract)
                        for j in range(min(8, len(attenuation_spectrum))):
                            current_spectrum[j] -= attenuation_spectrum[j]
                            current_spectrum[j] = max(0.0, current_spectrum[j])  # Prevent negative
                
                if element_result.get('generated_spectrum'):
                    generated_spectrum = element_result['generated_spectrum']
                    if isinstance(generated_spectrum, list):
                        # Add generated noise
                        for j in range(min(8, len(generated_spectrum))):
                            if generated_spectrum[j] > 0:
                                current_spectrum[j] = self._combine_noise_levels(
                                    current_spectrum[j], generated_spectrum[j]
                                )
                
                # Update A-weighted level
                current_dba = self._calculate_dba_from_spectrum(current_spectrum)
                
                # Provide legacy keys expected by UI
                element_result['noise_before'] = noise_before_dba
                element_result['noise_after'] = current_dba
                element_result['noise_after_dba'] = current_dba
                element_result['noise_after_spectrum'] = current_spectrum.copy()
                # Include per-element NC rating for UI summary panels
                try:
                    element_result['nc_rating'] = self._calculate_nc_rating(current_spectrum)
                except Exception:
                    # If NC calculation fails, omit but do not break pipeline
                    pass
                
                element_results.append(element_result)
                
                # Track total attenuation
                if element_result.get('attenuation_dba'):
                    total_attenuation_dba += element_result['attenuation_dba']
            
            # Calculate NC rating
            nc_rating = self._calculate_nc_rating(current_spectrum)
            
            return PathResult(
                path_id=path_id,
                source_noise_dba=source_element.source_noise_level if source_element else 50.0,
                terminal_noise_dba=current_dba,
                total_attenuation_dba=total_attenuation_dba,
                nc_rating=nc_rating,
                octave_band_spectrum=current_spectrum,
                element_results=element_results,
                warnings=warnings_list,
                calculation_valid=True
            )
            
        except Exception as e:
            return PathResult(
                path_id=path_id,
                source_noise_dba=0.0,
                terminal_noise_dba=0.0,
                total_attenuation_dba=0.0,
                nc_rating=0,
                octave_band_spectrum=[0.0] * 8,
                element_results=[],
                warnings=[],
                calculation_valid=False,
                error_message=str(e)
            )
    
    def _calculate_element_effect(self, element: PathElement, 
                                input_spectrum: List[float], 
                                input_dba: float) -> Dict[str, Any]:
        """Calculate the acoustic effect of a single path element"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': None,
            'generated_spectrum': None,
            'attenuation_dba': None,
            'generated_dba': None
        }
        
        try:
            if element.element_type == 'duct':
                result = self._calculate_duct_effect(element)
            elif element.element_type == 'elbow':
                result = self._calculate_elbow_effect(element)
            elif element.element_type == 'junction':
                result = self._calculate_junction_effect(element)
            elif element.element_type == 'flex_duct':
                result = self._calculate_flex_duct_effect(element)
            elif element.element_type == 'terminal':
                result = self._calculate_terminal_effect(element)
            else:
                # Unknown element type - pass through
                pass
                
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def _calculate_duct_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate duct attenuation effect"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': [0.0] * 8,
            'generated_spectrum': None,
            'attenuation_dba': 0.0,
            'generated_dba': None
        }
        
        try:
            if element.duct_shape == 'circular':
                # Use circular duct calculator
                if element.lining_thickness > 0:
                    # Lined circular duct
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if freq <= 4000:  # Circular calc supports up to 4000 Hz
                            attenuation = self.circular_calc.calculate_lined_insertion_loss(
                                element.diameter, element.lining_thickness, freq, element.length
                            )
                            result['attenuation_spectrum'][i] = attenuation
                else:
                    # Unlined circular duct
                    spectrum = self.circular_calc.get_unlined_attenuation_spectrum(
                        element.diameter, element.length
                    )
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if str(freq) in spectrum:
                            result['attenuation_spectrum'][i] = spectrum[str(freq)]
                            
            else:
                # Rectangular duct
                if element.lining_thickness > 0:
                    # Lined rectangular duct
                    if element.lining_thickness <= 1.0:
                        spectrum = self.rectangular_calc.get_1inch_lining_insertion_loss(
                            element.width, element.height, element.length
                        )
                    else:
                        spectrum = self.rectangular_calc.get_2inch_lining_attenuation(
                            element.width, element.height, element.length
                        )
                    
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if str(freq) in spectrum:
                            result['attenuation_spectrum'][i] = spectrum[str(freq)]
                else:
                    # Unlined rectangular duct
                    spectrum = self.rectangular_calc.get_unlined_attenuation(
                        element.width, element.height, element.length
                    )
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if str(freq) in spectrum:
                            result['attenuation_spectrum'][i] = spectrum[str(freq)]
            
            # Calculate A-weighted attenuation
            result['attenuation_dba'] = self._calculate_dba_from_spectrum(result['attenuation_spectrum'])
            
        except Exception as e:
            result['error'] = f"Duct calculation error: {str(e)}"
            
        return result
    
    def _calculate_elbow_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate elbow generated noise effect"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': None,
            'generated_spectrum': [0.0] * 8,
            'attenuation_dba': None,
            'generated_dba': 0.0
        }
        
        try:
            if element.vane_chord_length > 0 and element.num_vanes > 0:
                # Elbow with turning vanes
                duct_area = self._calculate_duct_area(element)
                spectrum = self.elbow_calc.calculate_complete_spectrum(
                    element.flow_rate, duct_area, element.height,
                    element.vane_chord_length, element.num_vanes,
                    element.pressure_drop, element.flow_velocity
                )
                
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    if str(freq) in spectrum:
                        result['generated_spectrum'][i] = spectrum[str(freq)]
            else:
                # Simple elbow - use junction calculator with elbow type
                duct_area = self._calculate_duct_area(element)
                # Use the junction calculator's spectrum method
                spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
                    element.flow_rate, duct_area, element.flow_rate, duct_area
                )
                # Extract elbow spectrum from results
                if 'elbow_90_no_vanes' in spectrum_data:
                    elbow_spectrum = spectrum_data['elbow_90_no_vanes']
                    for i, freq in enumerate(self.FREQUENCY_BANDS):
                        if str(freq) in elbow_spectrum:
                            result['generated_spectrum'][i] = elbow_spectrum[str(freq)]
            
            # Calculate A-weighted generated noise
            result['generated_dba'] = self._calculate_dba_from_spectrum(result['generated_spectrum'])
            
        except Exception as e:
            result['error'] = f"Elbow calculation error: {str(e)}"
            
        return result
    
    def _calculate_junction_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate junction generated noise effect"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': None,
            'generated_spectrum': [0.0] * 8,
            'attenuation_dba': None,
            'generated_dba': 0.0
        }
        
        try:
            duct_area = self._calculate_duct_area(element)
            # Use the junction calculator's spectrum method
            spectrum_data = self.junction_calc.calculate_junction_noise_spectrum(
                element.flow_rate, duct_area, element.flow_rate, duct_area
            )
            # Extract T-junction spectrum from results
            if 't_junction' in spectrum_data:
                junction_spectrum = spectrum_data['t_junction']
                for i, freq in enumerate(self.FREQUENCY_BANDS):
                    if str(freq) in junction_spectrum:
                        result['generated_spectrum'][i] = junction_spectrum[str(freq)]
            
            # Calculate A-weighted generated noise
            result['generated_dba'] = self._calculate_dba_from_spectrum(result['generated_spectrum'])
            
        except Exception as e:
            result['error'] = f"Junction calculation error: {str(e)}"
            
        return result
    
    def _calculate_flex_duct_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate flexible duct insertion loss effect"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': [0.0] * 8,
            'generated_spectrum': None,
            'attenuation_dba': 0.0,
            'generated_dba': None
        }
        
        try:
            spectrum = self.flex_calc.get_insertion_loss(element.diameter, element.length)
            
            for i, freq in enumerate(self.FREQUENCY_BANDS):
                if freq in spectrum:
                    result['attenuation_spectrum'][i] = spectrum[freq]
            
            # Calculate A-weighted attenuation
            result['attenuation_dba'] = self._calculate_dba_from_spectrum(result['attenuation_spectrum'])
            
        except Exception as e:
            result['error'] = f"Flex duct calculation error: {str(e)}"
            
        return result
    
    def _calculate_terminal_effect(self, element: PathElement) -> Dict[str, Any]:
        """Calculate terminal unit effect (room correction)"""
        result: Dict[str, Any] = {
            'attenuation_spectrum': None,
            'generated_spectrum': None,
            'attenuation_dba': None,
            'generated_dba': None
        }
        
        try:
            if element.room_volume > 0 and element.room_absorption > 0:
                # Apply room correction using the room calculator
                # This would typically be applied to the final spectrum
                # For now, we'll note that room correction is available
                result['room_correction_available'] = True
                result['room_volume'] = element.room_volume
                result['room_absorption'] = element.room_absorption
                
        except Exception as e:
            result['error'] = f"Terminal calculation error: {str(e)}"
            
        return result
    
    def _calculate_duct_area(self, element: PathElement) -> float:
        """Calculate duct cross-sectional area in square feet"""
        if element.duct_shape == 'circular':
            # Convert diameter from inches to feet
            radius_ft = (element.diameter / 2.0) / 12.0
            return math.pi * radius_ft * radius_ft
        else:
            # Rectangular duct
            width_ft = element.width / 12.0
            height_ft = element.height / 12.0
            return width_ft * height_ft
    
    def _estimate_spectrum_from_dba(self, dba: float) -> List[float]:
        """Estimate octave band spectrum from A-weighted level"""
        # Typical HVAC spectrum shape
        spectrum_shape = [0.0, -2.0, -1.0, 0.0, 1.0, 2.0, 1.0, -1.0]
        spectrum = []
        
        for shape in spectrum_shape:
            band_level = dba + shape
            spectrum.append(max(0.0, band_level))
            
        return spectrum
    
    def _calculate_dba_from_spectrum(self, spectrum: List[float]) -> float:
        """Calculate A-weighted level from octave band spectrum"""
        # A-weighting factors for each frequency band
        a_weighting = [-26.2, -16.1, -8.6, -3.2, 0.0, 1.2, 1.0, -1.1]
        
        weighted_sum = 0.0
        for i, level in enumerate(spectrum):
            if level > 0:
                weighted_level = level + a_weighting[i]
                weighted_sum += 10 ** (weighted_level / 10.0)
        
        if weighted_sum > 0:
            return 10 * math.log10(weighted_sum)
        else:
            return 0.0
    
    def _combine_noise_levels(self, level1: float, level2: float) -> float:
        """Combine two noise levels using logarithmic addition"""
        if level1 <= 0 and level2 <= 0:
            return 0.0
        elif level1 <= 0:
            return level2
        elif level2 <= 0:
            return level1
        else:
            linear1 = 10 ** (level1 / 10.0)
            linear2 = 10 ** (level2 / 10.0)
            combined_linear = linear1 + linear2
            return 10 * math.log10(combined_linear)
    
    def _calculate_nc_rating(self, spectrum: List[float]) -> int:
        """Calculate NC rating from octave band spectrum"""
        # Find the highest NC curve that the spectrum doesn't exceed
        for nc_rating in sorted(self.NC_CURVES.keys(), reverse=True):
            nc_curve = self.NC_CURVES[nc_rating]
            exceeds = False
            
            for i, level in enumerate(spectrum):
                if i < len(nc_curve) and level > nc_curve[i]:
                    exceeds = True
                    break
            
            if not exceeds:
                return nc_rating
        
        return 65  # Default to highest NC rating if all exceeded
    
    def get_nc_description(self, nc_rating: int) -> str:
        """Get description of NC rating"""
        descriptions = {
            15: "Very quiet - Private offices, libraries",
            20: "Quiet - Executive offices, conference rooms", 
            25: "Moderately quiet - Open offices, classrooms",
            30: "Moderate - General offices, retail spaces",
            35: "Moderately noisy - Restaurants, lobbies",
            40: "Noisy - Cafeterias, gymnasiums",
            45: "Very noisy - Workshops, mechanical rooms",
            50: "Extremely noisy - Industrial spaces",
            55: "Unacceptable for most occupied spaces",
            60: "Unacceptable for occupied spaces",
            65: "Hearing protection recommended"
        }
        
        # Find closest NC rating
        closest_nc = min(descriptions.keys(), key=lambda x: abs(x - nc_rating))
        return descriptions.get(closest_nc, "Unknown criteria")
    
    def validate_path_elements(self, path_elements: List[PathElement]) -> Tuple[bool, List[str]]:
        """Validate path elements for calculation"""
        warnings = []
        is_valid = True
        
        if not path_elements:
            warnings.append("No path elements provided")
            return False, warnings
        
        # Check for source element
        has_source = any(elem.element_type == 'source' for elem in path_elements)
        if not has_source:
            warnings.append("No source element found")
            is_valid = False
        
        # Validate each element
        for i, element in enumerate(path_elements):
            element_num = i + 1
            
            if element.element_type == 'duct':
                if element.length <= 0:
                    warnings.append(f"Element {element_num}: Invalid duct length ({element.length})")
                    is_valid = False
                
                if element.duct_shape == 'circular':
                    if element.diameter <= 0:
                        warnings.append(f"Element {element_num}: Invalid duct diameter ({element.diameter})")
                        is_valid = False
                else:
                    if element.width <= 0 or element.height <= 0:
                        warnings.append(f"Element {element_num}: Invalid duct dimensions ({element.width}x{element.height})")
                        is_valid = False
            
            elif element.element_type in ['elbow', 'junction']:
                if element.flow_rate <= 0:
                    warnings.append(f"Element {element_num}: Invalid flow rate ({element.flow_rate})")
                    is_valid = False
        
        return is_valid, warnings 