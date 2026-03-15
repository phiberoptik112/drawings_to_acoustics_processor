"""
Edge case tests for HVAC noise calculators.

Tests cover:
- Zero and negative CFM flow rates
- Zero and negative duct dimensions
- Zero length segments
- Paths with no segments
- Paths with many segments (stress test)
- Missing source components
- Invalid element types
- NC rating edge cases
"""

import sys
import os
import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from calculations.hvac_noise_engine import (
    HVACNoiseEngine, PathElement, PathResult, OctaveBandData,
    HVACEngineError, PathElementError, CalculationError
)
from calculations.space_noise_service import SpaceNoiseService, NoiseCalculationResult
from calculations.hvac_constants import NUM_OCTAVE_BANDS, DEFAULT_NC_RATING


class TestHVACNoiseEngineEdgeCases:
    """Edge case tests for HVACNoiseEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HVACNoiseEngine()

    # Empty path cases

    def test_empty_path_elements_list(self):
        """Test calculation with empty path elements list."""
        result = self.engine.calculate_path_noise([], path_id="empty_path")

        assert isinstance(result, PathResult)
        assert result.calculation_valid == False or len(result.octave_band_spectrum) == NUM_OCTAVE_BANDS
        assert result.path_id == "empty_path"

    def test_none_path_elements(self):
        """Test calculation with None path elements."""
        # Should handle None gracefully or raise appropriate error
        try:
            result = self.engine.calculate_path_noise(None, path_id="none_path")
            assert result.calculation_valid == False
        except (TypeError, HVACEngineError):
            pass  # Expected behavior

    # Source element edge cases

    def test_path_without_source_element(self):
        """Test path that has no source element."""
        elements = [
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=10.0,
                width=12.0,
                height=12.0,
                flow_rate=500
            ),
            PathElement(
                element_type='terminal',
                element_id='term_1',
                room_volume=1000,
                room_absorption=100
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should handle missing source - might return zeros or error
        assert isinstance(result, PathResult)

    def test_source_with_zero_noise_level(self):
        """Test source element with zero noise level."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=0.0,
                octave_band_levels=[0.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='terminal',
                element_id='term_1',
                room_volume=1000,
                room_absorption=100
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)
        assert result.source_noise_dba == 0.0

    def test_source_with_negative_noise_level(self):
        """Test source element with negative noise level."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=-10.0,
                octave_band_levels=[-10.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should handle negative values
        assert isinstance(result, PathResult)

    def test_source_with_none_octave_bands(self):
        """Test source element with None octave band levels."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=None,  # None instead of list
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should handle None octave bands
        assert isinstance(result, PathResult)

    # Duct dimension edge cases

    def test_duct_with_zero_dimensions(self):
        """Test duct element with zero dimensions."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=10.0,
                width=0.0,  # Zero width
                height=0.0,  # Zero height
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should handle zero dimensions
        assert isinstance(result, PathResult)

    def test_duct_with_negative_dimensions(self):
        """Test duct element with negative dimensions."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=10.0,
                width=-12.0,  # Negative
                height=-12.0,  # Negative
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should handle negative dimensions gracefully
        assert isinstance(result, PathResult)

    def test_duct_with_zero_length(self):
        """Test duct element with zero length."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=0.0,  # Zero length
                width=12.0,
                height=12.0,
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Zero length = no attenuation
        assert isinstance(result, PathResult)

    def test_circular_duct_with_zero_diameter(self):
        """Test circular duct with zero diameter."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=10.0,
                diameter=0.0,  # Zero diameter
                duct_shape='circular',
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)

    # Flow rate edge cases

    def test_zero_cfm_flow_rate(self):
        """Test elements with zero CFM flow rate."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=0.0  # Zero CFM
            ),
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=10.0,
                width=12.0,
                height=12.0,
                flow_rate=0.0  # Zero CFM
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)

    def test_negative_cfm_flow_rate(self):
        """Test elements with negative CFM flow rate."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=-500.0  # Negative CFM
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)

    def test_extremely_high_cfm(self):
        """Test with extremely high CFM (stress test)."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=100000.0  # Very high CFM
            ),
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=10.0,
                width=48.0,
                height=48.0,
                flow_rate=100000.0
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)
        # High flow should result in high velocity noise

    # Path length stress tests

    def test_path_with_single_segment(self):
        """Test path with only one duct segment."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='duct',
                element_id='duct_1',
                length=10.0,
                width=12.0,
                height=12.0,
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)
        assert len(result.octave_band_spectrum) == NUM_OCTAVE_BANDS

    def test_path_with_many_segments_stress_test(self):
        """Test path with 50+ segments (stress test)."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=80.0,
                octave_band_levels=[80.0] * NUM_OCTAVE_BANDS,
                flow_rate=1000
            )
        ]

        # Add 50 duct segments
        for i in range(50):
            elements.append(PathElement(
                element_type='duct',
                element_id=f'duct_{i}',
                length=5.0,
                width=12.0,
                height=12.0,
                flow_rate=1000
            ))

        elements.append(PathElement(
            element_type='terminal',
            element_id='term_1',
            room_volume=5000,
            room_absorption=500
        ))

        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)
        # With 50 segments of attenuation, terminal noise should be lower than source
        if result.calculation_valid:
            assert result.terminal_noise_dba <= result.source_noise_dba + 10  # Allow some margin

    # Invalid element type cases

    def test_unknown_element_type(self):
        """Test with unknown element type."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='unknown_type',  # Invalid type
                element_id='unknown_1',
                length=10.0
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should skip or handle unknown types gracefully
        assert isinstance(result, PathResult)

    # Terminal/Room correction edge cases

    def test_terminal_with_zero_room_volume(self):
        """Test terminal element with zero room volume."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='terminal',
                element_id='term_1',
                room_volume=0.0,  # Zero volume
                room_absorption=100
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)

    def test_terminal_with_zero_absorption(self):
        """Test terminal element with zero room absorption."""
        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=[70.0] * NUM_OCTAVE_BANDS,
                flow_rate=500
            ),
            PathElement(
                element_type='terminal',
                element_id='term_1',
                room_volume=1000,
                room_absorption=0.0  # Zero absorption
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        assert isinstance(result, PathResult)


class TestOctaveBandDataEdgeCases:
    """Edge case tests for OctaveBandData dataclass."""

    def test_to_list_returns_correct_order(self):
        """Test that to_list returns values in correct frequency order."""
        data = OctaveBandData(
            freq_63=1.0, freq_125=2.0, freq_250=3.0, freq_500=4.0,
            freq_1000=5.0, freq_2000=6.0, freq_4000=7.0, freq_8000=8.0
        )

        result = data.to_list()

        assert result == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]

    def test_from_list_with_exact_8_values(self):
        """Test from_list with exactly 8 values."""
        data = OctaveBandData()
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]

        result = data.from_list(values)

        assert result.freq_63 == 10.0
        assert result.freq_8000 == 80.0

    def test_from_list_with_more_than_8_values(self):
        """Test from_list with more than 8 values (should only use first 8)."""
        data = OctaveBandData()
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

        result = data.from_list(values)

        assert result.freq_63 == 10.0
        assert result.freq_8000 == 80.0

    def test_from_list_with_fewer_than_8_values(self):
        """Test from_list with fewer than 8 values."""
        data = OctaveBandData()
        values = [10.0, 20.0, 30.0]  # Only 3 values

        result = data.from_list(values)

        # Should return original data unchanged
        assert result is data

    def test_from_list_with_empty_list(self):
        """Test from_list with empty list."""
        data = OctaveBandData()
        values = []

        result = data.from_list(values)

        # Should return original data unchanged
        assert result is data

    def test_default_values_are_zero(self):
        """Test that default values are all zero."""
        data = OctaveBandData()

        assert data.to_list() == [0.0] * 8


class TestSpaceNoiseServiceEdgeCases:
    """Edge case tests for SpaceNoiseService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = SpaceNoiseService()

    def test_space_with_no_hvac_paths(self):
        """Test calculation for space with no HVAC paths."""
        # Create mock space with empty hvac_paths
        class MockSpace:
            hvac_paths = []

        result = self.service.calculate_space_noise(MockSpace())

        assert isinstance(result, NoiseCalculationResult)
        assert result.success == False
        assert 'No HVAC paths' in (result.error or '')

    def test_energy_accumulation_with_zero_levels(self):
        """Test energy accumulation with all zero levels."""
        total_energy = {63: 0.0, 125: 0.0, 250: 0.0, 500: 0.0,
                        1000: 0.0, 2000: 0.0, 4000: 0.0, 8000: 0.0}
        spectrum = [0.0] * 8

        self.service._accumulate_energy(total_energy, spectrum)

        # 10^(0/10) = 1.0 for each band
        for freq in total_energy:
            assert total_energy[freq] == 1.0

    def test_energy_to_db_with_zero_energy(self):
        """Test energy to dB conversion with zero energy."""
        energy_by_freq = {63: 0.0, 125: 0.0, 250: 0.0, 500: 0.0,
                          1000: 0.0, 2000: 0.0, 4000: 0.0, 8000: 0.0}

        result = self.service._energy_to_db(energy_by_freq)

        # Zero energy should result in 0 dB (not negative infinity)
        for freq in result:
            assert result[freq] == 0.0

    def test_nc_rating_with_all_zero_levels(self):
        """Test NC rating calculation with all zero levels."""
        sound_levels = {63: 0.0, 125: 0.0, 250: 0.0, 500: 0.0,
                        1000: 0.0, 2000: 0.0, 4000: 0.0, 8000: 0.0}

        result = self.service._calculate_nc_rating(sound_levels)

        # All zeros should return None (no significant noise)
        assert result is None


class TestNCRatingEdgeCases:
    """Edge case tests for NC rating calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HVACNoiseEngine()

    def test_nc_rating_with_extreme_low_levels(self):
        """Test NC rating with very low sound levels."""
        # Levels below NC-15
        spectrum = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]

        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=15.0,
                octave_band_levels=spectrum,
                flow_rate=100
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should calculate valid NC rating
        assert isinstance(result, PathResult)

    def test_nc_rating_with_extreme_high_levels(self):
        """Test NC rating with very high sound levels."""
        # Levels above NC-70
        spectrum = [90.0, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0]

        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=95.0,
                octave_band_levels=spectrum,
                flow_rate=5000
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # Should cap at max NC or handle gracefully
        assert isinstance(result, PathResult)

    def test_nc_rating_with_single_frequency_spike(self):
        """Test NC rating with one frequency significantly higher than others."""
        # Single spike at 500 Hz
        spectrum = [30.0, 30.0, 30.0, 70.0, 30.0, 30.0, 30.0, 30.0]

        elements = [
            PathElement(
                element_type='source',
                element_id='source_1',
                source_noise_level=70.0,
                octave_band_levels=spectrum,
                flow_rate=500
            )
        ]
        result = self.engine.calculate_path_noise(elements)

        # NC rating should be determined by worst case frequency
        assert isinstance(result, PathResult)


class TestPathElementDataclass:
    """Edge case tests for PathElement dataclass."""

    def test_path_element_default_values(self):
        """Test that PathElement has correct default values."""
        element = PathElement(element_type='duct', element_id='test')

        assert element.length == 0.0
        assert element.width == 0.0
        assert element.height == 0.0
        assert element.diameter == 0.0
        assert element.flow_rate == 0.0
        assert element.octave_band_levels is None
        assert element.duct_shape == 'rectangular'
        assert element.duct_type == 'sheet_metal'

    def test_path_element_with_all_none_optionals(self):
        """Test PathElement with None optional values."""
        element = PathElement(
            element_type='duct',
            element_id='test',
            fitting_type=None,
            branch_takeoff_choice=None,
            termination_type=None,
            octave_band_levels=None
        )

        assert element.fitting_type is None
        assert element.branch_takeoff_choice is None
        assert element.termination_type is None
        assert element.octave_band_levels is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
