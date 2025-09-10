"""
Acoustic Utilities - Centralized acoustic constants and common functions

This module consolidates all acoustic constants, NC rating data, A-weighting factors,
frequency bands, and common mathematical functions used across the HVAC calculation system.

By centralizing these utilities, we eliminate duplication and ensure consistency
across all calculation modules.
"""

import math
from typing import Dict, List, Optional, Union, Any


class AcousticConstants:
    """Centralized acoustic constants and reference data"""
    
    # Standard 1/1 octave band center frequencies (Hz)
    FREQUENCY_BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    
    # A-weighting adjustments for each octave band (dB)
    # Applied to convert octave band levels to A-weighted sound levels
    A_WEIGHTING = [-26.2, -16.1, -8.6, -3.2, 0.0, 1.2, 1.0, -1.1]
    
    # NC (Noise Criteria) curves - sound pressure levels (dB) for each NC rating
    # Format: NC_rating -> [63Hz, 125Hz, 250Hz, 500Hz, 1000Hz, 2000Hz, 4000Hz, 8000Hz]
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
    
    # Number of octave bands (for validation)
    NUM_OCTAVE_BANDS = 8
    
    # Valid NC rating range
    MIN_NC_RATING = 15
    MAX_NC_RATING = 65
    
    # Default noise level for fallback calculations
    DEFAULT_NOISE_LEVEL = 50.0
    
    # Minimum meaningful sound level (dB)
    MIN_SOUND_LEVEL = 0.0
    
    @classmethod
    def get_frequency_labels(cls, as_strings: bool = False) -> List[Union[str, int]]:
        """Get frequency band labels in string or integer format"""
        if as_strings:
            return [str(f) for f in cls.FREQUENCY_BANDS]
        return cls.FREQUENCY_BANDS.copy()


class SpectrumProcessor:
    """Common spectrum processing and conversion functions"""
    
    @staticmethod
    def calculate_dba_from_spectrum(spectrum: List[float]) -> float:
        """
        Calculate A-weighted sound level from octave band spectrum
        
        Args:
            spectrum: List of octave band sound pressure levels (dB)
            
        Returns:
            A-weighted sound level (dB(A))
        """
        if not spectrum:
            return 0.0
            
        weighted_sum = 0.0
        for i, level in enumerate(spectrum[:AcousticConstants.NUM_OCTAVE_BANDS]):
            if level > 0 and i < len(AcousticConstants.A_WEIGHTING):
                weighted_level = level + AcousticConstants.A_WEIGHTING[i]
                weighted_sum += 10 ** (weighted_level / 10.0)
        
        if weighted_sum > 0:
            return 10 * math.log10(weighted_sum)
        else:
            return 0.0
    
    @staticmethod
    def combine_noise_levels(level1: float, level2: float) -> float:
        """
        Combine two noise levels using logarithmic addition
        
        Args:
            level1: First noise level (dB)
            level2: Second noise level (dB)
            
        Returns:
            Combined noise level (dB)
        """
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
    
    @staticmethod
    def calculate_nc_rating(spectrum: List[float]) -> int:
        """
        Calculate NC rating from octave band spectrum
        
        NC rating is defined as the lowest NC curve that fully contains the
        measured octave-band spectrum (i.e., the minimum rating for which no
        band exceeds the curve limit).
        
        Args:
            spectrum: List of octave band sound pressure levels (dB)
            
        Returns:
            NC rating (15-65)
        """
        if not spectrum:
            return AcousticConstants.MIN_NC_RATING
            
        # Iterate through NC curves in ascending order
        for nc_rating in sorted(AcousticConstants.NC_CURVES.keys()):
            nc_curve = AcousticConstants.NC_CURVES[nc_rating]
            exceeds = False

            for i, level in enumerate(spectrum):
                if i < len(nc_curve) and level > nc_curve[i]:
                    exceeds = True
                    break

            if not exceeds:
                return nc_rating

        # If every curve is exceeded, return the highest rating
        return max(AcousticConstants.NC_CURVES.keys())
    
    @staticmethod
    def estimate_spectrum_from_dba(dba: float) -> List[float]:
        """
        Estimate octave band spectrum from A-weighted level
        
        Uses typical HVAC spectrum shape as a starting point.
        
        Args:
            dba: A-weighted sound level (dB(A))
            
        Returns:
            Estimated octave band spectrum
        """
        # Typical HVAC spectrum shape relative to overall level
        spectrum_shape = [0.0, -2.0, -1.0, 0.0, 1.0, 2.0, 1.0, -1.0]
        spectrum = []
        
        for shape in spectrum_shape:
            band_level = dba + shape
            spectrum.append(max(AcousticConstants.MIN_SOUND_LEVEL, band_level))
            
        return spectrum
    
    @staticmethod
    def validate_spectrum(spectrum: List[float], strict: bool = True) -> bool:
        """
        Validate octave band spectrum format and values
        
        Args:
            spectrum: List of octave band levels
            strict: If True, requires exactly 8 bands; if False, allows fewer
            
        Returns:
            True if spectrum is valid
        """
        if not isinstance(spectrum, (list, tuple)):
            return False
            
        if strict and len(spectrum) != AcousticConstants.NUM_OCTAVE_BANDS:
            return False
            
        if not strict and len(spectrum) > AcousticConstants.NUM_OCTAVE_BANDS:
            return False
            
        # Check that all values are numeric and non-negative
        try:
            for level in spectrum:
                if not isinstance(level, (int, float)) or level < 0:
                    return False
            return True
        except (TypeError, ValueError):
            return False
    
    @staticmethod
    def normalize_spectrum_length(spectrum: List[float]) -> List[float]:
        """
        Normalize spectrum to standard 8-band format
        
        Args:
            spectrum: Input spectrum (may be shorter or longer than 8 bands)
            
        Returns:
            Normalized 8-band spectrum
        """
        if not spectrum:
            return [0.0] * AcousticConstants.NUM_OCTAVE_BANDS
            
        normalized = spectrum[:AcousticConstants.NUM_OCTAVE_BANDS]
        
        # Pad with zeros if too short
        if len(normalized) < AcousticConstants.NUM_OCTAVE_BANDS:
            normalized.extend([0.0] * (AcousticConstants.NUM_OCTAVE_BANDS - len(normalized)))
            
        return normalized


class FrequencyBandManager:
    """Utilities for frequency band management and conversion"""
    
    @staticmethod
    def normalize_frequency_format(input_bands: List[Union[str, int, float]]) -> List[int]:
        """
        Normalize frequency bands to standard integer format
        
        Args:
            input_bands: List of frequencies in various formats
            
        Returns:
            Normalized list of integer frequencies
        """
        normalized = []
        for band in input_bands:
            try:
                if isinstance(band, str):
                    # Remove any non-numeric characters and convert
                    numeric_str = ''.join(c for c in band if c.isdigit())
                    if numeric_str:
                        normalized.append(int(numeric_str))
                else:
                    normalized.append(int(float(band)))
            except (ValueError, TypeError):
                continue
        return normalized
    
    @staticmethod
    def convert_spectrum_dict_to_list(spectrum_dict: Dict[str, float], 
                                    frequency_order: Optional[List[int]] = None) -> List[float]:
        """
        Convert frequency-keyed spectrum dictionary to ordered list
        
        Args:
            spectrum_dict: Dictionary with frequency keys and level values
            frequency_order: Optional frequency order; defaults to standard bands
            
        Returns:
            Ordered list of spectrum values
        """
        if frequency_order is None:
            frequency_order = AcousticConstants.FREQUENCY_BANDS
            
        spectrum_list = []
        for freq in frequency_order:
            # Try various key formats
            key_variations = [str(freq), f"{freq}Hz", f"{freq}_Hz", freq]
            value = None
            
            for key in key_variations:
                if key in spectrum_dict:
                    value = spectrum_dict[key]
                    break
                    
            spectrum_list.append(float(value or 0.0))
            
        return spectrum_list
    
    @staticmethod
    def convert_list_to_spectrum_dict(spectrum_list: List[float], 
                                    key_format: str = "Hz") -> Dict[str, float]:
        """
        Convert spectrum list to frequency-keyed dictionary
        
        Args:
            spectrum_list: List of spectrum values
            key_format: Format for dictionary keys ("Hz", "str", or "int")
            
        Returns:
            Dictionary with frequency keys
        """
        spectrum_dict = {}
        frequencies = AcousticConstants.FREQUENCY_BANDS[:len(spectrum_list)]
        
        for freq, value in zip(frequencies, spectrum_list):
            if key_format == "Hz":
                key = f"{freq}Hz"
            elif key_format == "str":
                key = str(freq)
            elif key_format == "int":
                key = freq
            else:
                key = f"{freq}Hz"  # Default format
                
            spectrum_dict[key] = float(value)
            
        return spectrum_dict
    
    @staticmethod
    def interpolate_missing_bands(spectrum_dict: Dict[str, float]) -> Dict[str, float]:
        """
        Interpolate missing frequency bands in spectrum
        
        Args:
            spectrum_dict: Partial spectrum dictionary
            
        Returns:
            Complete spectrum dictionary with interpolated values
        """
        # Convert to list, interpolate, then convert back
        spectrum_list = FrequencyBandManager.convert_spectrum_dict_to_list(spectrum_dict)
        
        # Simple linear interpolation for missing values (zeros)
        for i in range(len(spectrum_list)):
            if spectrum_list[i] == 0.0:
                # Find nearest non-zero neighbors
                left_val, right_val = 0.0, 0.0
                left_idx, right_idx = -1, -1
                
                # Look left
                for j in range(i - 1, -1, -1):
                    if spectrum_list[j] > 0:
                        left_val = spectrum_list[j]
                        left_idx = j
                        break
                        
                # Look right
                for j in range(i + 1, len(spectrum_list)):
                    if spectrum_list[j] > 0:
                        right_val = spectrum_list[j]
                        right_idx = j
                        break
                
                # Interpolate
                if left_idx >= 0 and right_idx >= 0:
                    # Linear interpolation
                    weight = (i - left_idx) / (right_idx - left_idx)
                    spectrum_list[i] = left_val + weight * (right_val - left_val)
                elif left_idx >= 0:
                    spectrum_list[i] = left_val
                elif right_idx >= 0:
                    spectrum_list[i] = right_val
        
        return FrequencyBandManager.convert_list_to_spectrum_dict(spectrum_list)


class NCRatingUtils:
    """Utilities specific to NC rating analysis and compliance"""
    
    # Space type to recommended NC rating mapping
    SPACE_TYPE_NC_RECOMMENDATIONS = {
        'private_office': 30,
        'executive_office': 25,
        'conference_room': 25,
        'open_office': 35,
        'classroom': 30,
        'library': 25,
        'restaurant': 40,
        'retail': 40,
        'lobby': 35,
        'auditorium': 25,
        'hospital_room': 30,
        'laboratory': 45,
        'workshop': 50,
        'mechanical_room': 60
    }
    
    @staticmethod
    def get_nc_description(nc_rating: int) -> str:
        """
        Get human-readable description of NC rating
        
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
            40: "Noisy - Cafeterias, workshops",
            45: "Very noisy - Workshops, mechanical rooms",
            50: "Extremely noisy - Gymnasiums, industrial spaces",
            55: "Unacceptable for most occupied spaces",
            60: "Unacceptable for occupied spaces",
            65: "Hearing protection recommended"
        }
        
        # Find closest NC rating
        closest_nc = min(descriptions.keys(), key=lambda x: abs(x - nc_rating))
        return descriptions.get(closest_nc, "Unknown criteria")
    
    @staticmethod
    def get_recommended_nc_for_space(space_type: str) -> Optional[int]:
        """
        Get recommended NC rating for a space type
        
        Args:
            space_type: Type of space
            
        Returns:
            Recommended NC rating or None if not found
        """
        space_key = space_type.lower().replace(' ', '_').replace('-', '_')
        return NCRatingUtils.SPACE_TYPE_NC_RECOMMENDATIONS.get(space_key)
    
    @staticmethod
    def analyze_nc_compliance(measured_spectrum: List[float], 
                            target_nc: int) -> Dict[str, Any]:
        """
        Analyze NC compliance for measured spectrum
        
        Args:
            measured_spectrum: Measured octave band levels
            target_nc: Target NC rating
            
        Returns:
            Dictionary with compliance analysis
        """
        actual_nc = SpectrumProcessor.calculate_nc_rating(measured_spectrum)
        meets_target = actual_nc <= target_nc
        
        # Find exceedances
        exceedances = []
        if target_nc in AcousticConstants.NC_CURVES:
            target_curve = AcousticConstants.NC_CURVES[target_nc]
            for i, (measured, limit) in enumerate(zip(measured_spectrum, target_curve)):
                if measured > limit:
                    freq = AcousticConstants.FREQUENCY_BANDS[i]
                    exceedance = measured - limit
                    exceedances.append((freq, exceedance))
        
        return {
            'actual_nc_rating': actual_nc,
            'target_nc_rating': target_nc,
            'meets_target': meets_target,
            'exceedances': exceedances,
            'nc_description': NCRatingUtils.get_nc_description(actual_nc),
            'measured_dba': SpectrumProcessor.calculate_dba_from_spectrum(measured_spectrum),
            'improvement_needed': max(0, actual_nc - target_nc)
        }


# Convenience functions for backward compatibility
def calculate_dba_from_spectrum(spectrum: List[float]) -> float:
    """Convenience function for A-weighted level calculation"""
    return SpectrumProcessor.calculate_dba_from_spectrum(spectrum)


def combine_noise_levels(level1: float, level2: float) -> float:
    """Convenience function for noise level combination"""
    return SpectrumProcessor.combine_noise_levels(level1, level2)


def calculate_nc_rating(spectrum: List[float]) -> int:
    """Convenience function for NC rating calculation"""
    return SpectrumProcessor.calculate_nc_rating(spectrum)


def get_nc_description(nc_rating: int) -> str:
    """Convenience function for NC rating description"""
    return NCRatingUtils.get_nc_description(nc_rating)


# Export all classes and constants for easy importing
__all__ = [
    'AcousticConstants',
    'SpectrumProcessor', 
    'FrequencyBandManager',
    'NCRatingUtils',
    'calculate_dba_from_spectrum',
    'combine_noise_levels',
    'calculate_nc_rating',
    'get_nc_description'
]