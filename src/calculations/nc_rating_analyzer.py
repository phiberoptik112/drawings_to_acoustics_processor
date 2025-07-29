"""
NC Rating Analyzer - Advanced NC (Noise Criteria) rating analysis and octave band processing
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class OctaveBandData:
    """Octave band sound pressure levels"""
    freq_63: float = 0.0
    freq_125: float = 0.0
    freq_250: float = 0.0
    freq_500: float = 0.0
    freq_1000: float = 0.0
    freq_2000: float = 0.0
    freq_4000: float = 0.0
    freq_8000: float = 0.0
    
    def to_list(self) -> List[float]:
        """Convert to list for processing"""
        return [self.freq_63, self.freq_125, self.freq_250, self.freq_500, 
                self.freq_1000, self.freq_2000, self.freq_4000, self.freq_8000]
    
    def from_list(self, values: List[float]) -> 'OctaveBandData':
        """Create from list of values"""
        if len(values) >= 8:
            return OctaveBandData(
                freq_63=values[0], freq_125=values[1], freq_250=values[2], freq_500=values[3],
                freq_1000=values[4], freq_2000=values[5], freq_4000=values[6], freq_8000=values[7]
            )
        return self


@dataclass
class NCAnalysisResult:
    """Result of NC rating analysis"""
    nc_rating: int
    octave_band_levels: OctaveBandData
    exceedances: List[Tuple[int, float]]  # (frequency, dB over limit)
    overall_dba: float
    calculation_method: str
    warnings: List[str]
    meets_criteria: bool


class NCRatingAnalyzer:
    """Advanced NC rating analysis with octave band processing"""
    
    # NC curves - sound pressure levels (dB) for each NC rating at each octave band frequency
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
    
    # Octave band center frequencies (Hz)
    FREQUENCIES = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    
    # A-weighting adjustments for each octave band
    A_WEIGHTING = [-26.2, -16.1, -8.6, -3.2, 0.0, 1.2, 1.0, -1.1]
    
    def __init__(self):
        """Initialize the NC rating analyzer"""
        pass
    
    def analyze_octave_band_data(self, octave_data: OctaveBandData, target_nc: Optional[int] = None) -> NCAnalysisResult:
        """
        Analyze octave band data to determine NC rating
        
        Args:
            octave_data: Octave band sound pressure levels
            target_nc: Target NC rating for comparison (optional)
            
        Returns:
            NCAnalysisResult with detailed analysis
        """
        levels = octave_data.to_list()
        
        # Determine NC rating
        nc_rating = self.determine_nc_rating(levels)
        
        # Check for exceedances if target NC is specified
        exceedances = []
        meets_criteria = True
        
        if target_nc and target_nc in self.NC_CURVES:
            target_levels = self.NC_CURVES[target_nc]
            for i, (measured, limit) in enumerate(zip(levels, target_levels)):
                if measured > limit:
                    exceedance = measured - limit
                    exceedances.append((self.FREQUENCIES[i], exceedance))
                    meets_criteria = False
        
        # Calculate overall dB(A)
        overall_dba = self.calculate_overall_dba(levels)
        
        # Generate warnings
        warnings = self.generate_warnings(levels, nc_rating, exceedances)
        
        return NCAnalysisResult(
            nc_rating=nc_rating,
            octave_band_levels=octave_data,
            exceedances=exceedances,
            overall_dba=overall_dba,
            calculation_method="Octave Band Analysis",
            warnings=warnings,
            meets_criteria=meets_criteria
        )
    
    def estimate_octave_bands_from_dba(self, dba_level: float, spectrum_type: str = "typical_hvac") -> OctaveBandData:
        """
        Estimate octave band levels from overall dB(A) level
        
        Args:
            dba_level: Overall A-weighted sound level
            spectrum_type: Type of noise spectrum for estimation
            
        Returns:
            OctaveBandData with estimated levels
        """
        # Typical HVAC spectrum shapes (relative to 1000 Hz)
        spectrum_shapes = {
            "typical_hvac": [5, 3, 1, -1, 0, -2, -4, -6],  # Fan/duct noise
            "fan_noise": [8, 5, 2, -1, 0, -3, -6, -9],     # Centrifugal fan
            "diffuser_noise": [0, -2, -1, 0, 0, -1, -3, -5], # Terminal diffuser
            "duct_breakout": [3, 1, 0, -1, 0, -2, -4, -7],  # Duct wall transmission
            "flat_spectrum": [0, 0, 0, 0, 0, 0, 0, 0]       # Flat across frequencies
        }
        
        shape = spectrum_shapes.get(spectrum_type, spectrum_shapes["typical_hvac"])
        
        # Estimate 1000 Hz level from dB(A)
        # This is an approximation - exact conversion requires iterative calculation
        level_1000 = dba_level - 2  # Typical adjustment for HVAC spectra
        
        # Calculate octave band levels
        octave_levels = []
        for i, relative_level in enumerate(shape):
            band_level = level_1000 + relative_level
            octave_levels.append(max(0, band_level))  # Don't go below 0 dB
        
        return OctaveBandData().from_list(octave_levels)
    
    def determine_nc_rating(self, octave_levels: List[float]) -> int:
        """
        Determine NC rating from octave band levels
        
        Args:
            octave_levels: List of 8 octave band levels
            
        Returns:
            NC rating (15-65)
        """
        if len(octave_levels) != 8:
            return 30  # Default if invalid data
        
        # Find the highest NC curve that is not exceeded by any frequency
        for nc_rating in sorted(self.NC_CURVES.keys()):
            nc_limits = self.NC_CURVES[nc_rating]
            
            # Check if all octave bands are below this NC curve
            exceeds_curve = False
            for measured, limit in zip(octave_levels, nc_limits):
                if measured > limit:
                    exceeds_curve = True
                    break
            
            if not exceeds_curve:
                return nc_rating
        
        # If all curves are exceeded, return highest rating
        return max(self.NC_CURVES.keys())
    
    def calculate_overall_dba(self, octave_levels: List[float]) -> float:
        """
        Calculate overall A-weighted sound level from octave bands
        
        Args:
            octave_levels: List of 8 octave band levels
            
        Returns:
            Overall dB(A) level
        """
        if len(octave_levels) != 8:
            return 0.0
        
        # Apply A-weighting and convert to linear scale
        linear_sum = 0.0
        for level, a_weight in zip(octave_levels, self.A_WEIGHTING):
            if level > 0:
                a_weighted_level = level + a_weight
                linear_sum += 10 ** (a_weighted_level / 10.0)
        
        # Convert back to dB
        if linear_sum > 0:
            return 10 * math.log10(linear_sum)
        else:
            return 0.0
    
    def generate_warnings(self, levels: List[float], nc_rating: int, exceedances: List[Tuple[int, float]]) -> List[str]:
        """
        Generate analysis warnings based on results
        
        Args:
            levels: Octave band levels
            nc_rating: Determined NC rating
            exceedances: List of frequency exceedances
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check for unusual spectral characteristics
        if len(levels) >= 8:
            # Check for low frequency dominance
            if levels[0] > levels[4] + 10:  # 63 Hz > 1000 Hz + 10 dB
                warnings.append("Low frequency noise dominance detected")
            
            # Check for high frequency emphasis
            if levels[7] > levels[4] + 5:  # 8000 Hz > 1000 Hz + 5 dB
                warnings.append("High frequency noise emphasis detected")
            
            # Check for very low levels
            if max(levels) < 20:
                warnings.append("Very low noise levels - verify measurement accuracy")
        
        # NC rating warnings
        if nc_rating > 50:
            warnings.append("High NC rating - may require noise control measures")
        elif nc_rating < 20:
            warnings.append("Very low NC rating - verify calculations")
        
        # Exceedance warnings
        if exceedances:
            freq_list = [str(freq) for freq, _ in exceedances]
            warnings.append(f"Target NC exceeded at frequencies: {', '.join(freq_list)} Hz")
        
        return warnings
    
    def get_nc_description(self, nc_rating: int) -> str:
        """
        Get description of NC rating suitability
        
        Args:
            nc_rating: NC rating value
            
        Returns:
            Description of suitability for different spaces
        """
        descriptions = {
            15: "Very quiet - Concert halls, broadcasting studios, private offices",
            20: "Quiet - Executive offices, conference rooms, libraries",
            25: "Moderately quiet - Open offices, classrooms, hospitals",
            30: "Moderate - General offices, retail spaces, restaurants",
            35: "Moderately noisy - Cafeterias, gymnasiums, lobbies",
            40: "Noisy - Light industrial, workshops, kitchens",
            45: "Very noisy - Heavy industrial, mechanical rooms",
            50: "Extremely noisy - Factories, transportation terminals",
            55: "Unacceptable for most occupied spaces",
            60: "Unacceptable for occupied spaces except very briefly",
            65: "Hearing protection recommended"
        }
        
        # Find closest NC rating description
        closest_nc = min(descriptions.keys(), key=lambda x: abs(x - nc_rating))
        base_desc = descriptions.get(closest_nc, "Unknown criteria")
        
        if nc_rating != closest_nc:
            return f"NC-{nc_rating}: Between NC-{closest_nc} criteria - {base_desc}"
        else:
            return f"NC-{nc_rating}: {base_desc}"
    
    def compare_to_standards(self, nc_rating: int, space_type: str) -> Dict[str, any]:
        """
        Compare NC rating to recommended standards for different space types
        
        Args:
            nc_rating: Measured NC rating
            space_type: Type of space (office, classroom, etc.)
            
        Returns:
            Dictionary with comparison results
        """
        # Recommended NC ratings for different space types
        standards = {
            "private_office": {"recommended": 25, "maximum": 30},
            "open_office": {"recommended": 30, "maximum": 35},
            "conference_room": {"recommended": 20, "maximum": 25},
            "classroom": {"recommended": 25, "maximum": 30},
            "library": {"recommended": 20, "maximum": 25},
            "hospital_room": {"recommended": 25, "maximum": 30},
            "restaurant": {"recommended": 35, "maximum": 40},
            "retail": {"recommended": 35, "maximum": 40},
            "gymnasium": {"recommended": 40, "maximum": 45},
            "lobby": {"recommended": 35, "maximum": 40},
            "corridor": {"recommended": 35, "maximum": 40}
        }
        
        standard = standards.get(space_type.lower().replace(" ", "_"), 
                                {"recommended": 30, "maximum": 35})
        
        recommended = standard["recommended"]
        maximum = standard["maximum"]
        
        # Determine compliance
        if nc_rating <= recommended:
            compliance = "Excellent"
            status = "Meets recommended criteria"
        elif nc_rating <= maximum:
            compliance = "Acceptable"
            status = "Meets maximum criteria but exceeds recommended"
        else:
            compliance = "Non-compliant"
            status = f"Exceeds maximum criteria by {nc_rating - maximum} NC points"
        
        return {
            "space_type": space_type,
            "measured_nc": nc_rating,
            "recommended_nc": recommended,
            "maximum_nc": maximum,
            "compliance": compliance,
            "status": status,
            "improvement_needed": max(0, nc_rating - maximum)
        }
    
    def recommend_noise_control(self, analysis_result: NCAnalysisResult, target_nc: int) -> List[str]:
        """
        Recommend noise control measures based on analysis
        
        Args:
            analysis_result: NC analysis result
            target_nc: Target NC rating to achieve
            
        Returns:
            List of recommended noise control measures
        """
        recommendations = []
        
        if analysis_result.nc_rating <= target_nc:
            recommendations.append("Current noise levels meet target criteria")
            return recommendations
        
        reduction_needed = analysis_result.nc_rating - target_nc
        
        # General recommendations based on reduction needed
        if reduction_needed <= 5:
            recommendations.extend([
                "Consider adding duct silencers in main supply ducts",
                "Install flexible duct connections at equipment",
                "Add acoustic lining to supply and return ducts"
            ])
        elif reduction_needed <= 10:
            recommendations.extend([
                "Install high-performance duct silencers",
                "Relocate noisy equipment away from quiet spaces",
                "Add vibration isolation to mechanical equipment",
                "Consider variable speed drives to reduce fan noise"
            ])
        else:
            recommendations.extend([
                "Major noise control measures required",
                "Consider equipment replacement with quieter alternatives",
                "Install sound-rated mechanical room construction",
                "Add multiple stages of silencing in ductwork",
                "Evaluate system design for noise optimization"
            ])
        
        # Frequency-specific recommendations
        levels = analysis_result.octave_band_levels.to_list()
        if len(levels) >= 8:
            # Low frequency problems
            if levels[0] > levels[4] + 10 or levels[1] > levels[4] + 8:
                recommendations.append("Address low frequency noise with equipment isolation and structural modifications")
            
            # High frequency problems  
            if levels[6] > levels[4] + 5 or levels[7] > levels[4] + 5:
                recommendations.append("Add high frequency absorption and consider diffuser design")
        
        return recommendations