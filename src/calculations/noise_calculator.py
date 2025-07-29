"""
HVAC Noise Calculator - Calculate mechanical background noise levels and NC ratings
"""

import math
from typing import Dict, List, Tuple, Optional
from data.components import STANDARD_COMPONENTS, STANDARD_FITTINGS
from .nc_rating_analyzer import NCRatingAnalyzer, OctaveBandData


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
        self.nc_analyzer = NCRatingAnalyzer()
    
    def calculate_hvac_path_noise(self, path_data: Dict) -> Dict:
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
        try:
            results = {
                'source_noise': 0.0,
                'terminal_noise': 0.0,
                'total_attenuation': 0.0,
                'path_segments': [],
                'nc_rating': 0,
                'calculation_valid': False,
                'warnings': []
            }
            
            # Get source noise level
            source_component = path_data.get('source_component', {})
            source_type = source_component.get('component_type', '')
            
            if source_type in STANDARD_COMPONENTS:
                results['source_noise'] = STANDARD_COMPONENTS[source_type]['noise_level']
            else:
                results['source_noise'] = source_component.get('noise_level', 50.0)
                results['warnings'].append(f"Unknown component type '{source_type}', using default noise level")
            
            # Calculate attenuation through each segment
            segments = path_data.get('segments', [])
            current_noise = results['source_noise']
            total_attenuation = 0.0
            
            for i, segment in enumerate(segments):
                segment_result = self.calculate_segment_attenuation(segment)
                segment_result['segment_number'] = i + 1
                segment_result['noise_before'] = current_noise
                
                # Apply attenuation
                current_noise -= segment_result['total_attenuation']
                current_noise += segment_result['fitting_additions']
                
                segment_result['noise_after'] = current_noise
                total_attenuation += segment_result['total_attenuation']
                
                results['path_segments'].append(segment_result)
            
            # Account for terminal component
            terminal_component = path_data.get('terminal_component', {})
            terminal_type = terminal_component.get('component_type', '')
            
            if terminal_type in STANDARD_COMPONENTS:
                terminal_noise = STANDARD_COMPONENTS[terminal_type]['noise_level']
                # For terminal units, add their noise to the path noise
                if terminal_noise > 0:
                    current_noise = self.combine_noise_sources(current_noise, terminal_noise)
            
            results['terminal_noise'] = current_noise
            results['total_attenuation'] = total_attenuation
            
            # Calculate NC rating with enhanced analysis
            results['nc_rating'] = self.calculate_nc_rating(current_noise)
            
            # Enhanced NC analysis if available
            octave_data = self.nc_analyzer.estimate_octave_bands_from_dba(current_noise, "typical_hvac")
            nc_analysis = self.nc_analyzer.analyze_octave_band_data(octave_data)
            results['detailed_nc_analysis'] = {
                'octave_bands': nc_analysis.octave_band_levels.to_list(),
                'overall_dba': nc_analysis.overall_dba,
                'nc_description': self.nc_analyzer.get_nc_description(nc_analysis.nc_rating),
                'warnings': nc_analysis.warnings
            }
            
            # Validation
            if results['source_noise'] > 0 and len(segments) > 0:
                results['calculation_valid'] = True
            
            # Add warnings for unusual results
            if current_noise > 70:
                results['warnings'].append("High noise level - consider additional attenuation")
            elif current_noise < 15:
                results['warnings'].append("Very low noise level - verify calculations")
            
            return results
            
        except Exception as e:
            return {
                'source_noise': 0.0,
                'terminal_noise': 0.0,
                'total_attenuation': 0.0,
                'path_segments': [],
                'nc_rating': 0,
                'calculation_valid': False,
                'error': str(e)
            }
    
    def calculate_segment_attenuation(self, segment_data: Dict) -> Dict:
        """
        Calculate noise attenuation for a single duct segment
        
        Args:
            segment_data: Dictionary containing segment properties
            
        Returns:
            Dictionary with attenuation calculations
        """
        result = {
            'distance_loss': 0.0,
            'duct_loss': 0.0,
            'fitting_additions': 0.0,
            'total_attenuation': 0.0
        }
        
        try:
            # Distance attenuation (6 dB per doubling of distance)
            length = segment_data.get('length', 0)
            if length > 0:
                # Use 3 dB per doubling for ducted systems (vs 6 dB for free field)
                reference_distance = 10  # feet
                if length > reference_distance:
                    result['distance_loss'] = 3 * math.log2(length / reference_distance)
            
            # Duct attenuation
            result['duct_loss'] = self.calculate_duct_attenuation(segment_data)
            
            # Fitting noise additions
            fittings = segment_data.get('fittings', [])
            fitting_total = 0.0
            
            for fitting in fittings:
                fitting_type = fitting.get('fitting_type', '')
                if fitting_type in STANDARD_FITTINGS:
                    fitting_total += STANDARD_FITTINGS[fitting_type]['noise_adjustment']
                else:
                    fitting_total += fitting.get('noise_adjustment', 0.0)
            
            result['fitting_additions'] = fitting_total
            result['total_attenuation'] = result['distance_loss'] + result['duct_loss']
            
            return result
            
        except Exception as e:
            result['error'] = str(e)
            return result
    
    def calculate_duct_attenuation(self, segment_data: Dict) -> float:
        """
        Calculate noise attenuation due to duct characteristics
        
        Args:
            segment_data: Dictionary containing duct properties
            
        Returns:
            Attenuation in dB
        """
        try:
            length = segment_data.get('length', 0)
            duct_type = segment_data.get('duct_type', 'sheet_metal')
            duct_shape = segment_data.get('duct_shape', 'rectangular')
            insulation = segment_data.get('insulation', None)
            
            if length <= 0:
                return 0.0
            
            # Base attenuation rates (dB per 100 feet)
            attenuation_rates = {
                'sheet_metal': {
                    'rectangular': 1.0,
                    'round': 0.8
                },
                'fiberglass': {
                    'rectangular': 8.0,
                    'round': 6.0
                },
                'fabric': {
                    'rectangular': 12.0,
                    'round': 10.0
                }
            }
            
            # Get base rate
            base_rate = attenuation_rates.get(duct_type, {}).get(duct_shape, 1.0)
            
            # Apply insulation multiplier
            insulation_multiplier = 1.0
            if insulation:
                if 'fiberglass' in insulation.lower():
                    insulation_multiplier = 2.0
                elif 'foam' in insulation.lower():
                    insulation_multiplier = 1.5
            
            # Calculate attenuation
            attenuation = (base_rate * insulation_multiplier * length) / 100.0
            
            # Limit maximum attenuation to reasonable values
            return min(attenuation, 30.0)
            
        except Exception:
            return 0.0
    
    def calculate_nc_rating(self, noise_level: float) -> int:
        """
        Convert A-weighted noise level to approximate NC rating
        
        Args:
            noise_level: A-weighted sound level in dB(A)
            
        Returns:
            NC rating (15-65)
        """
        try:
            # Simple approximation: A-weighted level roughly corresponds to NC rating
            # This is a simplified conversion - full NC analysis requires octave band data
            
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
    
    def validate_path_data(self, path_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate HVAC path data for calculation
        
        Args:
            path_data: Path data dictionary
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        is_valid = True
        
        # Check source component
        source_component = path_data.get('source_component')
        if not source_component:
            warnings.append("No source component specified")
            is_valid = False
        
        # Check segments
        segments = path_data.get('segments', [])
        if not segments:
            warnings.append("No segments in path")
            is_valid = False
        
        for i, segment in enumerate(segments):
            segment_num = i + 1
            
            # Check segment length
            length = segment.get('length', 0)
            if length <= 0:
                warnings.append(f"Segment {segment_num}: Invalid length ({length})")
            elif length > 500:
                warnings.append(f"Segment {segment_num}: Very long segment ({length} ft)")
            
            # Check duct dimensions
            width = segment.get('duct_width', 0)
            height = segment.get('duct_height', 0)
            
            if width <= 0 or height <= 0:
                warnings.append(f"Segment {segment_num}: Missing duct dimensions")
        
        # Check terminal component
        terminal_component = path_data.get('terminal_component')
        if not terminal_component:
            warnings.append("No terminal component specified")
        
        return is_valid, warnings
    
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
            # Estimate octave band data from overall level
            octave_data = self.nc_analyzer.estimate_octave_bands_from_dba(noise_level, "typical_hvac")
            
            # Perform NC analysis
            nc_analysis = self.nc_analyzer.analyze_octave_band_data(octave_data, target_nc)
            
            # Compare to standards
            standards_comparison = self.nc_analyzer.compare_to_standards(nc_analysis.nc_rating, space_type)
            
            # Get recommendations if needed
            recommendations = []
            if target_nc and nc_analysis.nc_rating > target_nc:
                recommendations = self.nc_analyzer.recommend_noise_control(nc_analysis, target_nc)
            elif not nc_analysis.meets_criteria:
                recommendations = self.nc_analyzer.recommend_noise_control(nc_analysis, standards_comparison['maximum_nc'])
            
            return {
                'measured_noise_dba': noise_level,
                'nc_rating': nc_analysis.nc_rating,
                'octave_band_levels': nc_analysis.octave_band_levels.to_list(),
                'space_type': space_type,
                'standards_comparison': standards_comparison,
                'meets_target': nc_analysis.meets_criteria,
                'exceedances': nc_analysis.exceedances,
                'recommendations': recommendations,
                'warnings': nc_analysis.warnings,
                'nc_description': self.nc_analyzer.get_nc_description(nc_analysis.nc_rating)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'measured_noise_dba': noise_level,
                'nc_rating': self.calculate_nc_rating(noise_level),
                'analysis_failed': True
            }