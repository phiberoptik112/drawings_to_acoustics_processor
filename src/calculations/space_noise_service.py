"""
Space Noise Service - Handles mechanical background noise calculations for spaces.

This service extracts the calculation logic from Space.calculate_mechanical_background_noise()
to improve testability and separation of concerns.
"""

import logging
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Standard octave band frequencies
STANDARD_BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]


@dataclass
class NoiseCalculationResult:
    """Result of a space mechanical noise calculation"""
    nc_rating: Optional[int]
    sound_pressure_levels: Dict[int, float]
    paths_analyzed: int
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        result = {
            'nc_rating': self.nc_rating,
            'sound_pressure_levels': self.sound_pressure_levels,
            'paths_analyzed': self.paths_analyzed,
            'success': self.success
        }
        if self.error:
            result['error'] = self.error
        return result


class SpaceNoiseService:
    """Service for calculating mechanical background noise in spaces."""

    def __init__(self):
        """Initialize the service with required calculators."""
        from calculations.hvac_path_calculator import HVACPathCalculator
        self.path_calculator = HVACPathCalculator()

    def calculate_space_noise(self, space) -> NoiseCalculationResult:
        """Calculate mechanical background noise from HVAC paths serving a space.

        Args:
            space: Space model instance with hvac_paths relationship

        Returns:
            NoiseCalculationResult with NC rating, spectrum, and analysis details
        """
        if not space.hvac_paths:
            return NoiseCalculationResult(
                nc_rating=None,
                sound_pressure_levels={},
                paths_analyzed=0,
                success=False,
                error='No HVAC paths found serving this space'
            )

        total_energy_by_freq = {freq: 0.0 for freq in STANDARD_BANDS}
        paths_analyzed = 0

        for path in space.hvac_paths:
            try:
                spectrum = self._calculate_path_spectrum(path)
                if spectrum:
                    self._accumulate_energy(total_energy_by_freq, spectrum)
                    paths_analyzed += 1
            except Exception as e:
                logger.error(f"Error calculating noise for path {getattr(path, 'id', '?')}: {e}")
                continue

        # Convert energy back to dB SPL
        final_sound_levels = self._energy_to_db(total_energy_by_freq)

        # Calculate NC rating
        nc_rating = self._calculate_nc_rating(final_sound_levels)

        return NoiseCalculationResult(
            nc_rating=nc_rating,
            sound_pressure_levels=final_sound_levels,
            paths_analyzed=paths_analyzed,
            success=True
        )

    def _calculate_path_spectrum(self, path) -> Optional[List[float]]:
        """Calculate the octave band spectrum for a single HVAC path.

        Args:
            path: HVACPath model instance

        Returns:
            List of 8 octave band levels, or None if calculation fails
        """
        from models import get_session
        from sqlalchemy.orm import selectinload
        from models.hvac import HVACPath, HVACSegment

        session = get_session()
        try:
            # Eager-load all required relationships
            db_path = (
                session.query(HVACPath)
                .options(
                    selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                    selectinload(HVACPath.primary_source),
                )
                .filter(HVACPath.id == getattr(path, 'id', None))
                .first()
            )
        finally:
            try:
                session.close()
            except Exception:
                pass

        if not db_path:
            return None

        # Build path data and calculate spectrum
        path_data = self.path_calculator.build_path_data_from_db(db_path)
        if not path_data:
            return None

        calc = self.path_calculator.noise_calculator.calculate_hvac_path_noise(path_data)
        return calc.get('octave_band_spectrum') or None

    def _accumulate_energy(self, total_energy: Dict[int, float], spectrum: List[float]) -> None:
        """Accumulate energy from a spectrum into the total energy dict.

        Energy addition: 10^(level/10) for each frequency band.

        Args:
            total_energy: Dictionary to accumulate into {freq: energy}
            spectrum: List of dB levels for each frequency band
        """
        for i, freq in enumerate(STANDARD_BANDS):
            if i < len(spectrum):
                level = float(spectrum[i] or 0.0)
                total_energy[freq] += 10 ** (level / 10.0)

    def _energy_to_db(self, energy_by_freq: Dict[int, float]) -> Dict[int, float]:
        """Convert accumulated energy back to dB levels.

        Args:
            energy_by_freq: Dictionary of {freq: energy}

        Returns:
            Dictionary of {freq: dB_level}
        """
        return {
            freq: 10 * math.log10(energy) if energy > 0 else 0.0
            for freq, energy in energy_by_freq.items()
        }

    def _calculate_nc_rating(self, sound_levels: Dict[int, float]) -> Optional[int]:
        """Calculate NC rating from octave band sound levels.

        Args:
            sound_levels: Dictionary of {freq: dB_level}

        Returns:
            NC rating as integer, or None if calculation fails
        """
        if not any(level > 0 for level in sound_levels.values()):
            return None

        try:
            from calculations.nc_rating_analyzer import OctaveBandData
            octave_data = OctaveBandData(
                freq_63=sound_levels.get(63, 0.0),
                freq_125=sound_levels.get(125, 0.0),
                freq_250=sound_levels.get(250, 0.0),
                freq_500=sound_levels.get(500, 0.0),
                freq_1000=sound_levels.get(1000, 0.0),
                freq_2000=sound_levels.get(2000, 0.0),
                freq_4000=sound_levels.get(4000, 0.0),
                freq_8000=sound_levels.get(8000, 0.0),
            )

            if hasattr(self.path_calculator, 'nc_analyzer'):
                nc_results = self.path_calculator.nc_analyzer.analyze_nc_rating(octave_data)
                if nc_results and isinstance(nc_results, dict):
                    return nc_results.get('nc_rating')

            # Fallback to noise calculator
            spectrum_list = [sound_levels.get(f, 0.0) for f in STANDARD_BANDS]
            return self.path_calculator.noise_calculator.calculate_nc_rating(spectrum_list)

        except Exception as e:
            logger.error(f"Error calculating NC rating: {e}")
            return None


# Module-level singleton for convenience
_service_instance: Optional[SpaceNoiseService] = None


def get_space_noise_service() -> SpaceNoiseService:
    """Get the singleton SpaceNoiseService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = SpaceNoiseService()
    return _service_instance


def calculate_space_mechanical_noise(space) -> Dict[str, Any]:
    """Convenience function to calculate mechanical noise for a space.

    This function provides backward compatibility with the old
    Space.calculate_mechanical_background_noise() method.

    Args:
        space: Space model instance

    Returns:
        Dictionary with nc_rating, sound_pressure_levels, paths_analyzed, success
    """
    service = get_space_noise_service()
    result = service.calculate_space_noise(space)
    return result.to_dict()
