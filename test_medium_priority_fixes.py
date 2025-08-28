#!/usr/bin/env python3
"""
Test Medium Priority Fixes Implementation
Validates the three medium priority fixes from HVAC_CALCULATIONS_ANALYSIS_AND_FIXES.md
"""

import sys
import os
sys.path.append('src')

def test_debug_logging_framework():
    """Test Fix 7: Debug Output Standardization"""
    print("🧪 Testing Debug Output Standardization...")
    
    try:
        from src.calculations.debug_logger import debug_logger, HVACDebugLogger
        
        # Test singleton pattern
        logger1 = HVACDebugLogger()
        logger2 = HVACDebugLogger()
        assert logger1 is logger2, "Debug logger should be singleton"
        
        # Test centralized logging methods
        debug_logger.info('TestComponent', 'Testing info message', {'test_data': 'value'})
        debug_logger.debug('TestComponent', 'Testing debug message')
        debug_logger.warning('TestComponent', 'Testing warning message')
        debug_logger.error('TestComponent', 'Testing error message', Exception('Test error'))
        
        # Test specialized logging methods
        debug_logger.log_calculation_start('TestComponent', 'test_calculation', 123)
        debug_logger.log_calculation_end('TestComponent', 'test_calculation', True, {'result': 'success'})
        debug_logger.log_element_processing('TestComponent', 'test_element', 'element_1', 
                                           input_spectrum=[50.0]*8, output_spectrum=[45.0]*8)
        debug_logger.log_validation_result('TestComponent', True, [], ['minor warning'])
        
        print("✅ Debug logging framework working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Debug logging framework failed: {e}")
        return False

def test_return_type_consistency():
    """Test Fix 8: Return Type Consistency"""
    print("🧪 Testing Return Type Consistency...")
    
    try:
        from src.calculations.result_types import CalculationResult, ResultStatus, OperationResult
        
        # Test CalculationResult creation
        success_result = CalculationResult.success("test data", warnings=["warning1"])
        assert success_result.is_success, "Should be success"
        assert success_result.data == "test data", "Should contain data"
        assert len(success_result.warnings) == 1, "Should have one warning"
        
        error_result = CalculationResult.error("Test error message")
        assert error_result.is_error, "Should be error"
        assert error_result.error_message == "Test error message", "Should contain error message"
        
        validation_result = CalculationResult.validation_failed("Validation failed", ["error1"])
        assert validation_result.status == ResultStatus.VALIDATION_FAILED, "Should be validation failed"
        
        # Test OperationResult
        op_success = OperationResult.success_result("Operation completed")
        assert op_success.success, "Should be successful"
        
        op_error = OperationResult.error_result("Operation failed")
        assert not op_error.success, "Should be error"
        
        print("✅ Return type consistency framework working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Return type consistency failed: {e}")
        return False

def test_magic_numbers_constants():
    """Test Fix 9: Replace Magic Numbers with Named Constants"""
    print("🧪 Testing Magic Numbers Replacement...")
    
    try:
        from src.calculations.hvac_constants import (
            NUM_OCTAVE_BANDS, DEFAULT_DUCT_WIDTH_IN, DEFAULT_DUCT_HEIGHT_IN,
            DEFAULT_FLOW_VELOCITY_FPM, FREQUENCY_BAND_LABELS, DEFAULT_SPECTRUM_LEVELS,
            NC_CURVE_DATA, MIN_NC_RATING, MAX_NC_RATING,
            is_valid_frequency_spectrum, is_valid_sound_level, is_valid_nc_rating,
            inches_to_feet, feet_to_inches, circular_area_from_diameter
        )
        
        # Test basic constants
        assert NUM_OCTAVE_BANDS == 8, "Should have 8 octave bands"
        assert len(FREQUENCY_BAND_LABELS) == 8, "Should have 8 frequency labels"
        assert len(DEFAULT_SPECTRUM_LEVELS) == 8, "Should have 8 default spectrum levels"
        assert DEFAULT_DUCT_WIDTH_IN == 12.0, "Default duct width should be 12 inches"
        assert DEFAULT_FLOW_VELOCITY_FPM == 800.0, "Default velocity should be 800 FPM"
        
        # Test NC curve data
        assert MIN_NC_RATING in NC_CURVE_DATA, "Min NC rating should be in curve data"
        assert MAX_NC_RATING in NC_CURVE_DATA, "Max NC rating should be in curve data"
        assert len(NC_CURVE_DATA[30]) == 8, "NC-30 curve should have 8 frequency bands"
        
        # Test validation helpers
        assert is_valid_frequency_spectrum([50.0]*8), "Should validate correct spectrum"
        assert not is_valid_frequency_spectrum([50.0]*7), "Should reject incorrect length"
        assert is_valid_sound_level(60.0), "Should validate reasonable sound level"
        assert not is_valid_sound_level(-10.0), "Should reject negative sound level"
        assert is_valid_nc_rating(30), "Should validate NC-30"
        assert not is_valid_nc_rating(100), "Should reject NC-100"
        
        # Test unit conversion helpers
        assert inches_to_feet(12.0) == 1.0, "12 inches should equal 1 foot"
        assert feet_to_inches(1.0) == 12.0, "1 foot should equal 12 inches"
        area = circular_area_from_diameter(12.0)
        assert area > 0, "Circular area should be positive"
        
        print("✅ Magic numbers constants working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Magic numbers constants failed: {e}")
        return False

def test_integration_with_calculation_engines():
    """Test integration of fixes with actual calculation engines"""
    print("🧪 Testing Integration with Calculation Engines...")
    
    try:
        from src.calculations.hvac_constants import NUM_OCTAVE_BANDS, DEFAULT_SPECTRUM_LEVELS
        
        # Test that HVAC noise engine uses constants
        from src.calculations.hvac_noise_engine import HVACNoiseEngine, PathElement
        
        engine = HVACNoiseEngine()
        
        # Create a simple path element
        source_element = PathElement(
            element_type='source',
            element_id='test_source',
            source_noise_level=60.0,
            octave_band_levels=DEFAULT_SPECTRUM_LEVELS.copy()
        )
        
        # Test that the engine can process elements with our constants
        result = engine.calculate_path_noise([source_element])
        assert result is not None, "Engine should return result"
        assert hasattr(result, 'octave_band_spectrum'), "Result should have octave band spectrum"
        assert len(result.octave_band_spectrum) == NUM_OCTAVE_BANDS, "Spectrum should have correct length"
        
        print("✅ Integration with calculation engines working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Integration with calculation engines failed: {e}")
        return False

def test_path_calculator_integration():
    """Test integration with path calculator"""
    print("🧪 Testing Path Calculator Integration...")
    
    try:
        from src.calculations.hvac_path_calculator import HVACPathCalculator
        from src.calculations.result_types import CalculationResult
        from src.calculations.hvac_constants import DEFAULT_DUCT_WIDTH_IN
        
        # Create calculator instance
        calculator = HVACPathCalculator(project_id=1)
        
        # Test that it has debug logger
        assert hasattr(calculator, 'debug_logger'), "Calculator should have debug logger"
        
        # Test creating path with invalid data should return CalculationResult
        invalid_data = {'components': [], 'segments': []}  # Not enough components
        
        result = calculator.create_hvac_path_from_drawing(1, invalid_data)
        assert isinstance(result, CalculationResult), "Should return CalculationResult"
        assert result.is_error, "Should be error result for invalid data"
        
        print("✅ Path calculator integration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Path calculator integration failed: {e}")
        return False

def main():
    """Run all medium priority fix tests"""
    print("🚀 Testing Medium Priority Fixes Implementation")
    print("=" * 60)
    
    tests = [
        test_debug_logging_framework,
        test_return_type_consistency,
        test_magic_numbers_constants,
        test_integration_with_calculation_engines,
        test_path_calculator_integration
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 60)
    print(f"📋 Test Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 All medium priority fixes implemented successfully!")
        return 0
    else:
        print("⚠️ Some tests failed. Check implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())