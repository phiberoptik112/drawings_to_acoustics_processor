"""
Simple test script to verify End Reflection Loss (ERL) integration
"""
import os
import sys
sys.path.insert(0, '/Users/jakepfitsch/Documents/drawings_to_acoustics_processor')

# Enable debug output
os.environ['HVAC_DEBUG_EXPORT'] = '1'

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "hvac_noise_engine",
    "/Users/jakepfitsch/Documents/drawings_to_acoustics_processor/src/calculations/hvac_noise_engine.py"
)
hvac_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hvac_module)

HVACNoiseEngine = hvac_module.HVACNoiseEngine
PathElement = hvac_module.PathElement


def test_erl_calculation():
    """Test that ERL is properly calculated for terminal elements"""
    print("=" * 80)
    print("TESTING END REFLECTION LOSS (ERL) INTEGRATION")
    print("=" * 80)
    
    engine = HVACNoiseEngine()
    
    # Create a simple path with source, duct, and terminal
    path_elements = [
        # Source element
        PathElement(
            element_type='source',
            element_id='source_1',
            source_noise_level=50.0,
            octave_band_levels=[72.0, 70.0, 64.0, 59.0, 56.0, 52.0, 52.0, 52.0],
            flow_rate=100.0
        ),
        # Duct element (12" x 8" rectangular)
        PathElement(
            element_type='duct',
            element_id='duct_1',
            length=10.0,  # 10 feet
            width=12.0,   # 12 inches
            height=8.0,   # 8 inches
            duct_shape='rectangular',
            duct_type='sheet_metal',
            lining_thickness=0.0,
            flow_rate=100.0
        ),
        # Terminal element - dimensions should be propagated from duct
        PathElement(
            element_type='terminal',
            element_id='terminal_1',
            width=12.0,   # Should match last duct
            height=8.0,   # Should match last duct
            duct_shape='rectangular',
            room_volume=5000.0,
            room_absorption=100.0,
            termination_type='flush'  # Grille/diffuser termination
        )
    ]
    
    print("\nTest Case 1: Rectangular duct (12\" x 8\") with flush termination")
    print("-" * 80)
    result = engine.calculate_path_noise(path_elements, debug=True, origin='test', path_id='test_1')
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print(f"  Source dBA: {result.source_noise_dba:.2f}")
    print(f"  Terminal dBA: {result.terminal_noise_dba:.2f}")
    print(f"  Total Attenuation: {result.total_attenuation_dba:.2f} dB")
    print(f"  NC Rating: {result.nc_rating}")
    print(f"  Calculation Valid: {result.calculation_valid}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    
    # Check if ERL was applied
    terminal_result = None
    for elem_result in result.element_results:
        if elem_result.get('element_id') == 'terminal_1':
            terminal_result = elem_result
            break
    
    if terminal_result:
        print("\nTerminal Element Analysis:")
        att_dba = terminal_result.get('attenuation_dba', 0.0)
        att_spectrum = terminal_result.get('attenuation_spectrum', [])
        print(f"  Attenuation dBA: {att_dba:.2f}")
        if att_spectrum:
            print(f"  Attenuation Spectrum: {[f'{x:.2f}' for x in att_spectrum]}")
            if att_dba > 0:
                print("\n✅ SUCCESS: End Reflection Loss is being calculated!")
                print(f"   ERL is providing {att_dba:.2f} dB of attenuation at the terminal.")
            else:
                print("\n⚠️  WARNING: ERL attenuation is 0 dB")
        else:
            print("\n❌ FAILED: No attenuation spectrum found")
    else:
        print("\n❌ FAILED: Terminal element not found in results")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("The End Reflection Loss calculation is now integrated into the path")
    print("noise calculation for terminal elements.")
    print("\nKey changes made:")
    print("1. Added 'termination_type' field to PathElement (flush/free)")
    print("2. Terminal elements now inherit duct dimensions from last segment")
    print("3. Enhanced debug logging with DEBUG_ERL prefix")
    print("4. ERL attenuation is calculated based on duct size and termination type")
    print("\nLook for 'DEBUG_ERL:' lines in the output above to see detailed ERL calculations.")
    print("=" * 80)


if __name__ == '__main__':
    test_erl_calculation()

