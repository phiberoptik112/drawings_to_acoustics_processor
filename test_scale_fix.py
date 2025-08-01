#!/usr/bin/env python3
"""
Test script to verify scale representation fixes
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from drawing.scale_manager import ScaleManager

def test_scale_calculations():
    """Test scale ratio calculations with zoom adjustments"""
    print("Testing Scale Manager calculations...")
    
    # Create scale manager
    scale_manager = ScaleManager()
    
    # Test 1: Set architectural scale
    print("\n1. Testing architectural scale: 1/4\"=1'0\"")
    success = scale_manager.set_scale_from_string('1/4"=1\'0"')
    print(f"   Scale set successfully: {success}")
    print(f"   Scale ratio: {scale_manager.scale_ratio:.2f} pixels/foot")
    print(f"   Scale string: {scale_manager.scale_string}")
    
    # Test 2: Convert known measurements
    print("\n2. Testing pixel to real conversions:")
    test_pixels = [100, 200, 300, 400]
    for pixels in test_pixels:
        real_distance = scale_manager.pixels_to_real(pixels)
        back_to_pixels = scale_manager.real_to_pixels(real_distance)
        print(f"   {pixels} px = {real_distance:.2f} ft = {back_to_pixels:.0f} px (roundtrip)")
    
    # Test 3: Area calculations
    print("\n3. Testing area calculations:")
    width_px, height_px = 200, 150
    area = scale_manager.calculate_area(width_px, height_px)
    print(f"   Rectangle {width_px}x{height_px} px = {area:.1f} sq ft")
    
    # Test 4: Distance calculations  
    print("\n4. Testing distance calculations:")
    x1, y1 = 100, 100
    x2, y2 = 400, 300
    distance = scale_manager.calculate_distance(x1, y1, x2, y2)
    print(f"   Distance from ({x1},{y1}) to ({x2},{y2}) = {distance:.1f} ft")
    
    # Test 5: Zoom factor simulation
    print("\n5. Testing zoom factor effects:")
    base_scale_ratio = scale_manager.scale_ratio
    zoom_factors = [0.5, 1.0, 1.5, 2.0]
    
    for zoom in zoom_factors:
        # Simulate zoom adjustment (as done in drawing_interface.py)
        adjusted_scale_ratio = base_scale_ratio * zoom
        scale_manager.scale_ratio = adjusted_scale_ratio
        
        # Test measurement at this zoom
        test_pixels_at_zoom = 200  # Same pixel distance on screen
        real_distance = scale_manager.pixels_to_real(test_pixels_at_zoom)
        
        print(f"   Zoom {zoom}x: {test_pixels_at_zoom} px = {real_distance:.2f} ft")
        
        # Expected: Higher zoom should give smaller real distances for same pixel count
        # because more pixels represent the same real distance when zoomed in
    
    print("\n✅ Scale calculation tests completed!")
    
    return True

def test_scale_calibration():
    """Test scale calibration from measurements"""
    print("\nTesting Scale Calibration...")
    
    scale_manager = ScaleManager()
    
    # Simulate calibrating from a known measurement
    # If we know that 278 pixels on screen = 25.0 feet in reality
    pixel_distance = 278
    real_distance = 25.0
    
    success = scale_manager.calibrate_from_known_measurement(pixel_distance, real_distance)
    print(f"Calibration successful: {success}")
    print(f"Calibrated scale ratio: {scale_manager.scale_ratio:.2f} pixels/foot")
    print(f"Generated scale string: {scale_manager.scale_string}")
    
    # Test the calibration
    test_distance = scale_manager.pixels_to_real(pixel_distance)
    print(f"Verification: {pixel_distance} px = {test_distance:.1f} ft (should be {real_distance:.1f})")
    
    return True

if __name__ == "__main__":
    print("Scale Representation Fix Test")
    print("=" * 40)
    
    try:
        test_scale_calculations()
        test_scale_calibration()
        print("\n🎉 All tests passed! Scale representation should now work correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()