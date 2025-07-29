"""
Scale Manager - Handle drawing scale and coordinate transformations
"""

import math
from PySide6.QtCore import QObject, Signal


class ScaleManager(QObject):
    """Manages drawing scale and coordinate transformations"""
    
    scale_changed = Signal(float, str)  # scale_ratio, scale_string
    
    def __init__(self):
        super().__init__()
        self.scale_ratio = 1.0  # Pixels per real-world unit
        self.scale_string = "1:100"  # Display string
        self.units = "feet"  # "feet" or "meters"
        
        # Page dimensions in pixels
        self.page_width_pixels = 0
        self.page_height_pixels = 0
        
    def set_page_dimensions(self, width_pixels, height_pixels):
        """Set the PDF page dimensions in pixels"""
        self.page_width_pixels = width_pixels
        self.page_height_pixels = height_pixels
        
    def set_scale_from_string(self, scale_string):
        """Set scale from string like '1:100'"""
        try:
            if ':' in scale_string:
                drawing_unit, real_unit = scale_string.split(':')
                drawing_unit = float(drawing_unit)
                real_unit = float(real_unit)
                
                if drawing_unit > 0 and real_unit > 0:
                    # This represents how many real-world units per drawing unit
                    # We'll need to calibrate this with actual pixel measurements
                    self.scale_string = scale_string
                    # Initial assumption - will be calibrated later
                    self.scale_ratio = 1.0 / real_unit
                    self.scale_changed.emit(self.scale_ratio, self.scale_string)
                    return True
                    
        except (ValueError, ZeroDivisionError):
            pass
            
        return False
        
    def set_scale_from_reference(self, pixel_distance, real_distance, real_units="feet"):
        """Set scale from a reference measurement"""
        if pixel_distance > 0 and real_distance > 0:
            self.scale_ratio = pixel_distance / real_distance
            self.units = real_units
            
            # Calculate scale string
            pixels_per_unit = self.scale_ratio
            if pixels_per_unit > 1:
                scale_ratio = 1 / pixels_per_unit
                self.scale_string = f"1:{scale_ratio:.0f}"
            else:
                scale_ratio = pixels_per_unit
                self.scale_string = f"{scale_ratio:.2f}:1"
                
            self.scale_changed.emit(self.scale_ratio, self.scale_string)
            return True
            
        return False
        
    def pixels_to_real(self, pixels):
        """Convert pixels to real-world units"""
        if self.scale_ratio > 0:
            return pixels / self.scale_ratio
        return 0
        
    def real_to_pixels(self, real_units):
        """Convert real-world units to pixels"""
        return real_units * self.scale_ratio
        
    def calculate_distance(self, x1, y1, x2, y2):
        """Calculate real-world distance between two pixel points"""
        pixel_distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        return self.pixels_to_real(pixel_distance)
        
    def calculate_area(self, width_pixels, height_pixels):
        """Calculate real-world area from pixel dimensions"""
        width_real = self.pixels_to_real(width_pixels)
        height_real = self.pixels_to_real(height_pixels)
        return width_real * height_real
        
    def get_scale_info(self):
        """Get current scale information"""
        return {
            'scale_ratio': self.scale_ratio,
            'scale_string': self.scale_string,
            'units': self.units,
            'pixels_per_unit': self.scale_ratio,
            'units_per_pixel': 1.0 / self.scale_ratio if self.scale_ratio > 0 else 0
        }
        
    def format_distance(self, distance):
        """Format distance with appropriate units"""
        if self.units == "feet":
            if distance >= 1:
                return f"{distance:.1f} ft"
            else:
                inches = distance * 12
                return f"{inches:.1f} in"
        else:  # meters
            if distance >= 1:
                return f"{distance:.2f} m"
            else:
                cm = distance * 100
                return f"{cm:.1f} cm"
                
    def format_area(self, area):
        """Format area with appropriate units"""
        if self.units == "feet":
            return f"{area:.0f} sf"
        else:
            return f"{area:.2f} m²"


class ScaleCalibrationDialog:
    """Helper class for scale calibration methods"""
    
    @staticmethod
    def get_common_scales():
        """Get list of common architectural scales"""
        return [
            "1:20", "1:25", "1:50", "1:75", "1:100", 
            "1:125", "1:150", "1:200", "1:250", "1:500",
            "1:1000", "1:1250", "1:2500", "1:5000"
        ]
        
    @staticmethod
    def calculate_scale_from_known_dimension(known_length_real, known_length_pixels):
        """Calculate scale from a known dimension"""
        if known_length_pixels > 0 and known_length_real > 0:
            scale_ratio = known_length_pixels / known_length_real
            
            # Find closest standard scale
            common_scales = ScaleCalibrationDialog.get_common_scales()
            best_scale = "1:100"
            best_diff = float('inf')
            
            for scale_str in common_scales:
                _, denominator = scale_str.split(':')
                test_ratio = 1.0 / float(denominator)
                diff = abs(test_ratio - (1.0 / scale_ratio))
                
                if diff < best_diff:
                    best_diff = diff
                    best_scale = scale_str
                    
            return scale_ratio, best_scale
            
        return None, None