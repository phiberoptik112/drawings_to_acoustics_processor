#!/usr/bin/env python3
"""
Test script to validate HVAC calculation pipeline with enhanced debugging
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_calculation_pipeline():
    """Test the HVAC calculation with sample data"""
    # Enable debug export for this test
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from calculations.noise_calculator import NoiseCalculator
        
        print("=== CALCULATION PIPELINE TEST ===")
        
        # Create sample path data similar to what we see in debug files
        path_data = {
            'source_component': {
                'component_type': 'RF',
                'noise_level': None,
                'octave_band_levels': [72.0, 72.0, 79.0, 74.0, 69.0, 71.0, 71.0, 59.0]
            },
            'terminal_component': {
                'component_type': 'grille',
                'noise_level': None
            },
            'segments': [
                {
                    'length': 11.9,
                    'duct_width': 12.0,
                    'duct_height': 8.0,
                    'diameter': 0,
                    'duct_shape': 'rectangular',
                    'duct_type': 'sheet_metal',
                    'insulation': None,
                    'lining_thickness': 0,
                    'fittings': [],
                    'flow_velocity': 800.0,
                    'flow_rate': 533.33,
                    'fitting_type': 'junction'
                },
                {
                    'length': 3.9,
                    'duct_width': 12.0,
                    'duct_height': 8.0,
                    'diameter': 0,
                    'duct_shape': 'rectangular',
                    'duct_type': 'sheet_metal',
                    'insulation': None,
                    'lining_thickness': 0,
                    'fittings': [],
                    'flow_velocity': 800.0,
                    'flow_rate': 533.33,
                    'fitting_type': 'elbow'
                },
                {
                    'length': 3.6,
                    'duct_width': 12.0,
                    'duct_height': 8.0,
                    'diameter': 0,
                    'duct_shape': 'rectangular',
                    'duct_type': 'sheet_metal',
                    'insulation': None,
                    'lining_thickness': 0,
                    'fittings': [],
                    'flow_velocity': 800.0,
                    'flow_rate': 533.33,
                    'fitting_type': 'elbow'
                }
            ]
        }
        
        # Create calculator and run calculation
        calculator = NoiseCalculator()
        result = calculator.calculate_hvac_path_noise(path_data, debug=True)
        
        print(f"\n=== FINAL TEST RESULTS ===")
        print(f"Calculation valid: {result.get('calculation_valid')}")
        print(f"Source noise: {result.get('source_noise')} dB(A)")
        print(f"Terminal noise: {result.get('terminal_noise')} dB(A)")
        print(f"NC rating: {result.get('nc_rating')}")
        print(f"Error: {result.get('error')}")
        print(f"Warnings: {result.get('warnings')}")
        print(f"Path segments count: {len(result.get('path_segments', []))}")
        
        # Check for specific issues
        if not result.get('calculation_valid'):
            print(f"\n!!! CALCULATION FAILED !!!")
            print(f"Error: {result.get('error')}")
            return False
            
        if result.get('terminal_noise') == 0.0:
            print(f"\n!!! WARNING: Terminal noise is 0.0 - possible calculation issue !!!")
            
        if len(result.get('path_segments', [])) == 0:
            print(f"\n!!! WARNING: No path segments in result - possible conversion issue !!!")
            
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_element_conversion():
    """Test the path data to element conversion"""
    os.environ['HVAC_DEBUG_EXPORT'] = '1'
    
    try:
        from calculations.noise_calculator import NoiseCalculator
        from calculations.hvac_noise_engine import PathElement
        
        print("\n=== ELEMENT CONVERSION TEST ===")
        
        calculator = NoiseCalculator()
        
        # Test with minimal path data
        path_data = {
            'source_component': {
                'component_type': 'RF',
                'noise_level': 75.0,
                'octave_band_levels': [72.0, 72.0, 79.0, 74.0, 69.0, 71.0, 71.0, 59.0]
            },
            'segments': [
                {
                    'length': 10.0,
                    'duct_width': 12.0,
                    'duct_height': 8.0,
                    'duct_shape': 'rectangular',
                    'duct_type': 'sheet_metal',
                    'flow_rate': 500.0
                }
            ],
            'terminal_component': {
                'component_type': 'grille'
            }
        }
        
        elements = calculator._convert_path_data_to_elements(path_data)
        
        print(f"Converted {len(elements)} elements:")
        for i, elem in enumerate(elements):
            print(f"  {i}: {elem.element_type} - {elem.element_id}")
            if elem.element_type == 'source':
                print(f"     noise_level: {elem.source_noise_level}")
                print(f"     octave_bands: {elem.octave_band_levels}")
            elif hasattr(elem, 'length') and elem.length > 0:
                print(f"     length: {elem.length}, flow_rate: {elem.flow_rate}")
                
        return True
        
    except Exception as e:
        print(f"ERROR in conversion test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Starting HVAC calculation debug tests...")
    
    # Run tests
    test1_result = test_element_conversion()
    test2_result = test_calculation_pipeline()
    
    print(f"\n=== TEST SUMMARY ===")
    print(f"Element conversion test: {'PASS' if test1_result else 'FAIL'}")
    print(f"Calculation pipeline test: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print("All tests PASSED - enhanced debugging should now provide better insights")
    else:
        print("Some tests FAILED - check the debug output above for issues")