"""
Room Properties Dialog - Convert drawn rectangles to spaces with acoustic properties
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QListWidget, QListWidgetItem, QMessageBox,
                             QTabWidget, QWidget, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from data.materials import STANDARD_MATERIALS, ROOM_TYPE_DEFAULTS, get_materials_by_category
from .material_search_dialog import MaterialSearchDialog


class RoomPropertiesDialog(QDialog):
    """Dialog for setting room/space properties from drawn rectangles"""
    
    # Signals
    space_created = Signal(dict)  # Emitted when space is created
    
    def __init__(self, parent=None, rectangle_data=None, scale_manager=None):
        super().__init__(parent)
        self.rectangle_data = rectangle_data or {}
        self.scale_manager = scale_manager
        self.selected_materials = {}
        
        self.init_ui()
        self.load_rectangle_data()
        self.load_room_type_defaults()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Room Properties")
        self.setModal(True)
        self.resize(600, 700)
        
        layout = QVBoxLayout()
        
        # Create tabs
        tabs = QTabWidget()
        
        # Basic properties tab
        basic_tab = self.create_basic_tab()
        tabs.addTab(basic_tab, "Basic Properties")
        
        # Materials tab
        materials_tab = self.create_materials_tab()
        tabs.addTab(materials_tab, "Surface Materials")
        
        # Calculations tab
        calc_tab = self.create_calculations_tab()
        tabs.addTab(calc_tab, "Calculations")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("Create Space")
        self.create_btn.clicked.connect(self.create_space)
        self.create_btn.setDefault(True)
        
        self.preview_btn = QPushButton("Preview Calculations")
        self.preview_btn.clicked.connect(self.preview_calculations)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_basic_tab(self):
        """Create the basic properties tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Room type presets
        preset_group = QGroupBox("Room Type Presets")
        preset_layout = QVBoxLayout()
        
        self.room_type_combo = QComboBox()
        self.room_type_combo.addItem("Custom", None)
        
        for key, room_type in ROOM_TYPE_DEFAULTS.items():
            self.room_type_combo.addItem(room_type['name'], key)
            
        self.room_type_combo.currentIndexChanged.connect(self.room_type_index_changed)
        preset_layout.addWidget(self.room_type_combo)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Basic information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter room name")
        basic_layout.addRow("Room Name:", self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Optional description")
        basic_layout.addRow("Description:", self.description_edit)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Geometry information
        geometry_group = QGroupBox("Geometry")
        geometry_layout = QFormLayout()
        
        self.area_label = QLabel("Not calculated")
        geometry_layout.addRow("Floor Area:", self.area_label)
        
        self.ceiling_height_spin = QDoubleSpinBox()
        self.ceiling_height_spin.setRange(6.0, 30.0)
        self.ceiling_height_spin.setValue(9.0)
        self.ceiling_height_spin.setSuffix(" ft")
        self.ceiling_height_spin.valueChanged.connect(self.calculate_volume)
        geometry_layout.addRow("Ceiling Height:", self.ceiling_height_spin)
        
        self.volume_label = QLabel("Not calculated")
        geometry_layout.addRow("Volume:", self.volume_label)
        
        self.wall_area_label = QLabel("Not calculated")
        geometry_layout.addRow("Wall Area:", self.wall_area_label)
        
        geometry_group.setLayout(geometry_layout)
        layout.addWidget(geometry_group)
        
        # Acoustic targets
        acoustic_group = QGroupBox("Acoustic Targets")
        acoustic_layout = QFormLayout()
        
        self.target_rt60_spin = QDoubleSpinBox()
        self.target_rt60_spin.setRange(0.3, 3.0)
        self.target_rt60_spin.setValue(0.8)
        self.target_rt60_spin.setSuffix(" seconds")
        self.target_rt60_spin.setSingleStep(0.1)
        acoustic_layout.addRow("Target RT60:", self.target_rt60_spin)
        
        self.target_nc_spin = QDoubleSpinBox()
        self.target_nc_spin.setRange(20, 50)
        self.target_nc_spin.setValue(35)
        self.target_nc_spin.setSuffix(" NC")
        acoustic_layout.addRow("Target NC:", self.target_nc_spin)
        
        acoustic_group.setLayout(acoustic_layout)
        layout.addWidget(acoustic_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_materials_tab(self):
        """Create the materials selection tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions and advanced search button
        header_layout = QHBoxLayout()
        
        instructions = QLabel("Select materials for each surface type. This affects RT60 calculations.")
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #7f8c8d; font-style: italic; margin-bottom: 10px;")
        header_layout.addWidget(instructions)
        
        header_layout.addStretch()
        
        # Advanced Material Search button
        self.advanced_search_btn = QPushButton("🔍 Advanced Material Search")
        self.advanced_search_btn.setToolTip("Search materials by frequency response and treatment needs")
        self.advanced_search_btn.clicked.connect(self.show_advanced_material_search)
        header_layout.addWidget(self.advanced_search_btn)
        
        layout.addLayout(header_layout)
        
        # Ceiling materials
        ceiling_group = QGroupBox("Ceiling Material")
        ceiling_layout = QVBoxLayout()
        
        self.ceiling_combo = QComboBox()
        self.populate_material_combo(self.ceiling_combo, 'ceiling')
        ceiling_layout.addWidget(self.ceiling_combo)
        
        self.ceiling_info_label = QLabel()
        self.ceiling_info_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        ceiling_layout.addWidget(self.ceiling_info_label)
        
        ceiling_group.setLayout(ceiling_layout)
        layout.addWidget(ceiling_group)
        
        # Wall materials
        wall_group = QGroupBox("Wall Material")
        wall_layout = QVBoxLayout()
        
        self.wall_combo = QComboBox()
        self.populate_material_combo(self.wall_combo, 'wall')
        wall_layout.addWidget(self.wall_combo)
        
        self.wall_info_label = QLabel()
        self.wall_info_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        wall_layout.addWidget(self.wall_info_label)
        
        wall_group.setLayout(wall_layout)
        layout.addWidget(wall_group)
        
        # Floor materials
        floor_group = QGroupBox("Floor Material")
        floor_layout = QVBoxLayout()
        
        self.floor_combo = QComboBox()
        self.populate_material_combo(self.floor_combo, 'floor')
        floor_layout.addWidget(self.floor_combo)
        
        self.floor_info_label = QLabel()
        self.floor_info_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        floor_layout.addWidget(self.floor_info_label)
        
        floor_group.setLayout(floor_layout)
        layout.addWidget(floor_group)
        
        # Connect signals for material info updates
        self.ceiling_combo.currentTextChanged.connect(lambda: self.update_material_info('ceiling'))
        self.wall_combo.currentTextChanged.connect(lambda: self.update_material_info('wall'))
        self.floor_combo.currentTextChanged.connect(lambda: self.update_material_info('floor'))
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_calculations_tab(self):
        """Create the calculations preview tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # RT60 calculation preview
        rt60_group = QGroupBox("RT60 Calculation Preview")
        rt60_layout = QVBoxLayout()
        
        self.rt60_preview_label = QLabel("Select materials to see RT60 calculation")
        self.rt60_preview_label.setStyleSheet("font-family: monospace; background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6;")
        self.rt60_preview_label.setWordWrap(True)
        rt60_layout.addWidget(self.rt60_preview_label)
        
        rt60_group.setLayout(rt60_layout)
        layout.addWidget(rt60_group)
        
        # Surface area breakdown
        areas_group = QGroupBox("Surface Area Breakdown")
        areas_layout = QVBoxLayout()
        
        self.areas_preview_label = QLabel("Geometry will be calculated from drawn rectangle")
        self.areas_preview_label.setStyleSheet("font-family: monospace; background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6;")
        areas_layout.addWidget(self.areas_preview_label)
        
        areas_group.setLayout(areas_layout)
        layout.addWidget(areas_group)
        
        # Total absorption
        absorption_group = QGroupBox("Total Absorption")
        absorption_layout = QVBoxLayout()
        
        self.absorption_preview_label = QLabel("Total absorption will be calculated from materials and areas")
        self.absorption_preview_label.setStyleSheet("font-family: monospace; background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6;")
        absorption_layout.addWidget(self.absorption_preview_label)
        
        absorption_group.setLayout(absorption_layout)
        layout.addWidget(absorption_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def populate_material_combo(self, combo_box, category):
        """Populate a material combo box with materials of the specified category"""
        # Get materials for the specific category
        if category:
            category_materials = get_materials_by_category(category)
            if not category_materials:  # If no materials for this category, show all
                category_materials = STANDARD_MATERIALS
        else:
            category_materials = STANDARD_MATERIALS
            
        # Sort materials by name for better UX
        sorted_materials = sorted(category_materials.items(), key=lambda x: x[1]['name'])
            
        for key, material in sorted_materials:
            # Show NRC if available, otherwise show absorption coefficient
            coeff_display = material.get('nrc', material['absorption_coeff'])
            display_name = f"{material['name']} (α={coeff_display:.2f})"
            combo_box.addItem(display_name, key)
            
    def update_material_info(self, surface_type):
        """Update material information label"""
        combo_map = {
            'ceiling': (self.ceiling_combo, self.ceiling_info_label),
            'wall': (self.wall_combo, self.wall_info_label),
            'floor': (self.floor_combo, self.floor_info_label)
        }
        
        combo, label = combo_map[surface_type]
        material_key = combo.currentData()
        
        if material_key and material_key in STANDARD_MATERIALS:
            material = STANDARD_MATERIALS[material_key]
            info_text = f"Absorption Coefficient: {material['absorption_coeff']} | {material['description']}"
            label.setText(info_text)
        else:
            label.setText("")
            
    def load_rectangle_data(self):
        """Load data from the drawn rectangle"""
        if not self.rectangle_data or not self.scale_manager:
            return
            
        # Set area
        area_real = self.rectangle_data.get('area_real', 0)
        if area_real > 0:
            area_formatted = self.scale_manager.format_area(area_real)
            self.area_label.setText(area_formatted)
            
        # Calculate initial volume and wall area
        self.calculate_volume()
        
    def load_room_type_defaults(self):
        """Load default values when room type changes"""
        # Set initial material info
        self.update_material_info('ceiling')
        self.update_material_info('wall')
        self.update_material_info('floor')
        
    def room_type_index_changed(self, index):
        """Handle room type combo box index change"""
        if index >= 0:
            room_type_key = self.room_type_combo.itemData(index)
            self.room_type_changed(room_type_key)
    
    def room_type_changed(self, room_type_key):
        """Handle room type preset change"""
        if not room_type_key or room_type_key not in ROOM_TYPE_DEFAULTS:
            return
            
        room_type = ROOM_TYPE_DEFAULTS[room_type_key]
        
        # Set target RT60
        self.target_rt60_spin.setValue(room_type['target_rt60'])
        
        # Set materials
        self.set_material_combo(self.ceiling_combo, room_type['ceiling_material'])
        self.set_material_combo(self.wall_combo, room_type['wall_material'])
        self.set_material_combo(self.floor_combo, room_type['floor_material'])
        
        # Update material info
        self.update_material_info('ceiling')
        self.update_material_info('wall')
        self.update_material_info('floor')
        
    def set_material_combo(self, combo_box, material_key):
        """Set combo box to specific material"""
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == material_key:
                combo_box.setCurrentIndex(i)
                break
                
    def calculate_volume(self):
        """Calculate room volume and wall area"""
        if not self.rectangle_data or not self.scale_manager:
            return
            
        area_real = self.rectangle_data.get('area_real', 0)
        height = self.ceiling_height_spin.value()
        
        if area_real > 0 and height > 0:
            # Calculate volume
            volume = area_real * height
            volume_formatted = f"{volume:,.0f} cf"
            self.volume_label.setText(volume_formatted)
            
            # Calculate wall area (perimeter × height)
            width_real = self.rectangle_data.get('width_real', 0)
            height_real = self.rectangle_data.get('height_real', 0)
            
            if width_real > 0 and height_real > 0:
                perimeter = 2 * (width_real + height_real)
                wall_area = perimeter * height
                wall_area_formatted = self.scale_manager.format_area(wall_area)
                self.wall_area_label.setText(wall_area_formatted)
                
                # Update calculations preview
                self.update_calculations_preview()
                
    def update_calculations_preview(self):
        """Update the calculations preview in the calculations tab"""
        if not self.rectangle_data or not self.scale_manager:
            return
            
        # Get surface areas
        floor_area = self.rectangle_data.get('area_real', 0)
        ceiling_area = floor_area
        height = self.ceiling_height_spin.value()
        
        width_real = self.rectangle_data.get('width_real', 0)
        height_real = self.rectangle_data.get('height_real', 0)
        
        if width_real > 0 and height_real > 0:
            perimeter = 2 * (width_real + height_real)
            wall_area = perimeter * height
        else:
            wall_area = 0
            
        # Update areas preview
        areas_text = f"Floor Area: {self.scale_manager.format_area(floor_area)}\n"
        areas_text += f"Ceiling Area: {self.scale_manager.format_area(ceiling_area)}\n"
        areas_text += f"Wall Area: {self.scale_manager.format_area(wall_area)}\n"
        areas_text += f"Total Surface Area: {self.scale_manager.format_area(floor_area + ceiling_area + wall_area)}"
        
        self.areas_preview_label.setText(areas_text)
        
        # Calculate absorption
        ceiling_key = self.ceiling_combo.currentData()
        wall_key = self.wall_combo.currentData()
        floor_key = self.floor_combo.currentData()
        
        if all([ceiling_key, wall_key, floor_key]):
            ceiling_coeff = STANDARD_MATERIALS[ceiling_key]['absorption_coeff']
            wall_coeff = STANDARD_MATERIALS[wall_key]['absorption_coeff']
            floor_coeff = STANDARD_MATERIALS[floor_key]['absorption_coeff']
            
            ceiling_absorption = ceiling_area * ceiling_coeff
            wall_absorption = wall_area * wall_coeff
            floor_absorption = floor_area * floor_coeff
            total_absorption = ceiling_absorption + wall_absorption + floor_absorption
            
            # Update absorption preview
            absorption_text = f"Ceiling: {ceiling_area:.0f} sf × {ceiling_coeff} = {ceiling_absorption:.1f} sabins\n"
            absorption_text += f"Walls: {wall_area:.0f} sf × {wall_coeff} = {wall_absorption:.1f} sabins\n"
            absorption_text += f"Floor: {floor_area:.0f} sf × {floor_coeff} = {floor_absorption:.1f} sabins\n"
            absorption_text += f"Total Absorption: {total_absorption:.1f} sabins"
            
            self.absorption_preview_label.setText(absorption_text)
            
            # Calculate RT60 (simplified Sabine formula)
            volume = floor_area * height
            if total_absorption > 0:
                rt60_calculated = 0.161 * volume / total_absorption
                target_rt60 = self.target_rt60_spin.value()
                
                status = "✅ MEETS TARGET" if abs(rt60_calculated - target_rt60) <= 0.2 else "❌ NEEDS ADJUSTMENT"
                
                rt60_text = f"Volume: {volume:,.0f} cf\n"
                rt60_text += f"Total Absorption: {total_absorption:.1f} sabins\n"
                rt60_text += f"Calculated RT60: {rt60_calculated:.2f} seconds\n"
                rt60_text += f"Target RT60: {target_rt60:.1f} seconds\n"
                rt60_text += f"Status: {status}"
                
                self.rt60_preview_label.setText(rt60_text)
            
    def preview_calculations(self):
        """Preview the acoustic calculations"""
        self.update_calculations_preview()
        
    def create_space(self):
        """Create the space with current properties"""
        # Validate inputs
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Room name is required.")
            self.name_edit.setFocus()
            return
            
        if not self.rectangle_data:
            QMessageBox.warning(self, "Error", "No rectangle data available.")
            return
            
        # Get material selections
        ceiling_key = self.ceiling_combo.currentData()
        wall_key = self.wall_combo.currentData()
        floor_key = self.floor_combo.currentData()
        
        if not all([ceiling_key, wall_key, floor_key]):
            QMessageBox.warning(self, "Validation Error", "Please select materials for all surfaces.")
            return
            
        # Prepare space data
        space_data = {
            'name': name,
            'description': self.description_edit.toPlainText().strip(),
            'floor_area': self.rectangle_data.get('area_real', 0),
            'ceiling_height': self.ceiling_height_spin.value(),
            'target_rt60': self.target_rt60_spin.value(),
            'ceiling_material': ceiling_key,
            'wall_material': wall_key,
            'floor_material': floor_key,
            'rectangle_data': self.rectangle_data,
            'geometry_calculated': True
        }
        
        # Calculate additional properties
        if space_data['floor_area'] > 0 and space_data['ceiling_height'] > 0:
            space_data['volume'] = space_data['floor_area'] * space_data['ceiling_height']
            
            # Calculate wall area
            width_real = self.rectangle_data.get('width_real', 0)
            height_real = self.rectangle_data.get('height_real', 0)
            
            if width_real > 0 and height_real > 0:
                perimeter = 2 * (width_real + height_real)
                space_data['wall_area'] = perimeter * space_data['ceiling_height']
                
        # Emit signal and close
        self.space_created.emit(space_data)
        self.accept()
        
    def show_advanced_material_search(self):
        """Show advanced material search dialog"""
        # Get current space data for analysis
        space_data = self.get_space_data()
        
        # Add volume calculation if missing
        if space_data['floor_area'] > 0 and space_data['ceiling_height'] > 0:
            space_data['volume'] = space_data['floor_area'] * space_data['ceiling_height']
            
            # Calculate wall area
            width_real = self.rectangle_data.get('width_real', 0)
            height_real = self.rectangle_data.get('height_real', 0)
            
            if width_real > 0 and height_real > 0:
                perimeter = 2 * (width_real + height_real)
                space_data['wall_area'] = perimeter * space_data['ceiling_height']
        
        # Show material search dialog
        search_dialog = MaterialSearchDialog(self, space_data)
        search_dialog.material_applied.connect(self.apply_searched_material)
        search_dialog.exec()
        
    def apply_searched_material(self, material, surface_type):
        """Apply material selected from advanced search"""
        material_key = material.get('key', '')
        
        if surface_type == 'ceiling':
            # Find and select the material in ceiling combo
            for i in range(self.ceiling_combo.count()):
                if self.ceiling_combo.itemData(i) == material_key:
                    self.ceiling_combo.setCurrentIndex(i)
                    break
        elif surface_type == 'wall':
            # Find and select the material in wall combo
            for i in range(self.wall_combo.count()):
                if self.wall_combo.itemData(i) == material_key:
                    self.wall_combo.setCurrentIndex(i)
                    break
        elif surface_type == 'floor':
            # Find and select the material in floor combo
            for i in range(self.floor_combo.count()):
                if self.floor_combo.itemData(i) == material_key:
                    self.floor_combo.setCurrentIndex(i)
                    break
        
        # Update material info display
        self.update_material_info(surface_type)
        
        # Show confirmation message
        QMessageBox.information(
            self, 
            "Material Applied",
            f"Applied {material.get('name', 'Unknown')} to {surface_type} surface."
        )
        
    def get_space_data(self):
        """Get the current space data (for external access)"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'floor_area': self.rectangle_data.get('area_real', 0),
            'ceiling_height': self.ceiling_height_spin.value(),
            'target_rt60': self.target_rt60_spin.value(),
            'ceiling_material': self.ceiling_combo.currentData(),
            'wall_material': self.wall_combo.currentData(),
            'floor_material': self.floor_combo.currentData(),
            'rectangle_data': self.rectangle_data
        }