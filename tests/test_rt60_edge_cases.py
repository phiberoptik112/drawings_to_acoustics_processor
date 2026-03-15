"""
Edge case tests for RT60 calculators.

Tests cover:
- Zero and negative volumes
- Zero and negative surface areas
- Extreme absorption coefficients (0.0, 1.0)
- Missing materials in database
- Empty surface lists
- Extremely large and small rooms
- Invalid input types
"""

import sys
import os
import math
import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from calculations.rt60_calculator import RT60Calculator, calculate_simple_rt60
from calculations.enhanced_rt60_calculator import EnhancedRT60Calculator
from calculations.acoustic_constants import (
    SABINE_CONSTANT_IMPERIAL, RT60_INVALID_VALUE, MAX_ABSORPTION_COEFFICIENT
)


class TestRT60CalculatorEdgeCases:
    """Edge case tests for RT60Calculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = RT60Calculator()

    # Volume edge cases

    def test_zero_volume_returns_error(self):
        """Test that zero volume returns appropriate error."""
        space_data = {
            'volume': 0,
            'floor_area': 100,
            'wall_area': 200,
            'ceiling_area': 100,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        assert 'error' in result
        assert result['rt60'] == 0 or 'Invalid volume' in result.get('error', '')

    def test_negative_volume_returns_error(self):
        """Test that negative volume returns appropriate error."""
        space_data = {
            'volume': -1000,
            'floor_area': 100,
            'wall_area': 200,
            'ceiling_area': 100,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        assert 'error' in result or result['rt60'] == 0

    def test_extremely_large_volume(self):
        """Test calculation with extremely large volume (>1M cubic feet)."""
        space_data = {
            'volume': 2000000,  # 2 million cubic feet
            'floor_area': 50000,
            'wall_area': 100000,
            'ceiling_area': 50000,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should still calculate, just with high RT60
        assert 'rt60' in result
        if 'error' not in result:
            assert result['rt60'] > 0
            assert result['rt60'] < 100  # Reasonable upper bound

    def test_extremely_small_volume(self):
        """Test calculation with extremely small volume (<10 cubic feet)."""
        space_data = {
            'volume': 5,  # 5 cubic feet (tiny closet)
            'floor_area': 2,
            'wall_area': 8,
            'ceiling_area': 2,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should calculate with very low RT60
        assert 'rt60' in result
        if 'error' not in result:
            assert result['rt60'] >= 0

    # Surface area edge cases

    def test_zero_floor_area(self):
        """Test calculation with zero floor area."""
        space_data = {
            'volume': 1000,
            'floor_area': 0,
            'wall_area': 200,
            'ceiling_area': 100,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should still work with remaining surfaces
        assert 'rt60' in result

    def test_negative_surface_area(self):
        """Test that negative surface areas are handled gracefully."""
        space_data = {
            'volume': 1000,
            'floor_area': -100,  # Invalid
            'wall_area': 200,
            'ceiling_area': 100,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should handle gracefully (skip negative areas)
        assert 'rt60' in result

    def test_all_zero_surface_areas(self):
        """Test calculation when all surface areas are zero."""
        space_data = {
            'volume': 1000,
            'floor_area': 0,
            'wall_area': 0,
            'ceiling_area': 0,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should return error or invalid value
        assert 'error' in result or result['rt60'] == RT60_INVALID_VALUE

    # Absorption coefficient edge cases

    def test_zero_absorption_all_surfaces(self):
        """Test calculation when all surfaces have zero absorption."""
        # Create surfaces with explicit zero coefficients
        surfaces = [
            {'area': 100, 'material_key': 'nonexistent_material_zero_absorption'}
        ]

        total_absorption = self.calculator.calculate_total_absorption(surfaces)

        # Unknown materials should return 0 absorption
        assert total_absorption == 0.0

    def test_sabine_with_zero_absorption(self):
        """Test Sabine formula with zero absorption returns infinity."""
        rt60 = self.calculator.calculate_rt60_sabine(1000, 0)

        assert rt60 == float('inf')

    def test_sabine_with_negative_absorption(self):
        """Test Sabine formula with negative absorption returns infinity."""
        rt60 = self.calculator.calculate_rt60_sabine(1000, -100)

        assert rt60 == float('inf')

    def test_eyring_with_unity_absorption(self):
        """Test Eyring formula handles absorption coefficient of 1.0."""
        # When α = 1.0, log(1-α) = log(0) = undefined
        # Calculator should clamp to 0.99
        surfaces = [
            {'area': 100, 'material_key': 'test_high_absorption',
             'absorption_coefficients': {250: 1.0, 500: 1.0, 1000: 1.0, 2000: 1.0}}
        ]

        # This test verifies the calculator doesn't crash
        rt60 = self.calculator.calculate_rt60_eyring(1000, surfaces)

        # Should return a valid value (clamped) or infinity
        assert rt60 >= 0 or rt60 == float('inf')

    # Material database edge cases

    def test_missing_material_returns_zero_absorption(self):
        """Test that missing material returns zero absorption."""
        absorption = self.calculator.calculate_surface_absorption(
            100, 'completely_nonexistent_material_xyz'
        )

        assert absorption == 0.0

    def test_none_material_key(self):
        """Test that None material key is handled."""
        absorption = self.calculator.calculate_surface_absorption(100, None)

        assert absorption == 0.0

    def test_empty_string_material_key(self):
        """Test that empty string material key is handled."""
        absorption = self.calculator.calculate_surface_absorption(100, '')

        assert absorption == 0.0

    def test_space_with_all_invalid_materials(self):
        """Test space calculation with all invalid materials."""
        space_data = {
            'volume': 1000,
            'floor_area': 100,
            'wall_area': 200,
            'ceiling_area': 100,
            'ceiling_material': 'invalid_material_1',
            'wall_material': 'invalid_material_2',
            'floor_material': 'invalid_material_3'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should return error or invalid value since no valid surfaces
        assert 'error' in result or result['rt60'] == RT60_INVALID_VALUE

    # Empty and None input cases

    def test_empty_surfaces_list(self):
        """Test calculation with empty surfaces list."""
        total_absorption = self.calculator.calculate_total_absorption([])

        assert total_absorption == 0.0

    def test_none_volume_in_sabine(self):
        """Test Sabine formula with None volume."""
        rt60 = self.calculator.calculate_rt60_sabine(None, 100)

        assert rt60 == float('inf')

    def test_none_absorption_in_sabine(self):
        """Test Sabine formula with None absorption."""
        rt60 = self.calculator.calculate_rt60_sabine(1000, None)

        assert rt60 == float('inf')

    # Single surface cases

    def test_single_surface_only(self):
        """Test calculation with only one surface defined."""
        space_data = {
            'volume': 1000,
            'floor_area': 100,
            'wall_area': 0,
            'ceiling_area': 0,
            'ceiling_material': None,
            'wall_material': None,
            'floor_material': 'carpet'
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should calculate with single surface
        assert 'rt60' in result

    # Frequency-specific edge cases

    def test_invalid_frequency_returns_fallback(self):
        """Test that invalid frequency falls back to general coefficient."""
        # Use a material that exists in the database
        absorption = self.calculator.calculate_surface_absorption(
            100, 'acoustic_tile', frequency=999999  # Invalid frequency
        )

        # Should use fallback coefficient or return 0 for missing material
        assert absorption >= 0

    # Doors/windows edge cases

    def test_doors_windows_larger_than_wall_area(self):
        """Test when doors/windows area exceeds wall area."""
        space_data = {
            'volume': 1000,
            'floor_area': 100,
            'wall_area': 50,  # Small wall area
            'ceiling_area': 100,
            'ceiling_material': 'acoustic_tile',
            'wall_material': 'gypsum_board',
            'floor_material': 'carpet',
            'include_doors_windows': True,
            'doors_windows': [
                {'total_area': 100, 'material_key': 'glass', 'type': 'window',
                 'absorption_coefficients': {250: 0.05, 500: 0.04, 1000: 0.03, 2000: 0.02}}
            ]
        }
        result = self.calculator.calculate_space_rt60(space_data)

        # Should handle gracefully (effective wall area = 0)
        assert 'rt60' in result


class TestEnhancedRT60CalculatorEdgeCases:
    """Edge case tests for EnhancedRT60Calculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = EnhancedRT60Calculator()

    def test_zero_volume(self):
        """Test enhanced calculator with zero volume."""
        space_data = {
            'volume': 0,
            'surface_instances': [
                {'area': 100, 'material_key': 'acoustic_tile', 'surface_type': 'ceiling'}
            ]
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data)

        assert 'error' in result

    def test_negative_volume(self):
        """Test enhanced calculator with negative volume."""
        space_data = {
            'volume': -1000,
            'surface_instances': [
                {'area': 100, 'material_key': 'acoustic_tile', 'surface_type': 'ceiling'}
            ]
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data)

        assert 'error' in result

    def test_empty_surface_instances(self):
        """Test enhanced calculator with empty surface instances."""
        space_data = {
            'volume': 1000,
            'surface_instances': []
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data)

        assert 'error' in result

    def test_no_surface_instances_key(self):
        """Test enhanced calculator with missing surface_instances key."""
        space_data = {
            'volume': 1000
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data)

        assert 'error' in result

    def test_all_invalid_materials(self):
        """Test enhanced calculator with all invalid materials."""
        space_data = {
            'volume': 1000,
            'surface_instances': [
                {'area': 100, 'material_key': 'invalid_1', 'surface_type': 'ceiling'},
                {'area': 100, 'material_key': 'invalid_2', 'surface_type': 'wall'},
                {'area': 100, 'material_key': 'invalid_3', 'surface_type': 'floor'}
            ]
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data)

        # Should handle gracefully - zero absorption leads to high RT60
        assert 'rt60_by_frequency' in result

    def test_eyring_method_with_high_absorption(self):
        """Test Eyring method with high absorption surfaces."""
        # Create surfaces that would trigger the 0.99 clamp
        space_data = {
            'volume': 1000,
            'surface_instances': [
                {'area': 500, 'material_key': 'anechoic_wedges', 'surface_type': 'wall'}
            ]
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data, method='eyring')

        # Should not crash even if material doesn't exist
        assert 'rt60_by_frequency' in result

    def test_compliance_check_with_extreme_target(self):
        """Test compliance checking with extreme target RT60."""
        space_data = {
            'volume': 1000,
            'surface_instances': [
                {'area': 100, 'material_key': 'acoustic_tile', 'surface_type': 'ceiling'}
            ],
            'target_rt60': 0.001,  # Impossibly low target
            'target_tolerance': 0.0001
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data)

        # Should calculate but fail compliance
        assert result.get('overall_compliance', True) == False

    def test_average_rt60_with_all_invalid_values(self):
        """Test average RT60 calculation when all values are invalid."""
        rt60_by_freq = {125: 999.9, 250: 999.9, 500: 999.9, 1000: 999.9, 2000: 999.9, 4000: 999.9}

        avg = self.calculator._calculate_average_rt60(rt60_by_freq)

        # Should return 0 when all values are invalid
        assert avg == 0.0

    def test_surface_analysis_with_zero_area(self):
        """Test surface analysis with zero area surfaces."""
        space_data = {
            'volume': 1000,
            'surface_instances': [
                {'area': 0, 'material_key': 'acoustic_tile', 'surface_type': 'ceiling'},
                {'area': 100, 'material_key': 'gypsum_board', 'surface_type': 'wall'}
            ]
        }
        result = self.calculator.calculate_space_rt60_enhanced(space_data)

        # Should skip zero-area surfaces
        assert 'surface_analysis' in result


class TestSimpleRT60EdgeCases:
    """Edge case tests for calculate_simple_rt60 convenience function."""

    def test_zero_volume(self):
        """Test simple RT60 with zero volume."""
        result = calculate_simple_rt60(
            volume=0,
            floor_area=100,
            ceiling_height=10,
            materials={'ceiling': 'acoustic_tile', 'wall': 'gypsum_board', 'floor': 'carpet'}
        )

        assert 'error' in result or result['rt60'] == 0

    def test_zero_floor_area(self):
        """Test simple RT60 with zero floor area."""
        result = calculate_simple_rt60(
            volume=1000,
            floor_area=0,
            ceiling_height=10,
            materials={'ceiling': 'acoustic_tile', 'wall': 'gypsum_board', 'floor': 'carpet'}
        )

        # Zero floor area leads to zero wall area, should handle gracefully
        assert 'rt60' in result

    def test_zero_ceiling_height(self):
        """Test simple RT60 with zero ceiling height."""
        result = calculate_simple_rt60(
            volume=1000,
            floor_area=100,
            ceiling_height=0,
            materials={'ceiling': 'acoustic_tile', 'wall': 'gypsum_board', 'floor': 'carpet'}
        )

        # Zero height leads to zero wall area
        assert 'rt60' in result

    def test_empty_materials_dict(self):
        """Test simple RT60 with empty materials dict."""
        result = calculate_simple_rt60(
            volume=1000,
            floor_area=100,
            ceiling_height=10,
            materials={}
        )

        # Should handle empty materials - results in no valid surfaces
        assert 'rt60' in result or 'error' in result

    def test_none_materials(self):
        """Test simple RT60 with None material values."""
        result = calculate_simple_rt60(
            volume=1000,
            floor_area=100,
            ceiling_height=10,
            materials={'ceiling': None, 'wall': None, 'floor': None}
        )

        # Should handle None values
        assert 'rt60' in result or 'error' in result


class TestSabineConstantValidation:
    """Tests to validate Sabine constant usage."""

    def test_sabine_constant_value(self):
        """Verify Sabine constant is correct for imperial units."""
        assert SABINE_CONSTANT_IMPERIAL == 0.049

    def test_sabine_formula_basic(self):
        """Test basic Sabine formula calculation."""
        calculator = RT60Calculator()

        # Known values: 1000 cu.ft., 50 sabins absorption
        # RT60 = 0.049 * 1000 / 50 = 0.98 seconds
        rt60 = calculator.calculate_rt60_sabine(1000, 50)

        assert abs(rt60 - 0.98) < 0.01


class TestMaxAbsorptionClamp:
    """Tests for absorption coefficient clamping."""

    def test_max_absorption_constant(self):
        """Verify max absorption constant."""
        assert MAX_ABSORPTION_COEFFICIENT == 0.99

    def test_eyring_clamps_high_absorption(self):
        """Test that Eyring formula clamps absorption at 0.99."""
        calculator = RT60Calculator()

        # Create surfaces with absorption = 1.0 (should be clamped)
        surfaces = [
            {'area': 100, 'material_key': 'test',
             'absorption_coefficients': {500: 1.0}}
        ]

        # This should not raise an error (log(0) avoided by clamping)
        # We're testing that it doesn't crash
        try:
            rt60 = calculator.calculate_rt60_eyring(1000, surfaces)
            # If materials aren't in DB, returns inf; that's okay
            assert rt60 >= 0 or rt60 == float('inf')
        except (ValueError, ZeroDivisionError):
            pytest.fail("Eyring formula should clamp absorption to avoid math errors")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
