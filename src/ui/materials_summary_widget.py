"""
Materials Summary Widget - Displays selected materials with octave band contributions and doors/windows
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QGroupBox, QHeaderView,
                             QSplitter, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from typing import Dict, List, Optional, Tuple
import json

try:
    # Use the unified materials database so UI selections (including enhanced DB) match calculations
    from ..data.materials_database import get_all_materials
except ImportError:
    try:
        from data.materials_database import get_all_materials
    except ImportError:
        import sys
        import os
        current_dir = os.path.dirname(__file__)
        src_dir = os.path.dirname(current_dir)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from data.materials_database import get_all_materials


class MaterialsSummaryWidget(QWidget):
    """Widget for displaying comprehensive materials summary with octave band analysis"""
    
    # Signals
    doors_windows_changed = Signal()  # Emitted when doors/windows are modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.current_materials = {
            'ceiling': [],
            'wall': [],  
            'floor': [],
            'doors_windows': []
        }
        self.current_areas = {
            'ceiling_area': 0,
            'wall_area': 0,
            'floor_area': 0
        }
        self.current_materials_data = {
            'ceiling': [],
            'wall': [],
            'floor': []
        }
        self.frequencies = [125, 250, 500, 1000, 2000, 4000]
        # Unified materials mapping used for all lookups
        self.all_materials = get_all_materials()
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Materials Summary & Analysis")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin: 5px;")
        layout.addWidget(title_label)
        
        # Create splitter for materials table and doors/windows
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Selected materials section
        materials_group = self.create_materials_section()
        splitter.addWidget(materials_group)
        
        # Doors & windows section  
        doors_windows_group = self.create_doors_windows_section()
        splitter.addWidget(doors_windows_group)
        
        # Set splitter proportions (60% materials, 40% doors/windows)
        splitter.setSizes([360, 240])
        
        layout.addWidget(splitter)
        
        # Summary totals
        summary_group = self.create_summary_section()
        layout.addWidget(summary_group)
        
        self.setLayout(layout)
        
    def create_materials_section(self):
        """Create the selected materials table section"""
        group = QGroupBox("Selected Materials & Octave Band Contributions")
        layout = QVBoxLayout()
        
        # Create materials table
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(9)
        
        headers = ["Surface", "Material Name", "Area (sf)", "125Hz", "250Hz", "500Hz", "1000Hz", "2000Hz", "4000Hz"]
        self.materials_table.setHorizontalHeaderLabels(headers)
        
        # Configure table appearance
        self.materials_table.setAlternatingRowColors(True)
        self.materials_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.materials_table.setMaximumHeight(200)
        
        # Set column widths
        header = self.materials_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Surface
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Material Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Area
        for i in range(3, 9):  # Frequency columns
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            
        self.materials_table.setColumnWidth(0, 80)   # Surface
        self.materials_table.setColumnWidth(2, 80)   # Area
        for i in range(3, 9):  # Frequency columns
            self.materials_table.setColumnWidth(i, 60)
            
        layout.addWidget(self.materials_table)
        
        # Status label
        self.materials_status_label = QLabel("No materials selected")
        self.materials_status_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin: 5px;")
        layout.addWidget(self.materials_status_label)
        
        group.setLayout(layout)
        return group
        
    def create_doors_windows_section(self):
        """Create the doors & windows section"""
        group = QGroupBox("Doors & Windows")
        layout = QVBoxLayout()
        
        # Use the dedicated DoorsWindowsWidget
        try:
            from .doors_windows_widget import DoorsWindowsWidget
            self.doors_windows_widget = DoorsWindowsWidget()
            self.doors_windows_widget.elements_changed.connect(self.on_doors_windows_changed)
            layout.addWidget(self.doors_windows_widget)
        except ImportError as e:
            print(f"Warning: Could not import DoorsWindowsWidget: {e}")
            # Fallback to simple label
            fallback_label = QLabel("Doors & Windows widget not available")
            fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            layout.addWidget(fallback_label)
            self.doors_windows_widget = None
        
        group.setLayout(layout)
        return group
        
    def create_summary_section(self):
        """Create the summary totals section"""
        group = QGroupBox("Summary Totals")
        layout = QHBoxLayout()
        
        # Surface areas summary
        areas_frame = QFrame()
        areas_layout = QVBoxLayout()
        areas_title = QLabel("Surface Areas")
        areas_title.setStyleSheet("font-weight: bold; color: #2c3e50;")
        areas_layout.addWidget(areas_title)
        
        self.areas_summary_label = QLabel("No areas calculated")
        self.areas_summary_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        areas_layout.addWidget(self.areas_summary_label)
        
        areas_frame.setLayout(areas_layout)
        layout.addWidget(areas_frame)
        
        # Absorption summary  
        absorption_frame = QFrame()
        absorption_layout = QVBoxLayout()
        absorption_title = QLabel("Total Absorption by Frequency")
        absorption_title.setStyleSheet("font-weight: bold; color: #2c3e50;")
        absorption_layout.addWidget(absorption_title)
        
        self.absorption_summary_label = QLabel("No absorption calculated")
        self.absorption_summary_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        absorption_layout.addWidget(self.absorption_summary_label)
        
        absorption_frame.setLayout(absorption_layout)
        layout.addWidget(absorption_frame)
        
        # Average coefficients
        avg_frame = QFrame()
        avg_layout = QVBoxLayout()
        avg_title = QLabel("Area-Weighted Averages")
        avg_title.setStyleSheet("font-weight: bold; color: #2c3e50;")
        avg_layout.addWidget(avg_title)
        
        self.avg_summary_label = QLabel("No averages calculated")
        self.avg_summary_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        avg_layout.addWidget(self.avg_summary_label)
        
        avg_frame.setLayout(avg_layout)
        layout.addWidget(avg_frame)
        
        group.setLayout(layout)
        return group
        
    def update_materials_data(self, ceiling_materials: List[str], wall_materials: List[str], 
                            floor_materials: List[str], areas: Dict[str, float], 
                            ceiling_materials_data: List[Dict] = None,
                            wall_materials_data: List[Dict] = None,
                            floor_materials_data: List[Dict] = None):
        """Update the materials data and refresh the display"""
        self.current_materials['ceiling'] = ceiling_materials
        self.current_materials['wall'] = wall_materials  
        self.current_materials['floor'] = floor_materials
        self.current_areas = areas
        
        # Store detailed materials data with specific square footages
        self.current_materials_data = {
            'ceiling': ceiling_materials_data or [],
            'wall': wall_materials_data or [],
            'floor': floor_materials_data or []
        }
        
        self.refresh_materials_table()
        self.refresh_summary()
        
    def refresh_materials_table(self):
        """Refresh the materials table display"""
        self.materials_table.setRowCount(0)
        
        # Surface type colors
        colors = {
            'ceiling': QColor(173, 216, 230),  # Light blue
            'wall': QColor(144, 238, 144),     # Light green  
            'floor': QColor(222, 184, 135)     # Burlywood
        }
        
        row = 0
        total_materials = 0
        
        for surface_type in ['ceiling', 'wall', 'floor']:
            # Check if we have detailed materials data with square footages
            materials_data = self.current_materials_data.get(surface_type, [])
            
            if materials_data:
                # Use actual square footage data
                for material_data in materials_data:
                    material_key = material_data.get('material_key')
                    actual_area = material_data.get('square_footage', 0)
                    
                    if material_key not in self.all_materials or actual_area <= 0:
                        continue
                        
                    material = self.all_materials[material_key]
                    self.materials_table.insertRow(row)
                    
                    # Surface type
                    surface_item = QTableWidgetItem(surface_type.title())
                    surface_item.setBackground(colors[surface_type])
                    surface_item.setFlags(surface_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.materials_table.setItem(row, 0, surface_item)
                    
                    # Material name
                    name_item = QTableWidgetItem(material['name'])
                    name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.materials_table.setItem(row, 1, name_item)
                    
                    # Area (actual square footage)
                    area_item = QTableWidgetItem(f"{actual_area:.1f}")
                    area_item.setFlags(area_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.materials_table.setItem(row, 2, area_item)
                    
                    # Frequency coefficients
                    for i, freq in enumerate(self.frequencies):
                        coeff = self.get_material_coefficient(material, freq)
                        absorption = actual_area * coeff
                        
                        coeff_item = QTableWidgetItem(f"{absorption:.2f}")
                        coeff_item.setFlags(coeff_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        coeff_item.setToolTip(f"Coefficient: {coeff:.3f}\nArea: {actual_area:.1f} sf\nAbsorption: {absorption:.2f} sabins")
                        self.materials_table.setItem(row, 3 + i, coeff_item)
                    
                    row += 1
                    total_materials += 1
                    
            else:
                # Fallback to old equal distribution method
                materials = self.current_materials[surface_type]
                if not materials:
                    continue
                    
                area_key = f'{surface_type}_area'
                total_area = self.current_areas.get(area_key, 0)
                area_per_material = total_area / len(materials) if materials else 0
                
                for material_key in materials:
                    if material_key not in self.all_materials:
                        continue
                        
                    material = self.all_materials[material_key]
                    self.materials_table.insertRow(row)
                    
                    # Surface type
                    surface_item = QTableWidgetItem(surface_type.title())
                    surface_item.setBackground(colors[surface_type])
                    surface_item.setFlags(surface_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.materials_table.setItem(row, 0, surface_item)
                    
                    # Material name
                    name_item = QTableWidgetItem(material['name'])
                    name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.materials_table.setItem(row, 1, name_item)
                    
                    # Area
                    area_item = QTableWidgetItem(f"{area_per_material:.1f}")
                    area_item.setFlags(area_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.materials_table.setItem(row, 2, area_item)
                    
                    # Frequency coefficients
                    for i, freq in enumerate(self.frequencies):
                        coeff = self.get_material_coefficient(material, freq)
                        absorption = area_per_material * coeff
                        
                        coeff_item = QTableWidgetItem(f"{absorption:.2f}")
                        coeff_item.setFlags(coeff_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        coeff_item.setToolTip(f"Coefficient: {coeff:.3f}\nArea: {area_per_material:.1f} sf\nAbsorption: {absorption:.2f} sabins")
                        self.materials_table.setItem(row, 3 + i, coeff_item)
                    
                    row += 1
                    total_materials += 1
        
        # Update status
        if total_materials > 0:
            self.materials_status_label.setText(f"Showing {total_materials} materials with actual square footages")
        else:
            self.materials_status_label.setText("No materials selected")
            
    def get_material_coefficient(self, material: Dict, frequency: int) -> float:
        """Get absorption coefficient for a material at specific frequency"""
        if 'coefficients' in material:
            return material['coefficients'].get(str(frequency), material.get('nrc', material['absorption_coeff']))
        return material.get('nrc', material['absorption_coeff'])
        
    def refresh_summary(self):
        """Refresh the summary totals"""
        # Surface areas summary
        ceiling_area = self.current_areas.get('ceiling_area', 0)
        wall_area = self.current_areas.get('wall_area', 0)
        floor_area = self.current_areas.get('floor_area', 0)
        doors_windows_data = self.get_doors_windows_data()
        doors_windows_area = sum(item.get('total_area', 0) for item in doors_windows_data)
        
        total_area = ceiling_area + wall_area + floor_area + doors_windows_area
        
        areas_text = f"Ceiling: {ceiling_area:.0f} sf\n"
        areas_text += f"Walls: {wall_area:.0f} sf\n"
        areas_text += f"Floor: {floor_area:.0f} sf\n"
        areas_text += f"Doors/Windows: {doors_windows_area:.0f} sf\n"
        areas_text += f"Total: {total_area:.0f} sf"
        
        self.areas_summary_label.setText(areas_text)
        
        # Absorption by frequency
        absorption_by_freq = {freq: 0 for freq in self.frequencies}
        
        # Add surface materials absorption using actual square footages
        for surface_type in ['ceiling', 'wall', 'floor']:
            # Use detailed materials data with actual square footages
            materials_data = self.current_materials_data.get(surface_type, [])
            
            if materials_data:
                # Use actual square footage data
                for material_data in materials_data:
                    material_key = material_data.get('material_key')
                    actual_area = material_data.get('square_footage', 0)
                    
                    if material_key not in self.all_materials or actual_area <= 0:
                        continue
                        
                    material = self.all_materials[material_key]
                    for freq in self.frequencies:
                        coeff = self.get_material_coefficient(material, freq)
                        absorption_by_freq[freq] += actual_area * coeff
            else:
                # Fallback to old equal distribution method
                materials = self.current_materials[surface_type]
                if not materials:
                    continue
                    
                area_key = f'{surface_type}_area'
                total_area = self.current_areas.get(area_key, 0)
                area_per_material = total_area / len(materials) if materials else 0
                
                for material_key in materials:
                    if material_key in self.all_materials:
                        material = self.all_materials[material_key]
                        for freq in self.frequencies:
                            coeff = self.get_material_coefficient(material, freq)
                            absorption_by_freq[freq] += area_per_material * coeff
        
        # Add doors/windows absorption
        doors_windows_data = self.get_doors_windows_data()
        for item in doors_windows_data:
            area = item.get('total_area', 0)
            coefficients = item.get('absorption_coefficients', {})
            for freq in self.frequencies:
                coeff = coefficients.get(freq, 0)
                absorption_by_freq[freq] += area * coeff
        
        absorption_text = ""
        for freq in self.frequencies:
            absorption_text += f"{freq}Hz: {absorption_by_freq[freq]:.1f} sabins\n"
        absorption_text = absorption_text.rstrip()
        
        self.absorption_summary_label.setText(absorption_text)
        
        # Average coefficients
        if total_area > 0:
            avg_text = ""
            for freq in self.frequencies:
                avg_coeff = absorption_by_freq[freq] / total_area
                avg_text += f"{freq}Hz: {avg_coeff:.3f}\n"
            
            # Calculate NRC (average of 250, 500, 1000, 2000 Hz)
            nrc_freqs = [250, 500, 1000, 2000]
            nrc = sum(absorption_by_freq[f] for f in nrc_freqs) / (4 * total_area)
            avg_text += f"NRC: {nrc:.2f}"
            
            self.avg_summary_label.setText(avg_text)
        else:
            self.avg_summary_label.setText("No areas to calculate")
            
    def on_doors_windows_changed(self):
        """Handle changes in doors/windows from the dedicated widget"""
        self.refresh_summary()
        self.doors_windows_changed.emit()
            
    def get_doors_windows_data(self) -> List[Dict]:
        """Get current doors/windows data for RT60 calculations"""
        if self.doors_windows_widget:
            return self.doors_windows_widget.get_elements_data()
        return []
        
    def clear_all_data(self):
        """Clear all materials and doors/windows data"""
        self.current_materials = {
            'ceiling': [],
            'wall': [],
            'floor': [],
            'doors_windows': []
        }
        self.current_areas = {
            'ceiling_area': 0,
            'wall_area': 0,
            'floor_area': 0
        }
        
        self.refresh_materials_table()
        if self.doors_windows_widget:
            self.doors_windows_widget.clear_all_elements()
        self.refresh_summary()


# Add missing import
from PySide6.QtWidgets import QPushButton