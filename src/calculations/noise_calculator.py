"""
HVAC Noise Calculator - Calculate mechanical background noise levels and NC ratings
Revised to work with the unified HVAC noise engine
"""

import math
import os
import re
from typing import Dict, List, Tuple, Optional, Any
from .hvac_noise_engine import HVACNoiseEngine, PathElement, PathResult


class NoiseCalculator:
    """Professional HVAC noise calculation engine"""
    
    # NC rating frequency bands (Hz)
    NC_FREQUENCIES = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    
    # NC curves - sound pressure levels (dB) for each NC rating at each frequency
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
        """Initialize the noise calculator"""
        self.hvac_engine = HVACNoiseEngine()
    
    def calculate_hvac_path_noise(self, path_data: Dict, debug: bool = False, origin: str = "user", path_id: Optional[str] = None) -> Dict:
        """
        Calculate noise transmission through an HVAC path from source to terminal
        
        Args:
            path_data: Dictionary containing path information including:
                - source_component: Source component data
                - segments: List of segment data
                - terminal_component: Terminal component data
                
        Returns:
            Dictionary with calculation results
        """
        import os
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        try:
            if debug_export_enabled:
                pid = path_id or str(path_data.get('path_id', 'unknown'))
                print(f"\n===== [NOISE CALCULATOR] START | origin={origin} | path_id={pid} =====")
                print(f"DEBUG_NC: Input path_data keys: {list(path_data.keys())}")
                
            # Convert path_data to PathElement objects
            path_elements = self._convert_path_data_to_elements(path_data)
            
            if debug_export_enabled:
                print(f"DEBUG_NC: Converted to {len(path_elements)} PathElements")
                for i, elem in enumerate(path_elements):
                    print(f"DEBUG_NC:   Element {i}: {elem.element_type} - {elem.element_id}")
                    if elem.element_type == 'source':
                        print(f"DEBUG_NC:     Source noise_level: {elem.source_noise_level}")
                        print(f"DEBUG_NC:     Source octave_bands: {elem.octave_band_levels}")
            
            # Use the HVAC engine to calculate
            result = self.hvac_engine.calculate_path_noise(path_elements, path_id=(path_id or "path_1"), debug=debug, origin=origin)
            
            if debug_export_enabled:
                print(f"DEBUG_NC: Engine returned - valid: {result.calculation_valid}, error: {result.error_message}")
                print(f"DEBUG_NC: Source dBA: {result.source_noise_dba}, Terminal dBA: {result.terminal_noise_dba}")
                pid = path_id or str(path_data.get('path_id', 'unknown'))
                print(f"===== [NOISE CALCULATOR] END   | origin={origin} | path_id={pid} | valid={result.calculation_valid} =====\n")
            
            # Convert back to the expected format
            return self._convert_result_to_dict(result)
            
        except Exception as e:
            if debug_export_enabled:
                print(f"DEBUG_NC: Exception in calculate_hvac_path_noise: {e}")
                import traceback
                print(f"DEBUG_NC: Traceback: {traceback.format_exc()}")
                pid = path_id or str(path_data.get('path_id', 'unknown'))
                try:
                    print(f"===== [NOISE CALCULATOR] END   | origin={origin} | path_id={pid} | valid=False | error=1 =====\n")
                except Exception:
                    pass
            return {
                'source_noise': 0.0,
                'terminal_noise': 0.0,
                'total_attenuation': 0.0,
                'path_segments': [],
                'nc_rating': 0,
                'calculation_valid': False,
                'error': str(e)
            }
    
    def _convert_path_data_to_elements(self, path_data: Dict) -> List[PathElement]:
        """Convert legacy path data format to PathElement objects"""
        elements = []
        # Ensure debug flag is always defined within this function scope
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        # Add source element
        source_component = path_data.get('source_component', {})
        if source_component:
            # Enhanced debugging for source component data
            if debug_export_enabled:
                print(f"DEBUG_NC: Source component data received:")
                print(f"DEBUG_NC:   Source component keys: {list(source_component.keys())}")
                print(f"DEBUG_NC:   Source component full data: {source_component}")
                print(f"DEBUG_NC:   Source component flow_rate: {source_component.get('flow_rate', 'None')}")
                print(f"DEBUG_NC:   Source component flow_rate type: {type(source_component.get('flow_rate', None))}")
            
            # Get source flow rate from the first segment or source component
            source_flow_rate = source_component.get('flow_rate', 0.0)
            segments = path_data.get('segments', [])  # Define segments variable for debug output
            
            if not source_flow_rate:
                # Try to get flow rate from first segment
                if segments:
                    source_flow_rate = segments[0].get('flow_rate', 0.0)
            
            # Debug CFM assignment for source
            if debug_export_enabled:
                print(f"DEBUG_NC: Source CFM assignment:")
                print(f"DEBUG_NC:   Source component flow_rate: {source_component.get('flow_rate', 'None')}")
                print(f"DEBUG_NC:   First segment flow_rate: {segments[0].get('flow_rate', 'None') if segments else 'No segments'}")
                print(f"DEBUG_NC:   Final source flow_rate: {source_flow_rate}")
            
            source_element = PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=source_component.get('noise_level', 50.0),
                octave_band_levels=source_component.get('octave_band_levels'),
                flow_rate=source_flow_rate
            )
            elements.append(source_element)
        
        # Add segments
        segments = path_data.get('segments', [])
        for i, segment in enumerate(segments):
            element_type = self._determine_element_type(segment)
            
            # Normalize duct shape nomenclature ('round' -> 'circular')
            shape = segment.get('duct_shape', 'rectangular')
            if isinstance(shape, str):
                sl = shape.lower()
                shape = 'circular' if sl in ('round', 'circular') else 'rectangular'

            # Debug segment CFM assignment
            segment_flow_rate = segment.get('flow_rate', 0.0)
            if debug_export_enabled:
                print(f"DEBUG_NC: Segment {i+1} CFM assignment:")
                print(f"DEBUG_NC:   Raw segment flow_rate: {segment_flow_rate}")
                print(f"DEBUG_NC:   Segment keys: {list(segment.keys())}")
                if 'flow_rate' not in segment:
                    print(f"DEBUG_NC:   WARNING: No 'flow_rate' key in segment data")
                elif not segment_flow_rate or segment_flow_rate <= 0:
                    print(f"DEBUG_NC:   WARNING: Segment flow_rate is {segment_flow_rate}, may use defaults")
            
            element = PathElement(
                element_type=element_type,
                element_id=f'segment_{i+1}',
                length=segment.get('length', 0.0),
                width=segment.get('duct_width', 12.0),
                height=segment.get('duct_height', 8.0),
                diameter=segment.get('diameter', 0.0),
                duct_shape=shape,
                duct_type=segment.get('duct_type', 'sheet_metal'),
                lining_thickness=segment.get('lining_thickness', 0.0),
                flow_rate=segment_flow_rate,
                flow_velocity=segment.get('flow_velocity', 0.0),
                pressure_drop=segment.get('pressure_drop', 0.0),
                vane_chord_length=segment.get('vane_chord_length', 0.0),
                num_vanes=segment.get('num_vanes', 0),
                room_volume=segment.get('room_volume', 0.0),
                room_absorption=segment.get('room_absorption', 0.0),
                fitting_type=segment.get('fitting_type')
            )
            
            if debug_export_enabled:
                print(f"DEBUG_NC:   Created PathElement {i+1}:")
                print(f"DEBUG_NC:     element_type: {element.element_type}")
                print(f"DEBUG_NC:     element_id: {element.element_id}")
                print(f"DEBUG_NC:     length: {element.length}")
                print(f"DEBUG_NC:     width: {element.width}")
                print(f"DEBUG_NC:     height: {element.height}")
                print(f"DEBUG_NC:     duct_shape: {element.duct_shape}")
                print(f"DEBUG_NC:     duct_type: {element.duct_type}")
                print(f"DEBUG_NC:     lining_thickness: {element.lining_thickness}")
                print(f"DEBUG_NC:     flow_rate: {element.flow_rate}")
                print(f"DEBUG_NC:     fitting_type: {element.fitting_type}")
            
            elements.append(element)
        
        # Add terminal element
        terminal_component = path_data.get('terminal_component', {})
        if terminal_component:
            terminal_element = PathElement(
                element_type='terminal',
                element_id='terminal_1',
                source_noise_level=terminal_component.get('noise_level', 0.0),
                room_volume=terminal_component.get('room_volume', 0.0),
                room_absorption=terminal_component.get('room_absorption', 0.0)
            )
            elements.append(terminal_element)
        
        return elements
    
    def _determine_element_type(self, segment: Dict) -> str:
        """Determine the element type based on segment properties"""
        debug_export_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_export_enabled:
            print(f"DEBUG_ELEMENT_TYPE: Determining element type for segment:")
            print(f"DEBUG_ELEMENT_TYPE:   duct_type: {segment.get('duct_type')}")
            print(f"DEBUG_ELEMENT_TYPE:   fitting_type: {segment.get('fitting_type')}")
            print(f"DEBUG_ELEMENT_TYPE:   length: {segment.get('length')}")
            print(f"DEBUG_ELEMENT_TYPE:   duct_width: {segment.get('duct_width')}")
            print(f"DEBUG_ELEMENT_TYPE:   duct_height: {segment.get('duct_height')}")
        
        # Tokenize fitting_type to avoid substring misclassifications (e.g., 'steel' -> 'tee')
        ft_raw = (segment.get('fitting_type') or '')
        ft = ft_raw.lower()
        tokens = re.findall(r"[a-z0-9]+", ft)
        token_set = set(tokens)

        has_elbow = 'elbow' in token_set
        has_tee_like = ('tee' in token_set) or ('t' in token_set and 'junction' in token_set)
        has_branch = 'branch' in token_set or any(tok.startswith('branch') for tok in tokens)
        has_wye = 'wye' in token_set
        has_cross = 'cross' in token_set or ('x' in token_set and 'junction' in token_set)
        has_junction = ('junction' in token_set) or has_tee_like or has_branch or has_wye or has_cross

        is_pure_fitting = has_elbow or has_junction

        if debug_export_enabled:
            print(f"DEBUG_ELEMENT_TYPE:   parsed tokens: {tokens}")
            print(f"DEBUG_ELEMENT_TYPE:   has_elbow={has_elbow}, has_junction={has_junction}")

        # If it's a pure fitting type, prefer fitting classification even with dimensions present
        if is_pure_fitting:
            if debug_export_enabled:
                print(f"DEBUG_ELEMENT_TYPE:   Pure fitting detected - determining type from tokens")
            if segment.get('duct_type') == 'flexible':
                element_type = 'flex_duct'
            else:
                element_type = 'elbow' if has_elbow else 'junction'
        else:
            # Standard logic: check duct dimensions
            segment_length = segment.get('length', 0.0) or 0.0
            segment_width = segment.get('duct_width', 0.0) or 0.0
            segment_height = segment.get('duct_height', 0.0) or 0.0
            
            # If segment has no duct dimensions, it might be a pure fitting
            if segment_length <= 0 and segment_width <= 0 and segment_height <= 0:
                if debug_export_enabled:
                    print(f"DEBUG_ELEMENT_TYPE:   No duct dimensions - treating as pure fitting")
                
                if segment.get('duct_type') == 'flexible':
                    element_type = 'flex_duct'
                else:
                    # Map based on parsed tokens
                    if ft:
                        if has_elbow:
                            element_type = 'elbow'
                        elif has_junction:
                            element_type = 'junction'
                        else:
                            element_type = 'duct'  # Default to duct for unknown fitting types
                    else:
                        element_type = 'duct'  # No fitting type specified, treat as duct
            else:
                # Segment has duct dimensions - treat as duct regardless of fitting_type
                if segment.get('duct_type') == 'flexible':
                    element_type = 'flex_duct'
                else:
                    element_type = 'duct'  # Always a duct if it has dimensions
                
                if debug_export_enabled:
                    print(f"DEBUG_ELEMENT_TYPE:   Has duct dimensions - treating as {element_type}")
                    print(f"DEBUG_ELEMENT_TYPE:   fitting_type '{segment.get('fitting_type')}' will be handled as additional property")
        
        if debug_export_enabled:
            print(f"DEBUG_ELEMENT_TYPE:   Determined element_type: {element_type}")
        
        return element_type
    
    def _convert_result_to_dict(self, result: PathResult) -> Dict:
        """Convert PathResult to legacy dictionary format"""
        # Provide both legacy and new keys for compatibility
        return {
            'source_noise': result.source_noise_dba,
            'terminal_noise': result.terminal_noise_dba,
            'total_attenuation': result.total_attenuation_dba,
            'total_attenuation_dba': result.total_attenuation_dba,
            'path_segments': result.element_results,
            # Convenience alias for UI naming: elements can be components, fittings, or segments
            'path_elements': result.element_results,
            'nc_rating': result.nc_rating,
            'calculation_valid': result.calculation_valid,
            'warnings': result.warnings,
            'error': result.error_message,
            'octave_band_spectrum': result.octave_band_spectrum,
            'debug_log': getattr(result, 'debug_log', None)
        }
    
    def calculate_segment_attenuation(self, segment_data: Dict) -> Dict:
        """
        Calculate noise attenuation for a single duct segment
        
        Args:
            segment_data: Dictionary containing segment properties
            
        Returns:
            Dictionary with attenuation calculations
        """
        # Convert to PathElement and use the engine
        # Normalize duct shape for segment attenuation as well
        shape = segment_data.get('duct_shape', 'rectangular')
        if isinstance(shape, str):
            sl = shape.lower()
            shape = 'circular' if sl in ('round', 'circular') else 'rectangular'

        element = PathElement(
            element_type=self._determine_element_type(segment_data),
            element_id='temp_segment',
            length=segment_data.get('length', 0.0),
            width=segment_data.get('duct_width', 12.0),
            height=segment_data.get('duct_height', 8.0),
            diameter=segment_data.get('diameter', 0.0),
            duct_shape=shape,
            duct_type=segment_data.get('duct_type', 'sheet_metal'),
            lining_thickness=segment_data.get('lining_thickness', 0.0),
            flow_rate=segment_data.get('flow_rate', 0.0),
            flow_velocity=segment_data.get('flow_velocity', 0.0),
            pressure_drop=segment_data.get('pressure_drop', 0.0),
            vane_chord_length=segment_data.get('vane_chord_length', 0.0),
            num_vanes=segment_data.get('num_vanes', 0),
            fitting_type=segment_data.get('fitting_type')
        )
        
        # Create a dummy input spectrum
        input_spectrum = [50.0] * 8
        input_dba = 50.0
        
        # Calculate effect
        effect = self.hvac_engine._calculate_element_effect(element, input_spectrum, input_dba)
        
        # Convert to legacy format
        return {
            'distance_loss': 0.0,  # Not calculated in new engine
            'duct_loss': effect.get('attenuation_dba', 0.0),
            'fitting_additions': effect.get('generated_dba', 0.0),
            'total_attenuation': (effect.get('attenuation_dba', 0.0) - effect.get('generated_dba', 0.0)),
            'attenuation_spectrum': effect.get('attenuation_spectrum'),
            'generated_spectrum': effect.get('generated_spectrum')
        }
    
    def calculate_duct_attenuation(self, segment_data: Dict) -> float:
        """
        Calculate noise attenuation due to duct characteristics
        
        Args:
            segment_data: Dictionary containing duct properties
            
        Returns:
            Attenuation in dB
        """
        result = self.calculate_segment_attenuation(segment_data)
        return result.get('duct_loss', 0.0)
    
    def calculate_nc_rating(self, data: Optional[Any] = None) -> int:
        """
        Determine NC rating using final octave-band data when available.
        
        Preferred input:
        - data: one of
          - List[float] length 8: final octave band spectrum [63..8000 Hz]
          - Dict with key 'octave_band_spectrum' (or 'octave_band_levels')
          - float/int: fallback A-weighted overall level in dB(A)
        
        Returns:
            NC rating (15-65)
        """
        try:
            spectrum: Optional[List[float]] = None
            
            # Accept dicts from final calculation results
            if isinstance(data, dict):
                bands = data.get('octave_band_spectrum') or data.get('octave_band_levels')
                if isinstance(bands, (list, tuple)):
                    spectrum = [float(x or 0.0) for x in bands[:8]]
            # Accept direct list/tuple of bands
            elif isinstance(data, (list, tuple)):
                spectrum = [float(x or 0.0) for x in list(data)[:8]]
            
            # If we have a spectrum, ensure 8 bands and compute NC from curves
            if spectrum is not None:
                if len(spectrum) < 8:
                    spectrum = spectrum + [0.0] * (8 - len(spectrum))
                return self.hvac_engine._calculate_nc_rating(spectrum)
            
            # Fallback: treat as A-weighted overall level mapping
            noise_level = float(data) if isinstance(data, (int, float)) else 0.0
            if noise_level <= 20:
                return 15
            elif noise_level <= 25:
                return 20
            elif noise_level <= 30:
                return 25
            elif noise_level <= 35:
                return 30
            elif noise_level <= 40:
                return 35
            elif noise_level <= 45:
                return 40
            elif noise_level <= 50:
                return 45
            elif noise_level <= 55:
                return 50
            elif noise_level <= 60:
                return 55
            elif noise_level <= 65:
                return 60
            else:
                return 65
        except Exception:
            return 30  # Default NC rating
    
    def combine_noise_sources(self, noise1: float, noise2: float) -> float:
        """
        Combine two noise sources using logarithmic addition
        
        Args:
            noise1: First noise source level (dB)
            noise2: Second noise source level (dB)
            
        Returns:
            Combined noise level (dB)
        """
        try:
            if noise1 <= 0 and noise2 <= 0:
                return 0.0
            elif noise1 <= 0:
                return noise2
            elif noise2 <= 0:
                return noise1
            else:
                # Logarithmic addition: L_total = 10 * log10(10^(L1/10) + 10^(L2/10))
                linear1 = 10 ** (noise1 / 10.0)
                linear2 = 10 ** (noise2 / 10.0)
                combined_linear = linear1 + linear2
                return 10 * math.log10(combined_linear)
                
        except Exception:
            return max(noise1, noise2)  # Fallback to higher level
    
    def get_nc_criteria_description(self, nc_rating: int) -> str:
        """
        Get description of NC rating criteria
        
        Args:
            nc_rating: NC rating value
            
        Returns:
            Description string
        """
        return self.hvac_engine.get_nc_description(nc_rating)
    
    def validate_path_data(self, path_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate HVAC path data for calculation
        
        Args:
            path_data: Path data dictionary
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        try:
            path_elements = self._convert_path_data_to_elements(path_data)
            return self.hvac_engine.validate_path_elements(path_elements)
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def analyze_space_nc_compliance(self, noise_level: float, space_type: str, target_nc: Optional[int] = None) -> Dict:
        """
        Analyze NC compliance for a specific space type
        
        Args:
            noise_level: Measured noise level in dB(A)
            space_type: Type of space (office, classroom, etc.)
            target_nc: Optional target NC rating
            
        Returns:
            Dictionary with compliance analysis
        """
        try:
            # Estimate octave band spectrum from A-weighted level
            estimated_spectrum = self.hvac_engine._estimate_spectrum_from_dba(noise_level)
            
            # Calculate NC rating
            nc_rating = self.hvac_engine._calculate_nc_rating(estimated_spectrum)
            
            # Determine if meets target
            meets_target = True
            if target_nc and nc_rating > target_nc:
                meets_target = False
            
            return {
                'measured_noise_dba': noise_level,
                'nc_rating': nc_rating,
                'octave_band_levels': estimated_spectrum,
                'space_type': space_type,
                'meets_target': meets_target,
                'nc_description': self.hvac_engine.get_nc_description(nc_rating),
                'recommendations': self._get_recommendations(nc_rating, target_nc) if not meets_target else []
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'measured_noise_dba': noise_level,
                'nc_rating': self.calculate_nc_rating(noise_level),
                'analysis_failed': True
            }
    
    def _get_recommendations(self, current_nc: int, target_nc: Optional[int]) -> List[str]:
        """Get noise control recommendations"""
        recommendations = []
        
        if target_nc and current_nc > target_nc:
            improvement_needed = current_nc - target_nc
            
            if improvement_needed <= 5:
                recommendations.append("Consider adding duct lining or acoustic treatment")
            elif improvement_needed <= 10:
                recommendations.append("Add duct lining and consider silencers")
                recommendations.append("Review duct routing to minimize fittings")
            else:
                recommendations.append("Significant noise reduction required")
                recommendations.append("Consider multiple noise control measures")
                recommendations.append("Review entire HVAC system design")
        
        return recommendations