"""
Space Edit Dialog - Edit properties of existing spaces
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QTabWidget, QWidget, QListWidget,
                             QListWidgetItem, QScrollArea, QSizePolicy, QSplitter,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal, QTimer

from models import get_session
from models.space import Space, SurfaceType
from data.materials import STANDARD_MATERIALS, ROOM_TYPE_DEFAULTS, get_materials_by_category
from calculations.rt60_calculator import RT60Calculator
from ui.rt60_plot_widget import RT60PlotContainer


class MaterialSearchWidget(QWidget):
    """Widget for searching and selecting materials"""
    
    material_selected = Signal(str)  # Emits material key when selected
    
    def __init__(self, category, parent=None):
        super().__init__(parent)
        self.category = category
        self.filtered_materials = {}
        self.init_ui()
        
    def init_ui(self):
        """Initialize the search interface"""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(f"Search {self.category} materials...")
        self.search_edit.textChanged.connect(self.filter_materials)
        search_layout.addWidget(self.search_edit)
        
        # Add button
        self.add_btn = QPushButton("Add")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self.add_selected_material)
        search_layout.addWidget(self.add_btn)
        
        layout.addLayout(search_layout)
        
        # Materials list with expandable height
        self.materials_list = QListWidget()
        self.materials_list.setMinimumHeight(150)
        self.materials_list.setMaximumHeight(300)  # Increased from 150
        self.materials_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.materials_list.itemDoubleClicked.connect(self.add_selected_material)
        layout.addWidget(self.materials_list)
        
        # Status and expand controls
        expand_layout = QHBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready to search")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        expand_layout.addWidget(self.status_label)
        
        expand_layout.addStretch()
        
        # Expand/Collapse button
        self.expand_btn = QPushButton("Expand List")
        self.expand_btn.setMaximumWidth(100)
        self.expand_btn.clicked.connect(self.toggle_expand)
        expand_layout.addWidget(self.expand_btn)
        layout.addLayout(expand_layout)
        
        self.setLayout(layout)
        self.populate_materials()
        
        # Track expansion state
        self.is_expanded = False
        
    def populate_materials(self):
        """Populate the materials list"""
        # Get materials for this category
        category_materials = get_materials_by_category(self.category)
        if not category_materials:
            category_materials = STANDARD_MATERIALS
            
        # Sort by name
        sorted_materials = sorted(category_materials.items(), key=lambda x: x[1]['name'])
        
        for key, material in sorted_materials:
            coeff_display = material.get('nrc', material['absorption_coeff'])
            display_name = f"{material['name']} (α={coeff_display:.2f})"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, key)
            item.setData(Qt.UserRole + 1, material)
            self.materials_list.addItem(item)
            
        self.filtered_materials = dict(sorted_materials)
        
        # Set initial status
        self.status_label.setText(f"Showing all {len(sorted_materials)} materials")
        
    def filter_materials(self, search_text):
        """Filter materials based on search text"""
        search_lower = search_text.lower()
        visible_count = 0
        
        for i in range(self.materials_list.count()):
            item = self.materials_list.item(i)
            material = item.data(Qt.UserRole + 1)
            
            # Check if material name or description contains search text
            name_match = search_lower in material['name'].lower()
            desc_match = search_lower in material.get('description', '').lower()
            
            is_visible = name_match or desc_match
            item.setHidden(not is_visible)
            
            if is_visible:
                visible_count += 1
        
        # Update status label
        if search_text:
            self.status_label.setText(f"Found {visible_count} materials matching '{search_text}'")
        else:
            total_count = self.materials_list.count()
            self.status_label.setText(f"Showing all {total_count} materials")
            
        # Enable/disable add button based on selection
        self.add_btn.setEnabled(self.materials_list.currentItem() is not None)
        
    def add_selected_material(self):
        """Add the currently selected material"""
        current_item = self.materials_list.currentItem()
        if current_item:
            material_key = current_item.data(Qt.UserRole)
            print(f"DEBUG: MaterialSearchWidget.add_selected_material({self.category}): '{material_key}'")
            self.material_selected.emit(material_key)
            self.search_edit.clear()
            self.materials_list.clearSelection()
        else:
            print(f"DEBUG: MaterialSearchWidget.add_selected_material({self.category}): No item selected")
            
    def toggle_expand(self):
        """Toggle between expanded and collapsed view of the materials list"""
        if self.is_expanded:
            # Collapse
            self.materials_list.setMaximumHeight(300)
            self.expand_btn.setText("Expand List")
            self.is_expanded = False
        else:
            # Expand
            self.materials_list.setMaximumHeight(600)  # Much larger for better visibility
            self.expand_btn.setText("Collapse List")
            self.is_expanded = True


class MaterialListWidget(QWidget):
    """Widget for displaying and managing selected materials with square footage"""
    
    material_removed = Signal(str)  # Emits material key when removed
    material_changed = Signal()     # Emits when material square footage changes
    
    def __init__(self, surface_type, parent=None):
        super().__init__(parent)
        self.surface_type = surface_type
        self.materials_data = []  # List of dicts with material_key and square_footage
        self.total_surface_area = 0  # Total available surface area
        self.init_ui()
        
    def init_ui(self):
        """Initialize the materials list interface"""
        layout = QVBoxLayout()
        
        # Header with surface area info
        header_layout = QHBoxLayout()
        header_label = QLabel(f"Selected {self.surface_type.title()} Materials:")
        header_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        # Surface area info
        self.area_info_label = QLabel("Total: 0 sf")
        self.area_info_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        header_layout.addWidget(self.area_info_label)
        
        # Remove button
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_selected_material)
        header_layout.addWidget(self.remove_btn)
        
        layout.addLayout(header_layout)
        
        # Materials table (instead of list)
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(4)
        self.materials_table.setHorizontalHeaderLabels(["Material Name", "NRC", "Area (sf)", "% Coverage"])
        
        # Configure table
        self.materials_table.setMinimumHeight(80)
        self.materials_table.setMaximumHeight(200)
        self.materials_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.materials_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.materials_table.itemSelectionChanged.connect(self.update_remove_button)
        
        # Set column widths
        header = self.materials_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Material Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # NRC
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Area
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Coverage
        
        self.materials_table.setColumnWidth(1, 60)   # NRC
        self.materials_table.setColumnWidth(2, 80)   # Area
        self.materials_table.setColumnWidth(3, 80)   # Coverage
        
        layout.addWidget(self.materials_table)
        
        # Usage summary
        self.usage_label = QLabel("No materials selected")
        self.usage_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin: 5px;")
        layout.addWidget(self.usage_label)
        
        self.setLayout(layout)
        
    def set_total_surface_area(self, area):
        """Set the total available surface area for this surface type"""
        self.total_surface_area = area
        self.area_info_label.setText(f"Total: {area:.0f} sf")
        self.update_display()
        
    def add_material(self, material_key, default_area=None):
        """Add a material to the list with default square footage"""
        print(f"DEBUG: MaterialListWidget.add_material({self.surface_type}): '{material_key}'")
        
        # Check if material already exists
        if any(m['material_key'] == material_key for m in self.materials_data):
            print(f"DEBUG:   Material already exists")
            return
            
        if material_key in STANDARD_MATERIALS:
            # Calculate default area (remaining area or 10% of total, whichever is smaller)
            used_area = sum(m['square_footage'] for m in self.materials_data)
            remaining_area = max(0, self.total_surface_area - used_area)
            
            if default_area is None:
                default_area = min(remaining_area, self.total_surface_area * 0.1) if self.total_surface_area > 0 else 100
                default_area = max(1, default_area)  # Minimum 1 sf
            
            material_data = {
                'material_key': material_key,
                'square_footage': default_area
            }
            
            self.materials_data.append(material_data)
            print(f"DEBUG:   Material added with {default_area:.0f} sf")
            self.update_display()
            self.material_changed.emit()
        else:
            print(f"DEBUG:   Material not found in STANDARD_MATERIALS")
            
    def remove_selected_material(self):
        """Remove the selected material from the list"""
        current_row = self.materials_table.currentRow()
        if 0 <= current_row < len(self.materials_data):
            material_data = self.materials_data[current_row]
            material_key = material_data['material_key']
            
            self.materials_data.pop(current_row)
            self.material_removed.emit(material_key)
            self.update_display()
            self.material_changed.emit()
                
    def update_display(self):
        """Update the display of materials"""
        print(f"DEBUG: MaterialListWidget.update_display({self.surface_type}): {len(self.materials_data)} materials")
        self.materials_table.setRowCount(len(self.materials_data))
        
        total_used_area = 0
        
        for row, material_data in enumerate(self.materials_data):
            material_key = material_data['material_key']
            square_footage = material_data['square_footage']
            total_used_area += square_footage
            
            if material_key in STANDARD_MATERIALS:
                material = STANDARD_MATERIALS[material_key]
                
                # Material name
                name_item = QTableWidgetItem(material['name'])
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                name_item.setData(Qt.UserRole, material_key)
                self.materials_table.setItem(row, 0, name_item)
                
                # NRC
                nrc = material.get('nrc', material['absorption_coeff'])
                nrc_item = QTableWidgetItem(f"{nrc:.2f}")
                nrc_item.setFlags(nrc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.materials_table.setItem(row, 1, nrc_item)
                
                # Square footage (editable)
                area_item = QTableWidgetItem(f"{square_footage:.0f}")
                area_item.setData(Qt.UserRole, row)  # Store row index for editing
                self.materials_table.setItem(row, 2, area_item)
                
                # Coverage percentage
                coverage = (square_footage / self.total_surface_area * 100) if self.total_surface_area > 0 else 0
                coverage_item = QTableWidgetItem(f"{coverage:.1f}%")
                coverage_item.setFlags(coverage_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.materials_table.setItem(row, 3, coverage_item)
        
        # Connect cell changed signal for area editing
        self.materials_table.cellChanged.connect(self.on_cell_changed)
        
        # Update usage summary
        if self.materials_data:
            coverage_total = (total_used_area / self.total_surface_area * 100) if self.total_surface_area > 0 else 0
            remaining = max(0, self.total_surface_area - total_used_area)
            
            if coverage_total > 100:
                self.usage_label.setText(f"⚠️ Over-coverage: {coverage_total:.1f}% ({total_used_area:.0f} sf used, {self.total_surface_area:.0f} sf available)")
                self.usage_label.setStyleSheet("color: #e74c3c; font-size: 10px; margin: 5px; font-weight: bold;")
            else:
                self.usage_label.setText(f"Coverage: {coverage_total:.1f}% ({total_used_area:.0f} sf used, {remaining:.0f} sf remaining)")
                self.usage_label.setStyleSheet("color: #27ae60; font-size: 10px; margin: 5px;")
        else:
            self.usage_label.setText("No materials selected")
            self.usage_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin: 5px;")
            
    def on_cell_changed(self, row, column):
        """Handle cell value changes (for square footage editing)"""
        if column == 2 and 0 <= row < len(self.materials_data):  # Area column
            try:
                # Temporarily disconnect to avoid recursive calls
                self.materials_table.cellChanged.disconnect(self.on_cell_changed)
                
                item = self.materials_table.item(row, column)
                new_area = float(item.text())
                new_area = max(0, new_area)  # Don't allow negative areas
                
                # Update the data
                self.materials_data[row]['square_footage'] = new_area
                
                # Update the display
                item.setText(f"{new_area:.0f}")
                
                # Update coverage percentage
                coverage = (new_area / self.total_surface_area * 100) if self.total_surface_area > 0 else 0
                coverage_item = self.materials_table.item(row, 3)
                if coverage_item:
                    coverage_item.setText(f"{coverage:.1f}%")
                
                # Update usage summary
                self.update_usage_summary()
                
                # Reconnect and emit change signal
                self.materials_table.cellChanged.connect(self.on_cell_changed)
                self.material_changed.emit()
                
            except ValueError:
                # Restore original value if invalid input
                self.materials_table.cellChanged.disconnect(self.on_cell_changed)
                original_area = self.materials_data[row]['square_footage']
                item.setText(f"{original_area:.0f}")
                self.materials_table.cellChanged.connect(self.on_cell_changed)
                
    def update_usage_summary(self):
        """Update just the usage summary without full display refresh"""
        total_used_area = sum(m['square_footage'] for m in self.materials_data)
        
        if self.materials_data:
            coverage_total = (total_used_area / self.total_surface_area * 100) if self.total_surface_area > 0 else 0
            remaining = max(0, self.total_surface_area - total_used_area)
            
            if coverage_total > 100:
                self.usage_label.setText(f"⚠️ Over-coverage: {coverage_total:.1f}% ({total_used_area:.0f} sf used, {self.total_surface_area:.0f} sf available)")
                self.usage_label.setStyleSheet("color: #e74c3c; font-size: 10px; margin: 5px; font-weight: bold;")
            else:
                self.usage_label.setText(f"Coverage: {coverage_total:.1f}% ({total_used_area:.0f} sf used, {remaining:.0f} sf remaining)")
                self.usage_label.setStyleSheet("color: #27ae60; font-size: 10px; margin: 5px;")
        else:
            self.usage_label.setText("No materials selected")
            self.usage_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin: 5px;")
                
    def update_remove_button(self):
        """Update the remove button state"""
        self.remove_btn.setEnabled(self.materials_table.currentRow() >= 0)
        
    def get_materials_data(self):
        """Get the list of materials with their square footages"""
        return self.materials_data.copy()
        
    def get_materials(self):
        """Get the list of material keys (for backward compatibility)"""
        return [m['material_key'] for m in self.materials_data]
        
    def set_materials(self, materials):
        """Set the list of materials (backward compatibility)"""
        print(f"DEBUG: MaterialListWidget.set_materials({self.surface_type}): {materials}")
        
        self.materials_data = []
        if materials:
            # Convert old format to new format with default areas
            default_area_per_material = self.total_surface_area / len(materials) if materials and self.total_surface_area > 0 else 100
            
            for material_key in materials:
                if material_key:
                    self.materials_data.append({
                        'material_key': material_key,
                        'square_footage': default_area_per_material
                    })
        
        self.update_display()
        
    def set_materials_data(self, materials_data):
        """Set materials with specific square footages"""
        print(f"DEBUG: MaterialListWidget.set_materials_data({self.surface_type}): {materials_data}")
        self.materials_data = materials_data.copy() if materials_data else []
        self.update_display()


class SpaceEditDialog(QDialog):
    """Dialog for editing existing space properties"""
    
    def __init__(self, parent=None, space=None):
        super().__init__(parent)
        self.space = space
        
        # Initialize RT60 calculator
        self.rt60_calculator = RT60Calculator()
        
        # Timer for debouncing plot updates
        self.plot_update_timer = QTimer()
        self.plot_update_timer.setSingleShot(True)
        self.plot_update_timer.timeout.connect(self.update_rt60_plot)
        
        self.init_ui()
        self.load_space_data()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"Edit Space: {self.space.name if self.space else 'Unknown'}")
        self.setModal(True)
        self.setFixedSize(1400, 1000)  # Increased width for plot
        
        layout = QVBoxLayout()
        
        # Create main splitter for tabs and plot
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Create tabs
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
        
        main_splitter.addWidget(tabs)
        
        # Right side: RT60 Plot
        self.plot_container = RT60PlotContainer()
        self.plot_container.materials_changed.connect(lambda: self.schedule_plot_update())
        main_splitter.addWidget(self.plot_container)
        
        # Set splitter proportions (60% tabs, 40% plot)
        main_splitter.setSizes([840, 560])
        
        layout.addWidget(main_splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        
        self.save_close_btn = QPushButton("Save and Close")
        self.save_close_btn.clicked.connect(self.save_and_close)
        self.save_close_btn.setDefault(True)
        
        self.preview_btn = QPushButton("Preview Calculations")
        self.preview_btn.clicked.connect(self.preview_calculations)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.save_close_btn)
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
        
        # Show associated drawing information
        self.drawing_label = QLabel("No drawing assigned")
        self.drawing_label.setStyleSheet("color: #666; font-style: italic;")
        basic_layout.addRow("Associated Drawing:", self.drawing_label)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Optional description")
        basic_layout.addRow("Description:", self.description_edit)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Geometry information
        geometry_group = QGroupBox("Geometry")
        geometry_layout = QFormLayout()
        
        self.area_spin = QDoubleSpinBox()
        self.area_spin.setRange(1.0, 100000.0)
        self.area_spin.setSuffix(" sf")
        self.area_spin.valueChanged.connect(self.calculate_volume)
        self.area_spin.valueChanged.connect(lambda: self.schedule_plot_update())
        geometry_layout.addRow("Floor Area:", self.area_spin)
        
        self.ceiling_height_spin = QDoubleSpinBox()
        self.ceiling_height_spin.setRange(6.0, 30.0)
        self.ceiling_height_spin.setValue(9.0)
        self.ceiling_height_spin.setSuffix(" ft")
        self.ceiling_height_spin.valueChanged.connect(self.calculate_volume)
        self.ceiling_height_spin.valueChanged.connect(lambda: self.schedule_plot_update())
        geometry_layout.addRow("Ceiling Height:", self.ceiling_height_spin)
        
        self.volume_label = QLabel("Not calculated")
        geometry_layout.addRow("Volume:", self.volume_label)
        
        self.wall_area_spin = QDoubleSpinBox()
        self.wall_area_spin.setRange(1.0, 100000.0)
        self.wall_area_spin.setSuffix(" sf")
        self.wall_area_spin.valueChanged.connect(lambda: self.schedule_plot_update())
        geometry_layout.addRow("Wall Area:", self.wall_area_spin)
        
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
        
        # Show calculated values as read-only
        self.calculated_rt60_label = QLabel("Not calculated")
        acoustic_layout.addRow("Calculated RT60:", self.calculated_rt60_label)
        
        self.calculated_nc_label = QLabel("Not calculated")
        acoustic_layout.addRow("Calculated NC:", self.calculated_nc_label)
        
        acoustic_group.setLayout(acoustic_layout)
        layout.addWidget(acoustic_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_materials_tab(self):
        """Create the enhanced materials selection tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Search and add materials for each surface type. Multiple materials can be selected per surface.")
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #7f8c8d; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Create scroll area for materials sections
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Ceiling materials section
        ceiling_group = QGroupBox("Ceiling Materials")
        ceiling_layout = QVBoxLayout()
        
        # Create material list widget first
        self.ceiling_materials = MaterialListWidget('ceiling')
        self.ceiling_materials.material_removed.connect(self.update_calculations_preview)
        self.ceiling_materials.material_removed.connect(lambda: self.schedule_plot_update())
        self.ceiling_materials.material_changed.connect(self.update_calculations_preview)
        self.ceiling_materials.material_changed.connect(lambda: self.schedule_plot_update())
        
        # Search widget for ceiling materials
        self.ceiling_search = MaterialSearchWidget('ceiling')
        self.ceiling_search.material_selected.connect(lambda key: self.ceiling_materials.add_material(key))
        self.ceiling_search.material_selected.connect(self.update_calculations_preview)
        self.ceiling_search.material_selected.connect(lambda: self.schedule_plot_update())
        ceiling_layout.addWidget(self.ceiling_search)
        
        # Add selected ceiling materials
        ceiling_layout.addWidget(self.ceiling_materials)
        
        ceiling_group.setLayout(ceiling_layout)
        scroll_layout.addWidget(ceiling_group)
        
        # Wall materials section
        wall_group = QGroupBox("Wall Materials")
        wall_layout = QVBoxLayout()
        
        # Create material list widget first
        self.wall_materials = MaterialListWidget('wall')
        self.wall_materials.material_removed.connect(self.update_calculations_preview)
        self.wall_materials.material_removed.connect(lambda: self.schedule_plot_update())
        self.wall_materials.material_changed.connect(self.update_calculations_preview)
        self.wall_materials.material_changed.connect(lambda: self.schedule_plot_update())
        
        # Search widget for wall materials
        self.wall_search = MaterialSearchWidget('wall')
        self.wall_search.material_selected.connect(lambda key: self.wall_materials.add_material(key))
        self.wall_search.material_selected.connect(self.update_calculations_preview)
        self.wall_search.material_selected.connect(lambda: self.schedule_plot_update())
        wall_layout.addWidget(self.wall_search)
        
        # Add selected wall materials
        wall_layout.addWidget(self.wall_materials)
        
        wall_group.setLayout(wall_layout)
        scroll_layout.addWidget(wall_group)
        
        # Floor materials section
        floor_group = QGroupBox("Floor Materials")
        floor_layout = QVBoxLayout()
        
        # Create material list widget first
        self.floor_materials = MaterialListWidget('floor')
        self.floor_materials.material_removed.connect(self.update_calculations_preview)
        self.floor_materials.material_removed.connect(lambda: self.schedule_plot_update())
        self.floor_materials.material_changed.connect(self.update_calculations_preview)
        self.floor_materials.material_changed.connect(lambda: self.schedule_plot_update())
        
        # Search widget for floor materials
        self.floor_search = MaterialSearchWidget('floor')
        self.floor_search.material_selected.connect(lambda key: self.floor_materials.add_material(key))
        self.floor_search.material_selected.connect(self.update_calculations_preview)
        self.floor_search.material_selected.connect(lambda: self.schedule_plot_update())
        floor_layout.addWidget(self.floor_search)
        
        # Add selected floor materials
        floor_layout.addWidget(self.floor_materials)
        
        floor_group.setLayout(floor_layout)
        scroll_layout.addWidget(floor_group)
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
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
        self.rt60_preview_label.setStyleSheet("font-family: monospace; background-color: #f8f9fa; color: black; padding: 10px; border: 1px solid #dee2e6;")
        self.rt60_preview_label.setWordWrap(True)
        rt60_layout.addWidget(self.rt60_preview_label)
        
        rt60_group.setLayout(rt60_layout)
        layout.addWidget(rt60_group)
        
        # Surface area breakdown
        areas_group = QGroupBox("Surface Area Breakdown")
        areas_layout = QVBoxLayout()
        
        self.areas_preview_label = QLabel("Surface areas from space geometry")
        self.areas_preview_label.setStyleSheet("font-family: monospace; background-color: #f8f9fa; color: black; padding: 10px; border: 1px solid #dee2e6;")
        areas_layout.addWidget(self.areas_preview_label)
        
        areas_group.setLayout(areas_layout)
        layout.addWidget(areas_group)
        
        # Materials breakdown
        materials_group = QGroupBox("Materials Breakdown")
        materials_layout = QVBoxLayout()
        
        self.materials_preview_label = QLabel("Selected materials and their absorption coefficients")
        self.materials_preview_label.setStyleSheet("font-family: monospace; background-color: #f8f9fa; color: black; padding: 10px; border: 1px solid #dee2e6;")
        materials_layout.addWidget(self.materials_preview_label)
        
        materials_group.setLayout(materials_layout)
        layout.addWidget(materials_group)
        
        # Total absorption
        absorption_group = QGroupBox("Total Absorption")
        absorption_layout = QVBoxLayout()
        
        self.absorption_preview_label = QLabel("Total absorption will be calculated from materials and areas")
        self.absorption_preview_label.setStyleSheet("font-family: monospace; background-color: #f8f9fa; color: black; padding: 10px; border: 1px solid #dee2e6;")
        absorption_layout.addWidget(self.absorption_preview_label)
        
        absorption_group.setLayout(absorption_layout)
        layout.addWidget(absorption_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def get_average_absorption_coefficient(self, material_keys):
        """Calculate average absorption coefficient for a list of materials"""
        if not material_keys:
            return 0.0
            
        total_coeff = 0.0
        valid_materials = 0
        
        for key in material_keys:
            if key in STANDARD_MATERIALS:
                material = STANDARD_MATERIALS[key]
                total_coeff += material['absorption_coeff']
                valid_materials += 1
                
        return total_coeff / valid_materials if valid_materials > 0 else 0.0
        
    def find_material_key_by_name(self, material_name):
        """Find material key by name (for backward compatibility)"""
        if not material_name:
            return None
            
        print(f"DEBUG: find_material_key_by_name called with: '{material_name}'")
            
        # First try exact key match
        if material_name in STANDARD_MATERIALS:
            print(f"DEBUG: Found exact key match: '{material_name}'")
            return material_name
            
        # Then try to find by name
        for key, material in STANDARD_MATERIALS.items():
            if material['name'].lower() == material_name.lower():
                print(f"DEBUG: Found name match: '{material_name}' -> '{key}'")
                return key
                
        # Try partial name match
        for key, material in STANDARD_MATERIALS.items():
            if material_name.lower() in material['name'].lower():
                print(f"DEBUG: Found partial name match: '{material_name}' -> '{key}'")
                return key
                
        print(f"DEBUG: No match found for: '{material_name}'")
        return None
            
    def load_space_data(self):
        """Load existing space data into the dialog"""
        if not self.space:
            return
            
        print(f"DEBUG: load_space_data - Loading data for space ID: {self.space.id}")
            
        # Load basic properties
        self.name_edit.setText(self.space.name or "")
        self.description_edit.setPlainText(self.space.description or "")
        
        # Load drawing information
        if self.space.drawing:
            drawing_text = f"{self.space.drawing.name}"
            if self.space.drawing.scale_string:
                drawing_text += f" (Scale: {self.space.drawing.scale_string})"
            self.drawing_label.setText(drawing_text)
            self.drawing_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        else:
            self.drawing_label.setText("No drawing assigned")
            self.drawing_label.setStyleSheet("color: #e74c3c; font-style: italic;")
        
        # Load geometry
        if self.space.floor_area:
            self.area_spin.setValue(self.space.floor_area)
        if self.space.ceiling_height:
            self.ceiling_height_spin.setValue(self.space.ceiling_height)
        if self.space.wall_area:
            self.wall_area_spin.setValue(self.space.wall_area)
            
        # Load acoustic targets
        if self.space.target_rt60:
            self.target_rt60_spin.setValue(self.space.target_rt60)
            
        # Load calculated values
        if self.space.calculated_rt60:
            self.calculated_rt60_label.setText(f"{self.space.calculated_rt60:.2f} seconds")
        if self.space.calculated_nc:
            self.calculated_nc_label.setText(f"NC {self.space.calculated_nc:.0f}")
            
        # Load materials using new multiple materials system with fallback to legacy
        print(f"DEBUG: Loading materials for space '{self.space.name}'")
        
        # Try to load from new system first
        ceiling_materials = self.space.get_ceiling_materials()
        wall_materials = self.space.get_wall_materials()
        floor_materials = self.space.get_floor_materials()
        
        print(f"DEBUG: Materials from new system:")
        print(f"  ceiling_materials: {ceiling_materials}")
        print(f"  wall_materials: {wall_materials}")
        print(f"  floor_materials: {floor_materials}")
        
        # If no materials in new system, fall back to legacy single materials
        if not ceiling_materials and self.space.ceiling_material:
            ceiling_key = self.find_material_key_by_name(self.space.ceiling_material)
            ceiling_materials = [ceiling_key] if ceiling_key else []
            print(f"DEBUG: Fallback ceiling material: {ceiling_materials}")
            
        if not wall_materials and self.space.wall_material:
            wall_key = self.find_material_key_by_name(self.space.wall_material)
            wall_materials = [wall_key] if wall_key else []
            print(f"DEBUG: Fallback wall material: {wall_materials}")
            
        if not floor_materials and self.space.floor_material:
            floor_key = self.find_material_key_by_name(self.space.floor_material)
            floor_materials = [floor_key] if floor_key else []
            print(f"DEBUG: Fallback floor material: {floor_materials}")
        
        print(f"DEBUG: Final processed materials:")
        print(f"  ceiling_materials: {ceiling_materials}")
        print(f"  wall_materials: {wall_materials}")
        print(f"  floor_materials: {floor_materials}")
        
        self.ceiling_materials.set_materials(ceiling_materials)
        self.wall_materials.set_materials(wall_materials)
        self.floor_materials.set_materials(floor_materials)
        
        # Calculate initial volume
        self.calculate_volume()
        self.update_calculations_preview()
        
        # Initialize RT60 plot
        self.schedule_plot_update()
        
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
        
        # Set materials (convert to lists for new interface)
        # Use find_material_key_by_name to handle potential key mismatches
        ceiling_key = self.find_material_key_by_name(room_type['ceiling_material'])
        wall_key = self.find_material_key_by_name(room_type['wall_material'])
        floor_key = self.find_material_key_by_name(room_type['floor_material'])
        
        ceiling_materials = [ceiling_key] if ceiling_key else []
        wall_materials = [wall_key] if wall_key else []
        floor_materials = [floor_key] if floor_key else []
        
        self.ceiling_materials.set_materials(ceiling_materials)
        self.wall_materials.set_materials(wall_materials)
        self.floor_materials.set_materials(floor_materials)
        
        # Update calculations
        self.update_calculations_preview()
        
    def calculate_volume(self):
        """Calculate room volume and update surface areas"""
        floor_area = self.area_spin.value()
        height = self.ceiling_height_spin.value()
        wall_area = self.wall_area_spin.value()
        
        if floor_area > 0 and height > 0:
            volume = floor_area * height
            self.volume_label.setText(f"{volume:,.0f} cf")
            
            # Update surface areas in material widgets
            self.ceiling_materials.set_total_surface_area(floor_area)  # Ceiling area = floor area
            self.wall_materials.set_total_surface_area(wall_area)
            self.floor_materials.set_total_surface_area(floor_area)
            
            self.update_calculations_preview()
        else:
            self.volume_label.setText("Not calculated")
            
    def update_calculations_preview(self):
        """Update the calculations preview in the calculations tab"""
        floor_area = self.area_spin.value()
        ceiling_area = floor_area
        wall_area = self.wall_area_spin.value()
        height = self.ceiling_height_spin.value()
        
        # Update areas preview
        areas_text = f"Floor Area: {floor_area:,.0f} sf\n"
        areas_text += f"Ceiling Area: {ceiling_area:,.0f} sf\n"
        areas_text += f"Wall Area: {wall_area:,.0f} sf\n"
        areas_text += f"Total Surface Area: {floor_area + ceiling_area + wall_area:,.0f} sf"
        
        self.areas_preview_label.setText(areas_text)
        
        # Get selected materials
        ceiling_materials = self.ceiling_materials.get_materials()
        wall_materials = self.wall_materials.get_materials()
        floor_materials = self.floor_materials.get_materials()
        
        # Update materials preview
        materials_text = "Selected Materials:\n"
        
        if ceiling_materials:
            materials_text += "Ceiling:\n"
            for key in ceiling_materials:
                if key in STANDARD_MATERIALS:
                    material = STANDARD_MATERIALS[key]
                    coeff = material.get('nrc', material['absorption_coeff'])
                    materials_text += f"  • {material['name']} (α={coeff:.2f})\n"
        else:
            materials_text += "Ceiling: No materials selected\n"
            
        if wall_materials:
            materials_text += "Walls:\n"
            for key in wall_materials:
                if key in STANDARD_MATERIALS:
                    material = STANDARD_MATERIALS[key]
                    coeff = material.get('nrc', material['absorption_coeff'])
                    materials_text += f"  • {material['name']} (α={coeff:.2f})\n"
        else:
            materials_text += "Walls: No materials selected\n"
            
        if floor_materials:
            materials_text += "Floor:\n"
            for key in floor_materials:
                if key in STANDARD_MATERIALS:
                    material = STANDARD_MATERIALS[key]
                    coeff = material.get('nrc', material['absorption_coeff'])
                    materials_text += f"  • {material['name']} (α={coeff:.2f})\n"
        else:
            materials_text += "Floor: No materials selected\n"
            
        self.materials_preview_label.setText(materials_text)
        
        # Calculate absorption using average coefficients
        if all([floor_area, wall_area, height]) and (ceiling_materials or wall_materials or floor_materials):
            ceiling_coeff = self.get_average_absorption_coefficient(ceiling_materials)
            wall_coeff = self.get_average_absorption_coefficient(wall_materials)
            floor_coeff = self.get_average_absorption_coefficient(floor_materials)
            
            ceiling_absorption = ceiling_area * ceiling_coeff
            wall_absorption = wall_area * wall_coeff
            floor_absorption = floor_area * floor_coeff
            total_absorption = ceiling_absorption + wall_absorption + floor_absorption
            
            # Update absorption preview
            absorption_text = f"Ceiling: {ceiling_area:.0f} sf × {ceiling_coeff:.3f} = {ceiling_absorption:.1f} sabins\n"
            absorption_text += f"Walls: {wall_area:.0f} sf × {wall_coeff:.3f} = {wall_absorption:.1f} sabins\n"
            absorption_text += f"Floor: {floor_area:.0f} sf × {floor_coeff:.3f} = {floor_absorption:.1f} sabins\n"
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
            else:
                self.rt60_preview_label.setText("Please select materials to calculate RT60")
                self.absorption_preview_label.setText("No materials selected")
        else:
            self.rt60_preview_label.setText("Please enter room dimensions and select materials")
            self.absorption_preview_label.setText("No materials selected")
            
    def preview_calculations(self):
        """Preview the acoustic calculations"""
        self.update_calculations_preview()
        
    def save_changes(self):
        """Save changes to the space"""
        # Validate inputs
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Room name is required.")
            self.name_edit.setFocus()
            return
            
        # Get material selections
        ceiling_materials = self.ceiling_materials.get_materials()
        wall_materials = self.wall_materials.get_materials()
        floor_materials = self.floor_materials.get_materials()
        
        print(f"DEBUG: save_changes - Current materials in widgets:")
        print(f"  ceiling_materials: {ceiling_materials}")
        print(f"  wall_materials: {wall_materials}")
        print(f"  floor_materials: {floor_materials}")
        
        # For backward compatibility, use the first material of each type
        # In a future update, the database schema could be modified to store multiple materials
        ceiling_key = ceiling_materials[0] if ceiling_materials else None
        wall_key = wall_materials[0] if wall_materials else None
        floor_key = floor_materials[0] if floor_materials else None
        
        print(f"DEBUG: save_changes - Materials to save:")
        print(f"  ceiling_materials: {ceiling_materials}")
        print(f"  wall_materials: {wall_materials}")
        print(f"  floor_materials: {floor_materials}")
        
        if not any([ceiling_materials, wall_materials, floor_materials]):
            QMessageBox.warning(self, "Validation Error", "Please select at least one material for surfaces.")
            return
            
        session = None
        try:
            session = get_session()
            
            # Merge the space object into this session to ensure it's tracked
            space = session.merge(self.space)
            
            # Update space properties
            space.name = name
            space.description = self.description_edit.toPlainText().strip()
            space.floor_area = self.area_spin.value()
            space.ceiling_height = self.ceiling_height_spin.value()
            space.wall_area = self.wall_area_spin.value()
            space.target_rt60 = self.target_rt60_spin.value()
            
            # Store multiple materials using new system
            space.set_surface_materials(SurfaceType.CEILING, ceiling_materials, session)
            space.set_surface_materials(SurfaceType.WALL, wall_materials, session)
            space.set_surface_materials(SurfaceType.FLOOR, floor_materials, session)
            
            # Update legacy fields for backward compatibility (use first material)
            space.ceiling_material = ceiling_materials[0] if ceiling_materials else None
            space.wall_material = wall_materials[0] if wall_materials else None
            space.floor_material = floor_materials[0] if floor_materials else None
            
            print(f"DEBUG: save_changes - Multiple materials saved to space object")
            print(f"DEBUG: save_changes - Legacy compatibility fields updated:")
            print(f"  space.ceiling_material: '{space.ceiling_material}'")
            print(f"  space.wall_material: '{space.wall_material}'")
            print(f"  space.floor_material: '{space.floor_material}'")
            
            # Recalculate volume
            space.calculate_volume()
            
            # Update the dialog's space reference to the merged object
            self.space = space
            
            # Flush changes to database before commit to ensure they are persisted
            session.flush()
            
            # Commit changes
            session.commit()
            
            print(f"DEBUG: save_changes - Changes flushed and committed successfully")
            print(f"DEBUG: save_changes - Space ID: {space.id}")
            
            # Verify the changes were actually saved by doing a fresh query
            fresh_space = session.query(Space).filter(Space.id == space.id).first()
            print(f"DEBUG: save_changes - Fresh query verification:")
            print(f"  fresh_space ceiling materials: {fresh_space.get_ceiling_materials()}")
            print(f"  fresh_space wall materials: {fresh_space.get_wall_materials()}")
            print(f"  fresh_space floor materials: {fresh_space.get_floor_materials()}")
            
            session.close()
            
            # Don't close the dialog - just show success message
            QMessageBox.information(self, "Success", f"Space '{name}' updated successfully!")
            
            # Update calculations preview to reflect saved changes
            self.update_calculations_preview()
            
        except Exception as e:
            if session:
                session.rollback()
                session.close()
            QMessageBox.critical(self, "Error", f"Failed to save changes:\n{str(e)}")
            
    def save_and_close(self):
        """Save changes and close the dialog"""
        # First save the changes
        self.save_changes()
        
        # Then close the dialog
        self.accept()
    
    def schedule_plot_update(self):
        """Schedule a plot update with debouncing"""
        self.plot_update_timer.start(300)  # 300ms delay to debounce rapid changes
    
    def update_rt60_plot(self):
        """Update the RT60 plot with current space data"""
        try:
            # Get current room volume
            floor_area = self.area_spin.value()
            height = self.ceiling_height_spin.value()
            volume = floor_area * height
            
            if volume <= 0:
                self.plot_container.clear_rt60_data()
                return
            
            # Update plot with current volume
            self.plot_container.update_volume(volume)
            
            # Get material data with square footages
            ceiling_materials_data = self.ceiling_materials.get_materials_data()
            wall_materials_data = self.wall_materials.get_materials_data()
            floor_materials_data = self.floor_materials.get_materials_data()
            
            # Extract just the keys for backward compatibility with plot container
            ceiling_materials = [m['material_key'] for m in ceiling_materials_data]
            wall_materials = [m['material_key'] for m in wall_materials_data]  
            floor_materials = [m['material_key'] for m in floor_materials_data]
            
            # Update materials summary with current data including specific square footages
            areas = {
                'ceiling_area': floor_area,
                'wall_area': self.wall_area_spin.value(),
                'floor_area': floor_area
            }
            
            # Pass the detailed materials data if available
            if hasattr(self.plot_container, 'update_materials_data_detailed'):
                self.plot_container.update_materials_data_detailed(
                    ceiling_materials, wall_materials, floor_materials, areas,
                    ceiling_materials_data, wall_materials_data, floor_materials_data
                )
            else:
                # Fallback to old method
                self.plot_container.update_materials_data(
                    ceiling_materials, wall_materials, floor_materials, areas
                )
            
            # Get doors/windows data from the materials summary
            doors_windows_data = self.plot_container.get_doors_windows_data()
            
            # Check if we have materials to calculate with
            if not any([ceiling_materials_data, wall_materials_data, floor_materials_data, doors_windows_data]):
                self.plot_container.clear_rt60_data()
                return
            
            # Prepare space data for RT60 calculation including doors/windows with actual square footages
            space_data = {
                'volume': volume,
                'floor_area': floor_area,
                'ceiling_area': floor_area,  # Assume ceiling area = floor area
                'wall_area': self.wall_area_spin.value(),
                'ceiling_materials_data': ceiling_materials_data,
                'wall_materials_data': wall_materials_data,
                'floor_materials_data': floor_materials_data,
                'doors_windows': doors_windows_data,
                'include_doors_windows': True,
                # Keep old format for backward compatibility
                'ceiling_materials': ceiling_materials,
                'wall_materials': wall_materials,
                'floor_materials': floor_materials,
            }
            
            # Calculate RT60 frequency response
            results = self.rt60_calculator.calculate_rt60_frequency_response(space_data)
            
            # Update plot with RT60 data
            rt60_by_freq = results.get('rt60_by_frequency', {})
            self.plot_container.update_rt60_data(rt60_by_freq)
            
        except Exception as e:
            print(f"Error updating RT60 plot: {e}")
            self.plot_container.clear_rt60_data()
        
                
    def get_updated_space_data(self):
        """Get the updated space data as a dictionary for external use"""
        return {
            'id': self.space.id,
            'name': self.space.name,
            'ceiling_material': self.space.ceiling_material,
            'wall_material': self.space.wall_material,
            'floor_material': self.space.floor_material,
            'description': self.space.description
        }