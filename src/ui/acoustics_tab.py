"""
Acoustics Tab Widget - Enhanced RT60 analysis interface for Room Properties dialog
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
                             QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox, 
                             QDoubleSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextEdit, QCheckBox, QProgressBar, QFrame, QSplitter,
                             QHeaderView, QMessageBox, QSpacerItem, QSizePolicy,
                             QScrollArea, QToolButton, QMenu, QAction)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QObject
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush, QIcon

import sys
import os
from typing import Dict, List, Optional
from datetime import datetime

# Add the src directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.enhanced_materials import (
    ENHANCED_MATERIALS, SURFACE_CATEGORIES, ROOM_TYPE_PRESETS, 
    OCTAVE_BANDS, get_materials_by_category
)
from calculations.enhanced_rt60_calculator import EnhancedRT60Calculator
from calculations.surface_area_calculator import SurfaceAreaCalculator


class SurfaceManagementWidget(QWidget):
    """Widget for managing surface instances with material assignment and area calculation"""
    
    surface_changed = Signal()  # Emitted when surfaces are modified
    
    def __init__(self, space=None, parent=None):
        super().__init__(parent)
        self.space = space
        self.surface_instances = []
        self.area_calculator = SurfaceAreaCalculator(space) if space else None
        
        self.init_ui()
        self.populate_default_surfaces()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Surface management table
        self.create_surface_table()
        layout.addWidget(self.surface_table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.add_surface_btn = QPushButton("Add Surface")
        self.add_surface_btn.clicked.connect(self.add_surface)
        
        self.remove_surface_btn = QPushButton("Remove Selected")
        self.remove_surface_btn.clicked.connect(self.remove_selected_surface)
        
        self.suggest_surfaces_btn = QPushButton("Auto-Suggest")
        self.suggest_surfaces_btn.clicked.connect(self.auto_suggest_surfaces)
        
        button_layout.addWidget(self.add_surface_btn)
        button_layout.addWidget(self.remove_surface_btn)
        button_layout.addWidget(self.suggest_surfaces_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_surface_table(self):
        """Create the surface management table"""
        self.surface_table = QTableWidget()
        self.surface_table.setColumnCount(7)
        
        headers = ["Surface Type", "Material", "Area (sf)", "Calc", "Manual", "Use Manual", "Actions"]
        self.surface_table.setHorizontalHeaderLabels(headers)
        
        # Set column widths
        header = self.surface_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Surface Type
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Material
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Area
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Calc
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Manual
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Use Manual
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        self.surface_table.setAlternatingRowColors(True)
        self.surface_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
    def populate_default_surfaces(self):
        """Populate table with default surfaces for the room"""
        if not self.area_calculator:
            return
            
        # Get surface suggestions from area calculator
        suggestions = self.area_calculator.suggest_surface_instances()
        
        for suggestion in suggestions:
            if suggestion.get('priority') in ['required', 'recommended']:
                for i in range(suggestion.get('instances', 1)):
                    surface_data = {
                        'surface_type': suggestion['surface_type'],
                        'category': suggestion['category'],
                        'calculated_area': suggestion['area_per_instance'],
                        'manual_area': suggestion['area_per_instance'],
                        'use_manual_area': False,
                        'material_key': self.get_default_material_for_category(suggestion['category']),
                        'instance_number': i + 1
                    }
                    self.surface_instances.append(surface_data)
        
        self.refresh_table()
        
    def get_default_material_for_category(self, category):
        """Get a reasonable default material for a surface category"""
        category_defaults = {
            'ceilings': 'act_standard',
            'walls': 'drywall_painted', 
            'floors': 'carpet_medium',
            'doors': 'solid_wood_doors',
            'windows': 'glass_window'
        }
        return category_defaults.get(category, 'drywall_painted')
        
    def refresh_table(self):
        """Refresh the surface table with current data"""
        self.surface_table.setRowCount(len(self.surface_instances))
        
        for row, surface in enumerate(self.surface_instances):
            self.populate_table_row(row, surface)
            
        self.surface_changed.emit()
        
    def populate_table_row(self, row, surface_data):
        """Populate a single table row with surface data"""
        # Surface Type
        surface_type = surface_data.get('surface_type', 'Unknown')
        if surface_data.get('instance_number', 1) > 1:
            surface_type += f" #{surface_data['instance_number']}"
        
        surface_type_item = QTableWidgetItem(surface_type)
        surface_type_item.setFlags(surface_type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.surface_table.setItem(row, 0, surface_type_item)
        
        # Material ComboBox
        material_combo = QComboBox()
        category = surface_data.get('category', 'walls')
        self.populate_material_combo(material_combo, category)
        
        # Set current material
        current_material = surface_data.get('material_key')
        if current_material:
            for i in range(material_combo.count()):
                if material_combo.itemData(i) == current_material:
                    material_combo.setCurrentIndex(i)
                    break
        
        material_combo.currentDataChanged.connect(
            lambda material_key, r=row: self.material_changed(r, material_key)
        )
        self.surface_table.setCellWidget(row, 1, material_combo)
        
        # Calculated Area (read-only)
        calc_area = surface_data.get('calculated_area', 0)
        calc_item = QTableWidgetItem(f"{calc_area:.0f}")
        calc_item.setFlags(calc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        calc_item.setBackground(QColor(240, 240, 240))
        self.surface_table.setItem(row, 3, calc_item)
        
        # Manual Area (editable)
        manual_area = surface_data.get('manual_area', calc_area)
        manual_item = QTableWidgetItem(f"{manual_area:.0f}")
        manual_item.setData(Qt.ItemDataRole.UserRole, row)  # Store row index
        self.surface_table.setItem(row, 4, manual_item)
        
        # Effective Area Display
        use_manual = surface_data.get('use_manual_area', False)
        effective_area = manual_area if use_manual else calc_area
        area_item = QTableWidgetItem(f"{effective_area:.0f}")
        area_item.setFlags(area_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if use_manual:
            area_item.setBackground(QColor(255, 255, 200))  # Yellow for manual
        self.surface_table.setItem(row, 2, area_item)
        
        # Use Manual CheckBox
        use_manual_cb = QCheckBox()
        use_manual_cb.setChecked(use_manual)
        use_manual_cb.toggled.connect(
            lambda checked, r=row: self.toggle_manual_area(r, checked)
        )
        
        # Center the checkbox
        widget = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(use_manual_cb)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        
        self.surface_table.setCellWidget(row, 5, widget)
        
        # Actions (remove button)
        actions_widget = QWidget()
        actions_layout = QHBoxLayout()
        
        remove_btn = QToolButton()
        remove_btn.setText("×")
        remove_btn.setStyleSheet("QToolButton { color: red; font-weight: bold; }")
        remove_btn.clicked.connect(lambda _, r=row: self.remove_surface(r))
        
        actions_layout.addWidget(remove_btn)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_widget.setLayout(actions_layout)
        
        self.surface_table.setCellWidget(row, 6, actions_widget)
        
        # Connect manual area editing
        if manual_item:
            manual_item.itemChanged = lambda item: self.manual_area_changed(item)
            
    def populate_material_combo(self, combo_box, category):
        """Populate material combo box with materials for specific category"""
        combo_box.clear()
        
        # Get materials for this category
        category_materials = get_materials_by_category(category)
        
        # If no materials for category, use all materials
        if not category_materials:
            category_materials = ENHANCED_MATERIALS
            
        # Sort materials by name
        sorted_materials = sorted(category_materials.items(), 
                                key=lambda x: x[1]['name'])
        
        for material_key, material in sorted_materials:
            display_name = f"{material['name']} (NRC: {material.get('nrc', 0):.2f})"
            combo_box.addItem(display_name, material_key)
            
    def material_changed(self, row, material_key):
        """Handle material selection change"""
        if 0 <= row < len(self.surface_instances):
            self.surface_instances[row]['material_key'] = material_key
            self.surface_changed.emit()
            
    def toggle_manual_area(self, row, use_manual):
        """Toggle between calculated and manual area"""
        if 0 <= row < len(self.surface_instances):
            self.surface_instances[row]['use_manual_area'] = use_manual
            
            # Update the effective area display
            surface = self.surface_instances[row]
            effective_area = (surface.get('manual_area', 0) if use_manual 
                            else surface.get('calculated_area', 0))
            
            area_item = self.surface_table.item(row, 2)
            if area_item:
                area_item.setText(f"{effective_area:.0f}")
                if use_manual:
                    area_item.setBackground(QColor(255, 255, 200))  # Yellow for manual
                else:
                    area_item.setBackground(QColor(255, 255, 255))  # White for calculated
                    
            self.surface_changed.emit()
            
    def manual_area_changed(self, item):
        """Handle manual area value change"""
        if item.column() == 4:  # Manual area column
            try:
                new_area = float(item.text())
                row = item.data(Qt.ItemDataRole.UserRole)
                
                if 0 <= row < len(self.surface_instances):
                    self.surface_instances[row]['manual_area'] = new_area
                    
                    # If using manual area, update effective area display
                    if self.surface_instances[row].get('use_manual_area', False):
                        area_item = self.surface_table.item(row, 2)
                        if area_item:
                            area_item.setText(f"{new_area:.0f}")
                    
                    self.surface_changed.emit()
                    
            except ValueError:
                # Reset to previous value if invalid
                row = item.data(Qt.ItemDataRole.UserRole)
                if 0 <= row < len(self.surface_instances):
                    prev_area = self.surface_instances[row].get('manual_area', 0)
                    item.setText(f"{prev_area:.0f}")
                    
    def add_surface(self):
        """Add a new surface instance"""
        # Simple dialog to select surface type and category
        surface_data = {
            'surface_type': 'Custom Surface',
            'category': 'walls',
            'calculated_area': 0,
            'manual_area': 100,  # Default 100 sf
            'use_manual_area': True,
            'material_key': 'drywall_painted',
            'instance_number': 1
        }
        
        self.surface_instances.append(surface_data)
        self.refresh_table()
        
    def remove_surface(self, row):
        """Remove surface at specified row"""
        if 0 <= row < len(self.surface_instances):
            self.surface_instances.pop(row)
            self.refresh_table()
            
    def remove_selected_surface(self):
        """Remove currently selected surface"""
        current_row = self.surface_table.currentRow()
        if current_row >= 0:
            self.remove_surface(current_row)
            
    def auto_suggest_surfaces(self):
        """Auto-suggest surface configuration based on room geometry"""
        if not self.area_calculator:
            return
            
        # Clear existing surfaces
        self.surface_instances.clear()
        
        # Get fresh suggestions
        self.populate_default_surfaces()
        
    def get_surface_instances_for_calculation(self):
        """Get surface instances formatted for RT60 calculation"""
        calc_surfaces = []
        
        for surface in self.surface_instances:
            area = (surface.get('manual_area', 0) if surface.get('use_manual_area', False)
                   else surface.get('calculated_area', 0))
            
            if area > 0 and surface.get('material_key'):
                calc_surfaces.append({
                    'area': area,
                    'material_key': surface['material_key'],
                    'surface_type': surface.get('surface_type', 'Unknown')
                })
                
        return calc_surfaces
        
    def update_calculated_areas(self):
        """Recalculate all automatic surface areas"""
        if not self.area_calculator:
            return
            
        for surface in self.surface_instances:
            # Only update calculated areas, not manual overrides
            surface_type = surface.get('surface_type', '')
            area = self.area_calculator.estimate_surface_areas_by_type(surface_type)
            surface['calculated_area'] = area
            
        self.refresh_table()


class RT60ResultsWidget(QWidget):
    """Widget for displaying RT60 calculation results with frequency analysis"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_results = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the results display interface"""
        layout = QVBoxLayout()
        
        # Results summary
        summary_group = QGroupBox("RT60 Summary")
        summary_layout = QFormLayout()
        
        self.avg_rt60_label = QLabel("Not calculated")
        self.avg_rt60_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        summary_layout.addRow("Average RT60:", self.avg_rt60_label)
        
        self.target_rt60_label = QLabel("0.8 seconds")
        summary_layout.addRow("Target RT60:", self.target_rt60_label)
        
        self.compliance_label = QLabel("Not evaluated")
        summary_layout.addRow("Compliance:", self.compliance_label)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Frequency analysis table
        freq_group = QGroupBox("Frequency Analysis")
        freq_layout = QVBoxLayout()
        
        self.create_frequency_table()
        freq_layout.addWidget(self.frequency_table)
        
        freq_group.setLayout(freq_layout)
        layout.addWidget(freq_group)
        
        # Visualization placeholder
        viz_group = QGroupBox("RT60 Frequency Response")
        viz_layout = QVBoxLayout()
        
        self.visualization_label = QLabel("Run calculation to see frequency response")
        self.visualization_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visualization_label.setMinimumHeight(150)
        self.visualization_label.setStyleSheet("border: 1px solid gray; background-color: #f5f5f5;")
        
        viz_layout.addWidget(self.visualization_label)
        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)
        
        # Recommendations
        rec_group = QGroupBox("Recommendations")
        rec_layout = QVBoxLayout()
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setMaximumHeight(100)
        self.recommendations_text.setPlainText("Run calculation to see recommendations")
        
        rec_layout.addWidget(self.recommendations_text)
        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)
        
        self.setLayout(layout)
        
    def create_frequency_table(self):
        """Create frequency analysis table"""
        self.frequency_table = QTableWidget()
        self.frequency_table.setColumnCount(4)
        
        headers = ["Frequency (Hz)", "RT60 (s)", "Target (s)", "Status"]
        self.frequency_table.setHorizontalHeaderLabels(headers)
        
        # Set up table
        self.frequency_table.setRowCount(len(OCTAVE_BANDS))
        self.frequency_table.setAlternatingRowColors(True)
        
        # Populate frequency column
        for i, freq in enumerate(OCTAVE_BANDS):
            freq_item = QTableWidgetItem(str(freq))
            freq_item.setFlags(freq_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.frequency_table.setItem(i, 0, freq_item)
            
        # Set column widths
        header = self.frequency_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
    def update_results(self, results):
        """Update display with new RT60 calculation results"""
        self.current_results = results
        
        if 'error' in results:
            self.show_error(results['error'])
            return
            
        # Update summary
        avg_rt60 = results.get('average_rt60', 0)
        target_rt60 = results.get('target_rt60', 0.8)
        compliance = results.get('overall_compliance', False)
        
        self.avg_rt60_label.setText(f"{avg_rt60:.2f} seconds")
        self.target_rt60_label.setText(f"{target_rt60:.1f} seconds")
        
        # Color-code compliance
        if compliance:
            self.compliance_label.setText("✅ MEETS TARGET")
            self.compliance_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.compliance_label.setText("❌ NEEDS ADJUSTMENT")
            self.compliance_label.setStyleSheet("color: red; font-weight: bold;")
            
        # Update frequency table
        rt60_by_freq = results.get('rt60_by_frequency', {})
        compliance_by_freq = results.get('compliance_by_frequency', {})
        
        for i, freq in enumerate(OCTAVE_BANDS):
            rt60_value = rt60_by_freq.get(freq, 0)
            is_compliant = compliance_by_freq.get(freq, False)
            
            # RT60 value
            rt60_item = QTableWidgetItem(f"{rt60_value:.2f}")
            rt60_item.setFlags(rt60_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.frequency_table.setItem(i, 1, rt60_item)
            
            # Target value  
            target_item = QTableWidgetItem(f"{target_rt60:.1f}")
            target_item.setFlags(target_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.frequency_table.setItem(i, 2, target_item)
            
            # Status
            status_text = "✅ PASS" if is_compliant else "❌ FAIL"
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Color-code status
            if is_compliant:
                status_item.setBackground(QColor(200, 255, 200))  # Light green
            else:
                status_item.setBackground(QColor(255, 200, 200))  # Light red
                
            self.frequency_table.setItem(i, 3, status_item)
            
        # Update visualization
        self.update_visualization()
        
        # Update recommendations
        self.update_recommendations(results)
        
    def show_error(self, error_message):
        """Show error state"""
        self.avg_rt60_label.setText("Error")
        self.compliance_label.setText(f"Calculation Error: {error_message}")
        self.compliance_label.setStyleSheet("color: red;")
        
        # Clear frequency table
        for i in range(len(OCTAVE_BANDS)):
            for j in range(1, 4):  # Skip frequency column
                item = QTableWidgetItem("--")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.frequency_table.setItem(i, j, item)
                
        self.recommendations_text.setPlainText(f"Error: {error_message}")
        
    def update_visualization(self):
        """Update the frequency response visualization"""
        if not self.current_results or 'error' in self.current_results:
            return
            
        # Create simple ASCII-style visualization for now
        # In a full implementation, this would use a plotting library like matplotlib
        rt60_by_freq = self.current_results.get('rt60_by_frequency', {})
        target_rt60 = self.current_results.get('target_rt60', 0.8)
        
        viz_text = "RT60 Frequency Response:\n\n"
        
        max_rt60 = max(rt60_by_freq.values()) if rt60_by_freq else 2.0
        scale_factor = 40 / max_rt60  # Scale to fit in ~40 characters
        
        for freq in OCTAVE_BANDS:
            rt60_value = rt60_by_freq.get(freq, 0)
            bar_length = int(rt60_value * scale_factor)
            target_pos = int(target_rt60 * scale_factor)
            
            # Create bar representation
            bar = "█" * bar_length
            line = f"{freq:4d}Hz: {bar:<40} {rt60_value:.2f}s"
            
            # Add target indicator
            if bar_length < 40:
                line_list = list(line)
                if target_pos < len(line_list):
                    line_list[target_pos + 8] = '|'  # Offset for frequency label
                line = ''.join(line_list)
            
            viz_text += line + "\n"
            
        viz_text += f"\nTarget: {target_rt60:.1f}s (marked with |)"
        
        self.visualization_label.setText(viz_text)
        self.visualization_label.setStyleSheet(
            "font-family: monospace; font-size: 10px; padding: 10px; "
            "border: 1px solid gray; background-color: white;"
        )
        
    def update_recommendations(self, results):
        """Update recommendations text"""
        recommendations = results.get('recommendations', [])
        
        if not recommendations:
            self.recommendations_text.setPlainText("No specific recommendations at this time.")
            return
            
        rec_text = ""
        for i, rec in enumerate(recommendations, 1):
            priority = rec.get('priority', 'info').upper()
            message = rec.get('message', '')
            suggestion = rec.get('suggestion', '')
            
            rec_text += f"{i}. [{priority}] {message}\n"
            if suggestion:
                rec_text += f"   → {suggestion}\n"
            rec_text += "\n"
            
        self.recommendations_text.setPlainText(rec_text)


class AcousticsTab(QWidget):
    """Main Acoustics Tab widget for Room Properties dialog"""
    
    calculation_completed = Signal(dict)  # Emitted when RT60 calculation completes
    
    def __init__(self, space=None, parent=None):
        super().__init__(parent)
        self.space = space
        self.rt60_calculator = EnhancedRT60Calculator()
        self.area_calculator = SurfaceAreaCalculator(space) if space else None
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Initialize the user interface"""
        # Main splitter layout
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Configuration
        config_panel = self.create_configuration_panel()
        main_splitter.addWidget(config_panel)
        
        # Right panel: Results
        results_panel = self.create_results_panel()
        main_splitter.addWidget(results_panel)
        
        # Set splitter proportions (60% config, 40% results)
        main_splitter.setSizes([600, 400])
        
        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(main_splitter)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.calculate_btn = QPushButton("Calculate RT60")
        self.calculate_btn.clicked.connect(self.calculate_rt60)
        self.calculate_btn.setStyleSheet("QPushButton { background-color: #007ACC; color: white; font-weight: bold; padding: 8px; }")
        
        self.recalculate_areas_btn = QPushButton("Recalculate Areas")
        self.recalculate_areas_btn.clicked.connect(self.recalculate_areas)
        
        self.export_results_btn = QPushButton("Export Results")
        self.export_results_btn.clicked.connect(self.export_results)
        self.export_results_btn.setEnabled(False)
        
        button_layout.addWidget(self.calculate_btn)
        button_layout.addWidget(self.recalculate_areas_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.export_results_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_configuration_panel(self):
        """Create the left configuration panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Room geometry summary
        geometry_group = QGroupBox("Room Geometry")
        geometry_layout = QFormLayout()
        
        self.floor_area_label = QLabel("Not calculated")
        geometry_layout.addRow("Floor Area:", self.floor_area_label)
        
        self.ceiling_height_spin = QDoubleSpinBox()
        self.ceiling_height_spin.setRange(6.0, 30.0)
        self.ceiling_height_spin.setValue(9.0)
        self.ceiling_height_spin.setSuffix(" ft")
        self.ceiling_height_spin.valueChanged.connect(self.geometry_changed)
        geometry_layout.addRow("Ceiling Height:", self.ceiling_height_spin)
        
        self.volume_label = QLabel("Not calculated")
        geometry_layout.addRow("Volume:", self.volume_label)
        
        geometry_group.setLayout(geometry_layout)
        layout.addWidget(geometry_group)
        
        # Target criteria
        target_group = QGroupBox("Target Criteria")
        target_layout = QFormLayout()
        
        self.room_type_combo = QComboBox()
        self.populate_room_types()
        self.room_type_combo.currentDataChanged.connect(self.room_type_changed)
        target_layout.addRow("Room Type:", self.room_type_combo)
        
        self.target_rt60_spin = QDoubleSpinBox()
        self.target_rt60_spin.setRange(0.3, 3.0)
        self.target_rt60_spin.setValue(0.8)
        self.target_rt60_spin.setSuffix(" seconds")
        self.target_rt60_spin.setSingleStep(0.1)
        target_layout.addRow("Target RT60:", self.target_rt60_spin)
        
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.05, 0.5)
        self.tolerance_spin.setValue(0.1)
        self.tolerance_spin.setSuffix(" seconds")
        self.tolerance_spin.setSingleStep(0.05)
        target_layout.addRow("Tolerance:", self.tolerance_spin)
        
        self.leed_compliance_cb = QCheckBox("LEED Compliance Required")
        target_layout.addRow("", self.leed_compliance_cb)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # Surface management
        surface_group = QGroupBox("Surface Materials")
        surface_layout = QVBoxLayout()
        
        self.surface_widget = SurfaceManagementWidget(self.space)
        surface_layout.addWidget(self.surface_widget)
        
        surface_group.setLayout(surface_layout)
        layout.addWidget(surface_group)
        
        panel.setLayout(layout)
        return panel
        
    def create_results_panel(self):
        """Create the right results panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Results widget
        self.results_widget = RT60ResultsWidget()
        layout.addWidget(self.results_widget)
        
        panel.setLayout(layout)
        return panel
        
    def setup_connections(self):
        """Set up signal connections"""
        self.surface_widget.surface_changed.connect(self.surfaces_changed)
        
    def populate_room_types(self):
        """Populate room type combo box"""
        self.room_type_combo.clear()
        
        for key, room_type in ROOM_TYPE_PRESETS.items():
            self.room_type_combo.addItem(room_type['name'], key)
            
    def load_space_data(self):
        """Load data from the space model"""
        if not self.space:
            return
            
        # Update geometry
        if self.space.floor_area:
            self.floor_area_label.setText(f"{self.space.floor_area:.0f} sf")
            
        if self.space.ceiling_height:
            self.ceiling_height_spin.setValue(self.space.ceiling_height)
            
        if self.space.target_rt60:
            self.target_rt60_spin.setValue(self.space.target_rt60)
            
        self.update_volume_display()
        
        # Update surface widget
        if self.area_calculator:
            self.surface_widget.area_calculator = self.area_calculator
            self.surface_widget.update_calculated_areas()
            
    def room_type_changed(self, room_type_key):
        """Handle room type selection change"""
        if room_type_key in ROOM_TYPE_PRESETS:
            preset = ROOM_TYPE_PRESETS[room_type_key]
            
            if preset.get('target_rt60'):
                self.target_rt60_spin.setValue(preset['target_rt60'])
                
            if preset.get('tolerance'):
                self.tolerance_spin.setValue(preset['tolerance'])
                
    def geometry_changed(self):
        """Handle geometry parameter changes"""
        self.update_volume_display()
        
        # Update area calculator
        if self.area_calculator and self.space:
            self.area_calculator.update_space_geometry(
                ceiling_height=self.ceiling_height_spin.value()
            )
            self.surface_widget.update_calculated_areas()
            
    def update_volume_display(self):
        """Update volume calculation display"""
        if self.space and self.space.floor_area:
            volume = self.space.floor_area * self.ceiling_height_spin.value()
            self.volume_label.setText(f"{volume:,.0f} cf")
        else:
            self.volume_label.setText("Not calculated")
            
    def surfaces_changed(self):
        """Handle surface configuration changes"""
        # This can trigger automatic recalculation if desired
        pass
        
    def recalculate_areas(self):
        """Recalculate all surface areas"""
        self.surface_widget.update_calculated_areas()
        
    def calculate_rt60(self):
        """Perform RT60 calculation"""
        try:
            # Prepare calculation data
            space_data = self.prepare_calculation_data()
            
            if not space_data:
                QMessageBox.warning(self, "Calculation Error", 
                                  "Unable to prepare calculation data. Please check room geometry and surfaces.")
                return
                
            # Perform calculation
            method = 'sabine'  # Could be made selectable
            results = self.rt60_calculator.calculate_space_rt60_enhanced(space_data, method)
            
            # Update results display
            self.results_widget.update_results(results)
            
            # Enable export
            self.export_results_btn.setEnabled(True)
            
            # Emit completion signal
            self.calculation_completed.emit(results)
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", 
                               f"An error occurred during calculation:\n{str(e)}")
            
    def prepare_calculation_data(self):
        """Prepare data for RT60 calculation"""
        if not self.space or not self.space.floor_area:
            return None
            
        # Get surface instances from surface widget
        surface_instances = self.surface_widget.get_surface_instances_for_calculation()
        
        if not surface_instances:
            return None
            
        # Calculate volume
        volume = self.space.floor_area * self.ceiling_height_spin.value()
        
        # Prepare space data
        space_data = {
            'volume': volume,
            'surface_instances': surface_instances,
            'target_rt60': self.target_rt60_spin.value(),
            'target_tolerance': self.tolerance_spin.value(),
            'room_type': self.room_type_combo.currentData(),
            'leed_compliance_required': self.leed_compliance_cb.isChecked()
        }
        
        return space_data
        
    def export_results(self):
        """Export RT60 calculation results"""
        if not hasattr(self.results_widget, 'current_results') or not self.results_widget.current_results:
            QMessageBox.information(self, "Export", "No results to export. Please run calculation first.")
            return
            
        # Generate formatted report
        results = self.results_widget.current_results
        report = self.rt60_calculator.format_frequency_report(results)
        
        # For now, show in dialog. In full implementation, this would save to file
        dialog = QMessageBox(self)
        dialog.setWindowTitle("RT60 Calculation Report")
        dialog.setText("Calculation Report:")
        dialog.setDetailedText(report)
        dialog.exec()
        
    def get_current_results(self):
        """Get current RT60 calculation results"""
        if hasattr(self.results_widget, 'current_results'):
            return self.results_widget.current_results
        return None