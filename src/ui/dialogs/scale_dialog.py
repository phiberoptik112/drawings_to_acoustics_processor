"""
Scale Dialog - Set drawing scale and coordinate system
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QFormLayout,
                             QGroupBox, QRadioButton, QButtonGroup, QMessageBox,
                             QDoubleSpinBox)
from PySide6.QtCore import Qt
from drawing.scale_manager import ScaleCalibrationDialog


class ScaleDialog(QDialog):
    """Dialog for setting drawing scale"""
    
    def __init__(self, parent=None, scale_manager=None):
        super().__init__(parent)
        self.scale_manager = scale_manager
        self.init_ui()
        self.load_current_scale()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Set Drawing Scale")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Scale input methods
        methods_group = QGroupBox("Scale Input Method")
        methods_layout = QVBoxLayout()
        
        self.method_group = QButtonGroup()
        
        # Standard scale method
        self.standard_radio = QRadioButton("Standard Scale")
        self.standard_radio.setChecked(True)
        self.standard_radio.toggled.connect(self.method_changed)
        self.method_group.addButton(self.standard_radio)
        methods_layout.addWidget(self.standard_radio)
        
        self.standard_layout = QFormLayout()
        
        self.scale_combo = QComboBox()
        scales = ScaleCalibrationDialog.get_common_scales()
        self.scale_combo.addItems(scales)
        self.standard_layout.addRow("Scale:", self.scale_combo)
        
        self.units_combo = QComboBox()
        self.units_combo.addItems(["feet", "meters"])
        self.standard_layout.addRow("Units:", self.units_combo)
        
        methods_layout.addLayout(self.standard_layout)
        
        # Custom scale method
        self.custom_radio = QRadioButton("Custom Scale")
        self.custom_radio.toggled.connect(self.method_changed)
        self.method_group.addButton(self.custom_radio)
        methods_layout.addWidget(self.custom_radio)
        
        self.custom_layout = QFormLayout()
        
        self.drawing_distance_edit = QDoubleSpinBox()
        self.drawing_distance_edit.setRange(0.1, 1000.0)
        self.drawing_distance_edit.setValue(2.5)
        self.drawing_distance_edit.setSuffix(" inches")
        self.custom_layout.addRow("Drawing Distance:", self.drawing_distance_edit)
        
        self.actual_distance_edit = QDoubleSpinBox()
        self.actual_distance_edit.setRange(0.1, 10000.0)
        self.actual_distance_edit.setValue(25.0)
        self.actual_distance_edit.setSuffix(" feet")
        self.custom_layout.addRow("Actual Distance:", self.actual_distance_edit)
        
        methods_layout.addLayout(self.custom_layout)
        
        # Reference line method
        self.reference_radio = QRadioButton("Reference Line (Measure on Drawing)")
        self.reference_radio.toggled.connect(self.method_changed)
        self.method_group.addButton(self.reference_radio)
        methods_layout.addWidget(self.reference_radio)
        
        self.reference_layout = QFormLayout()
        
        self.reference_pixels_edit = QDoubleSpinBox()
        self.reference_pixels_edit.setRange(1, 10000)
        self.reference_pixels_edit.setValue(250)
        self.reference_pixels_edit.setSuffix(" pixels")
        self.reference_layout.addRow("Measured Pixels:", self.reference_pixels_edit)
        
        self.reference_actual_edit = QDoubleSpinBox()
        self.reference_actual_edit.setRange(0.1, 10000.0)
        self.reference_actual_edit.setValue(50.0)
        self.reference_actual_edit.setSuffix(" feet")
        self.reference_layout.addRow("Actual Length:", self.reference_actual_edit)
        
        methods_layout.addLayout(self.reference_layout)
        
        methods_group.setLayout(methods_layout)
        layout.addWidget(methods_group)
        
        # Current scale display
        current_group = QGroupBox("Current Scale Information")
        current_layout = QFormLayout()
        
        self.current_scale_label = QLabel("Not set")
        current_layout.addRow("Current Scale:", self.current_scale_label)
        
        self.current_ratio_label = QLabel("Not set")
        current_layout.addRow("Pixels per Unit:", self.current_ratio_label)
        
        current_group.setLayout(current_layout)
        layout.addWidget(current_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_scale)
        self.apply_btn.setDefault(True)
        
        self.test_btn = QPushButton("Test")
        self.test_btn.clicked.connect(self.test_scale)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.test_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Update initial state
        self.method_changed()
        
    def load_current_scale(self):
        """Load current scale from scale manager"""
        if self.scale_manager:
            scale_info = self.scale_manager.get_scale_info()
            
            if scale_info['scale_string']:
                self.current_scale_label.setText(scale_info['scale_string'])
                
            if scale_info['scale_ratio'] > 0:
                self.current_ratio_label.setText(f"{scale_info['scale_ratio']:.4f}")
                
            # Set units
            self.units_combo.setCurrentText(scale_info['units'])
            
            # Try to match current scale in combo
            current_scale = scale_info['scale_string']
            index = self.scale_combo.findText(current_scale)
            if index >= 0:
                self.scale_combo.setCurrentIndex(index)
                
    def method_changed(self):
        """Handle scale method change"""
        standard_enabled = self.standard_radio.isChecked()
        custom_enabled = self.custom_radio.isChecked()
        reference_enabled = self.reference_radio.isChecked()
        
        # Enable/disable form sections
        self.scale_combo.setEnabled(standard_enabled)
        self.units_combo.setEnabled(standard_enabled)
        
        self.drawing_distance_edit.setEnabled(custom_enabled)
        self.actual_distance_edit.setEnabled(custom_enabled)
        
        self.reference_pixels_edit.setEnabled(reference_enabled)
        self.reference_actual_edit.setEnabled(reference_enabled)
        
    def test_scale(self):
        """Test the current scale settings"""
        scale_ratio, scale_string = self.calculate_scale()
        
        if scale_ratio and scale_string:
            # Show test results
            test_pixels = [50, 100, 200, 500]
            results = []
            
            for pixels in test_pixels:
                real_distance = pixels / scale_ratio
                results.append(f"{pixels}px = {real_distance:.2f} {self.get_units()}")
                
            result_text = "\n".join(results)
            QMessageBox.information(self, "Scale Test", 
                                   f"Scale: {scale_string}\nPixels per {self.get_units()}: {scale_ratio:.4f}\n\nTest conversions:\n{result_text}")
        else:
            QMessageBox.warning(self, "Error", "Invalid scale settings")
            
    def apply_scale(self):
        """Apply the scale settings"""
        scale_ratio, scale_string = self.calculate_scale()
        
        if scale_ratio and scale_string and self.scale_manager:
            # Update scale manager
            if self.reference_radio.isChecked():
                # Use reference measurement method
                pixel_distance = self.reference_pixels_edit.value()
                real_distance = self.reference_actual_edit.value()
                units = self.get_units()
                
                success = self.scale_manager.set_scale_from_reference(
                    pixel_distance, real_distance, units
                )
            elif self.standard_radio.isChecked():
                # Use ScaleManager's set_scale_from_string for standard scales
                scale_string = self.scale_combo.currentText()
                success = self.scale_manager.set_scale_from_string(scale_string)
                if success:
                    self.scale_manager.units = self.get_units()
            else:
                # Use calculated scale for custom scales
                self.scale_manager.scale_ratio = scale_ratio
                self.scale_manager.scale_string = scale_string
                self.scale_manager.units = self.get_units()
                self.scale_manager.scale_changed.emit(scale_ratio, scale_string)
                success = True
                
            if success:
                QMessageBox.information(self, "Success", f"Scale set to {scale_string}")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to set scale")
        else:
            QMessageBox.warning(self, "Error", "Invalid scale settings")
            
    def calculate_scale(self):
        """Calculate scale ratio and string from current settings"""
        if self.standard_radio.isChecked():
            # Standard scale
            scale_string = self.scale_combo.currentText()
            try:
                # Handle architectural scales like "1/8"=1'0""
                if '=' in scale_string and ('"' in scale_string or "'" in scale_string):
                    # Parse architectural scale
                    left_side, right_side = scale_string.split('=')
                    
                    # Parse drawing units (left side, typically inches)
                    drawing_inches = self._parse_inches(left_side.strip())
                    if drawing_inches is None:
                        return None, None
                    
                    # Parse real world units (right side, typically feet and inches)
                    real_inches = self._parse_inches(right_side.strip())
                    if real_inches is None:
                        return None, None
                    
                    # Convert to feet for consistency
                    drawing_feet = drawing_inches / 12.0
                    real_feet = real_inches / 12.0
                    
                    if drawing_feet > 0 and real_feet > 0:
                        # Calculate scale factor (real units per drawing unit)
                        scale_factor = real_feet / drawing_feet
                        # For now, use a reasonable default pixels per unit
                        # This will be calibrated with actual measurements later
                        # For architectural scales, assume 1 inch on drawing = ~139 pixels on screen (calibrated)
                        # Then scale_ratio = (139 pixels/inch) * (12 inches/foot) / scale_factor
                        scale_ratio = (139.0 * 12.0) / scale_factor  # Calibrated for 25ft measurement
                        return scale_ratio, scale_string
                
                # Handle ratio scales like "1:100"
                elif ':' in scale_string:
                    drawing_unit, real_unit = scale_string.split(':')
                    drawing_unit = float(drawing_unit)
                    real_unit = float(real_unit)
                    
                    if drawing_unit > 0 and real_unit > 0:
                        # Calculate scale ratio (pixels per real-world unit)
                        # For ratio scales, we need to determine pixels per unit
                        # Using a reasonable default that can be calibrated later
                        # For ratio scales like 1:100, assume 1 unit = ~100 pixels on screen
                        # Then scale_ratio = 100 pixels per drawing unit
                        scale_ratio = 100.0 / real_unit  # 100 pixels per unit as default
                        return scale_ratio, scale_string
                        
            except (ValueError, ZeroDivisionError):
                pass
                
        elif self.custom_radio.isChecked():
            # Custom scale
            drawing_distance = self.drawing_distance_edit.value()
            actual_distance = self.actual_distance_edit.value()
            
            if drawing_distance > 0 and actual_distance > 0:
                # Convert drawing distance to same units as actual
                if self.get_units() == "feet":
                    drawing_distance_converted = drawing_distance / 12  # inches to feet
                else:
                    drawing_distance_converted = drawing_distance * 0.0254  # inches to meters
                    
                scale_ratio = drawing_distance_converted / actual_distance
                
                # Generate scale string
                if scale_ratio < 1:
                    scale_string = f"1:{1/scale_ratio:.0f}"
                else:
                    scale_string = f"{scale_ratio:.2f}:1"
                    
                return scale_ratio, scale_string
                
        elif self.reference_radio.isChecked():
            # Reference line
            pixel_distance = self.reference_pixels_edit.value()
            actual_distance = self.reference_actual_edit.value()
            
            if pixel_distance > 0 and actual_distance > 0:
                scale_ratio = pixel_distance / actual_distance
                
                # Generate scale string
                if scale_ratio < 1:
                    scale_string = f"1:{1/scale_ratio:.0f}"
                else:
                    scale_string = f"{scale_ratio:.2f}:1"
                    
                return scale_ratio, scale_string
                
        return None, None
        
    def get_units(self):
        """Get selected units"""
        if self.standard_radio.isChecked():
            return self.units_combo.currentText()
        elif self.custom_radio.isChecked():
            return "feet" if self.actual_distance_edit.suffix().strip() == "feet" else "meters"
        elif self.reference_radio.isChecked():
            return "feet" if self.reference_actual_edit.suffix().strip() == "feet" else "meters"
        return "feet"
        
    def _parse_inches(self, dimension_str):
        """Parse dimension string like '1/8"' or '1'6"' and return total inches"""
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