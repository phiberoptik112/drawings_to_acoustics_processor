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
        """Set scale from string like '1:100' or '1/8\"=1\\'0\"'"""
        try:
            # Handle architectural scales like 1/8"=1'0"
            if '=' in scale_string and ('"' in scale_string or "'" in scale_string):
                success = self._parse_architectural_scale(scale_string)
                if success and hasattr(self, '_calibrated_pixels_per_inch'):
                    # Use calibrated pixel ratio if available
                    self._apply_calibrated_scale()
                return success
            
            # Handle ratio scales like 1:100
            elif ':' in scale_string:
                drawing_unit, real_unit = scale_string.split(':')
                drawing_unit = float(drawing_unit)
                real_unit = float(real_unit)
                
                if drawing_unit > 0 and real_unit > 0:
                    # This represents how many real-world units per drawing unit
                    self.scale_string = scale_string
                    # Use calibrated pixel ratio if available, otherwise default
                    if hasattr(self, '_calibrated_pixels_per_inch'):
                        # For ratio scales, assume typical document scales
                        self.scale_ratio = self._calibrated_pixels_per_inch / real_unit
                    else:
                        # Default assumption - will be calibrated later
                        self.scale_ratio = 100.0 / real_unit
                    self.scale_changed.emit(self.scale_ratio, self.scale_string)
                    return True
                    
        except (ValueError, ZeroDivisionError):
            pass
            
        return False
        
    def _parse_architectural_scale(self, scale_string):
        """Parse architectural scale strings like '1/8\"=1\\'0\"'"""
        try:
            # Clean up the string
            scale_string = scale_string.replace("'", "'").replace("'", "'")  # Normalize quotes
            scale_string = scale_string.replace('"', '"').replace('"', '"')  # Normalize quotes
            
            # Split on equals sign
            left_side, right_side = scale_string.split('=')
            
            # Parse left side (drawing units, typically inches)
            drawing_inches = self._parse_inches(left_side.strip())
            if drawing_inches is None:
                return False
                
            # Parse right side (real world units, typically feet and inches)
            real_inches = self._parse_inches(right_side.strip())
            if real_inches is None:
                return False
                
            # Convert to feet for consistency
            drawing_feet = drawing_inches / 12.0
            real_feet = real_inches / 12.0
            
            if drawing_feet > 0 and real_feet > 0:
                # Calculate scale factor (real units per drawing unit)
                scale_factor = real_feet / drawing_feet
                self.scale_string = scale_string
                self.units = "feet"
                # Store the scale factor for later pixel calibration
                self._architectural_scale_factor = scale_factor
                # Set initial scale ratio - this should be calibrated with actual measurements
                # Store the architectural scale factor for later calibration
                # For now, use a reasonable default that will be overridden by calibration
                self.scale_ratio = 10.0  # Default placeholder - will be calibrated
                self._needs_calibration = True
                self.scale_changed.emit(self.scale_ratio, self.scale_string)
                return True
                
        except (ValueError, ZeroDivisionError, AttributeError):
            pass
            
        return False
        
    def _parse_inches(self, dimension_str):
        """Parse dimension string like '1/8\"' or '1\\'6\"' and return total inches"""
        try:
            dimension_str = dimension_str.strip()
            total_inches = 0
            
            # Handle feet and inches like "1'6"" or "1'0""
            if "'" in dimension_str:
                parts = dimension_str.split("'")
                feet = float(parts[0]) if parts[0] else 0
                total_inches += feet * 12
                
                # Handle inches part after feet
                if len(parts) > 1:
                    inches_part = parts[1].replace('"', '').strip()
                    if inches_part:
                        total_inches += float(inches_part)
            
            # Handle just inches like "1/8"" or "6""
            elif '"' in dimension_str:
                inches_str = dimension_str.replace('"', '').strip()
                if '/' in inches_str:
                    # Handle fractions like "1/8"
                    numerator, denominator = inches_str.split('/')
                    total_inches = float(numerator) / float(denominator)
                else:
                    total_inches = float(inches_str)
            
            # Handle just numbers (assume inches)
            else:
                if '/' in dimension_str:
                    numerator, denominator = dimension_str.split('/')
                    total_inches = float(numerator) / float(denominator)
                else:
                    total_inches = float(dimension_str)
                    
            return total_inches
            
        except (ValueError, ZeroDivisionError):
            return None
        
    def set_scale_from_reference(self, pixel_distance, real_distance, real_units="feet"):
        """Set scale from a reference measurement"""
        if pixel_distance > 0 and real_distance > 0:
            self.scale_ratio = pixel_distance / real_distance
            self.units = real_units
            
            # If we have an architectural scale factor stored, use it to create proper scale string
            if hasattr(self, '_architectural_scale_factor') and self._architectural_scale_factor:
                # Keep the original architectural scale string format
                pass  # scale_string already set in _parse_architectural_scale
            else:
                # Calculate scale string for ratio formats
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
        
    def calibrate_from_known_measurement(self, pixel_distance, real_distance, scale_string=None):
        """Calibrate scale from a known measurement on the drawing"""
        if pixel_distance > 0 and real_distance > 0:
            # Calculate the actual scale ratio from the measurement
            self.scale_ratio = pixel_distance / real_distance
            self.units = "feet"  # Assuming feet for now
            
            # Clear the calibration flag
            self._needs_calibration = False
            
            # If we have an architectural scale factor, update the pixel-to-inch ratio
            if hasattr(self, '_architectural_scale_factor') and self._architectural_scale_factor:
                # Calculate pixels per inch on drawing from this calibration
                # real_distance feet = real_distance * 12 inches in reality
                # At architectural scale, this equals (real_distance * 12) / scale_factor inches on drawing
                # So pixel_distance pixels = ((real_distance * 12) / scale_factor) inches on drawing
                # Therefore: pixels per inch on drawing = pixel_distance / ((real_distance * 12) / scale_factor)
                drawing_inches = (real_distance * 12) / self._architectural_scale_factor
                self._calibrated_pixels_per_inch = pixel_distance / drawing_inches
                print(f"Calibrated: {self._calibrated_pixels_per_inch:.2f} pixels per inch on drawing")
            
            # If a scale string is provided, use it; otherwise generate one
            if scale_string:
                self.scale_string = scale_string
            else:
                # Generate a scale string based on the ratio
                if self.scale_ratio >= 1:
                    self.scale_string = f"{self.scale_ratio:.1f}:1"
                else:
                    self.scale_string = f"1:{1/self.scale_ratio:.0f}"
            
            self.scale_changed.emit(self.scale_ratio, self.scale_string)
            return True
            
        return False
        
    def _apply_calibrated_scale(self):
        """Apply calibrated pixel ratio to current architectural scale"""
        if hasattr(self, '_architectural_scale_factor') and hasattr(self, '_calibrated_pixels_per_inch'):
            # Recalculate scale ratio using calibrated pixel-to-inch ratio
            # scale_ratio = (pixels per inch on drawing) * (12 inches per foot) / scale_factor
            self.scale_ratio = (self._calibrated_pixels_per_inch * 12.0) / self._architectural_scale_factor
            self._needs_calibration = False
        
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
            # Common architectural scales (Imperial)
            '1/16"=1\'0"', '3/32"=1\'0"', '1/8"=1\'0"', '3/16"=1\'0"', 
            '1/4"=1\'0"', '3/8"=1\'0"', '1/2"=1\'0"', '3/4"=1\'0"',
            '1"=1\'0"', '1 1/2"=1\'0"', '3"=1\'0"',
            # Site plans
            '1"=10\'0"', '1"=20\'0"', '1"=30\'0"', '1"=40\'0"', '1"=50\'0"', '1"=100\'0"',
            # Legacy ratio scales
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
            best_scale = '1/4"=1\'0"'  # Default architectural scale
            best_diff = float('inf')
            
            for scale_str in common_scales:
                if '=' in scale_str:
                    # Handle architectural scales
                    try:
                        left_side, right_side = scale_str.split('=')
                        drawing_inches = ScaleCalibrationDialog._parse_scale_inches(left_side.strip())
                        real_inches = ScaleCalibrationDialog._parse_scale_inches(right_side.strip())
                        
                        if drawing_inches and real_inches:
                            # Convert to scale factor (real units per drawing unit)
                            test_scale_factor = real_inches / drawing_inches
                            # Convert to pixels per real unit equivalent
                            test_ratio = 1.0 / test_scale_factor
                            diff = abs(test_ratio - (1.0 / scale_ratio))
                            
                            if diff < best_diff:
                                best_diff = diff
                                best_scale = scale_str
                    except:
                        continue
                        
                elif ':' in scale_str:
                    # Handle ratio scales
                    try:
                        _, denominator = scale_str.split(':')
                        test_ratio = 1.0 / float(denominator)
                        diff = abs(test_ratio - (1.0 / scale_ratio))
                        
                        if diff < best_diff:
                            best_diff = diff
                            best_scale = scale_str
                    except:
                        continue
                    
            return scale_ratio, best_scale
            
        return None, None
        
    @staticmethod
    def _parse_scale_inches(dimension_str):
        """Parse dimension string for scale calculation"""
        try:
            dimension_str = dimension_str.strip()
            total_inches = 0
            
            # Handle feet and inches like "1'6"" or "1'0"" or "10'0""
            if "'" in dimension_str:
                parts = dimension_str.split("'")
                feet = float(parts[0]) if parts[0] else 0
                total_inches += feet * 12
                
                # Handle inches part after feet
                if len(parts) > 1:
                    inches_part = parts[1].replace('"', '').strip()
                    if inches_part:
                        total_inches += float(inches_part)
            
            # Handle just inches like "1/8"" or "6""
            elif '"' in dimension_str:
                inches_str = dimension_str.replace('"', '').strip()
                if '/' in inches_str:
                    # Handle fractions like "1/8" or "1 1/2"
                    if ' ' in inches_str:
                        # Handle mixed numbers like "1 1/2"
                        whole_part, frac_part = inches_str.split(' ', 1)
                        total_inches += float(whole_part)
                        numerator, denominator = frac_part.split('/')
                        total_inches += float(numerator) / float(denominator)
                    else:
                        # Handle simple fractions like "1/8"
                        numerator, denominator = inches_str.split('/')
                        total_inches = float(numerator) / float(denominator)
                else:
                    total_inches = float(inches_str)
            
            # Handle just numbers (assume inches)
            else:
                if '/' in dimension_str:
                    if ' ' in dimension_str:
                        # Handle mixed numbers like "1 1/2"
                        whole_part, frac_part = dimension_str.split(' ', 1)
                        total_inches += float(whole_part)
                        numerator, denominator = frac_part.split('/')
                        total_inches += float(numerator) / float(denominator)
                    else:
                        numerator, denominator = dimension_str.split('/')
                        total_inches = float(numerator) / float(denominator)
                else:
                    total_inches = float(dimension_str)
                    
            return total_inches
            
        except (ValueError, ZeroDivisionError):
            return None