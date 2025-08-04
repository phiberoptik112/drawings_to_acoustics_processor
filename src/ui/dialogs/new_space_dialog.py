"""
New Space Dialog - Provides multiple options for creating spaces
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QListWidget, QListWidgetItem, QMessageBox,
                             QTabWidget, QWidget, QCheckBox, QButtonGroup,
                             QRadioButton, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon

from models import get_session
from models.space import Space
from models.drawing import Drawing
from data.materials import STANDARD_MATERIALS, ROOM_TYPE_DEFAULTS


class NewSpaceDialog(QDialog):
    """Dialog for creating new spaces with multiple creation methods"""
    
    def __init__(self, parent=None, project_id=None):
        super().__init__(parent)
        self.project_id = project_id
        self.creation_method = "manual"  # "manual", "from_drawing", "from_rectangle"
        self.selected_drawing = None
        self.selected_rectangle = None
        
        self.init_ui()
        self.load_drawings()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Create New Space")
        self.setModal(True)
        self.setFixedSize(700, 800)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Create New Space")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Creation method selection
        method_group = QGroupBox("How would you like to create the space?")
        method_layout = QVBoxLayout()
        
        self.method_group = QButtonGroup()
        
        # Manual creation
        self.manual_radio = QRadioButton("📝 Manual Entry")
        self.manual_radio.setChecked(True)
        self.manual_radio.toggled.connect(lambda checked: self.set_method("manual") if checked else None)
        method_layout.addWidget(self.manual_radio)
        
        manual_desc = QLabel("Create a space by entering dimensions and properties manually")
        manual_desc.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px; margin-bottom: 10px;")
        method_layout.addWidget(manual_desc)
        
        # From drawing rectangles
        self.drawing_radio = QRadioButton("📐 From Drawing Rectangle")
        self.drawing_radio.toggled.connect(lambda checked: self.set_method("from_drawing") if checked else None)
        method_layout.addWidget(self.drawing_radio)
        
        drawing_desc = QLabel("Convert a rectangle you've drawn on a PDF into a space with precise measurements")
        drawing_desc.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px; margin-bottom: 10px;")
        method_layout.addWidget(drawing_desc)
        
        # Future: from template
        self.template_radio = QRadioButton("📋 From Template")
        self.template_radio.setEnabled(False)  # Not implemented yet
        method_layout.addWidget(self.template_radio)
        
        template_desc = QLabel("Create from a predefined room template (Coming Soon)")
        template_desc.setStyleSheet("color: #999; font-size: 11px; margin-left: 20px; margin-bottom: 10px;")
        method_layout.addWidget(template_desc)
        
        self.method_group.addButton(self.manual_radio, 0)
        self.method_group.addButton(self.drawing_radio, 1)
        self.method_group.addButton(self.template_radio, 2)
        
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # Stacked widget for different creation methods
        self.create_creation_widgets()
        layout.addWidget(self.manual_widget)
        layout.addWidget(self.drawing_widget)
        
        # Initially show manual widget
        self.drawing_widget.hide()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("Create Space")
        self.create_btn.clicked.connect(self.create_space)
        self.create_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_creation_widgets(self):
        """Create widgets for different creation methods"""
        # Manual creation widget
        self.manual_widget = QWidget()
        manual_layout = QVBoxLayout()
        
        # Basic properties
        basic_group = QGroupBox("Basic Properties")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter space name (e.g., Conference Room 101)")
        basic_layout.addRow("Space Name:", self.name_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Optional description")
        basic_layout.addRow("Description:", self.description_edit)
        
        basic_group.setLayout(basic_layout)
        manual_layout.addWidget(basic_group)
        
        # Dimensions
        dimensions_group = QGroupBox("Dimensions")
        dimensions_layout = QFormLayout()
        
        self.floor_area_spin = QDoubleSpinBox()
        self.floor_area_spin.setRange(1.0, 100000.0)
        self.floor_area_spin.setValue(200.0)
        self.floor_area_spin.setSuffix(" sf")
        dimensions_layout.addRow("Floor Area:", self.floor_area_spin)
        
        self.ceiling_height_spin = QDoubleSpinBox()
        self.ceiling_height_spin.setRange(6.0, 30.0)
        self.ceiling_height_spin.setValue(9.0)
        self.ceiling_height_spin.setSuffix(" ft")
        dimensions_layout.addRow("Ceiling Height:", self.ceiling_height_spin)
        
        self.wall_area_spin = QDoubleSpinBox()
        self.wall_area_spin.setRange(1.0, 100000.0)
        self.wall_area_spin.setValue(500.0)
        self.wall_area_spin.setSuffix(" sf")
        dimensions_layout.addRow("Wall Area:", self.wall_area_spin)
        
        dimensions_group.setLayout(dimensions_layout)
        manual_layout.addWidget(dimensions_group)
        
        # Room type presets
        preset_group = QGroupBox("Room Type Preset (Optional)")
        preset_layout = QVBoxLayout()
        
        self.room_type_combo = QComboBox()
        self.room_type_combo.addItem("Custom (No Preset)", None)
        
        for key, room_type in ROOM_TYPE_DEFAULTS.items():
            self.room_type_combo.addItem(room_type['name'], key)
            
        self.room_type_combo.currentIndexChanged.connect(self.apply_room_preset)
        preset_layout.addWidget(self.room_type_combo)
        
        preset_group.setLayout(preset_layout)
        manual_layout.addWidget(preset_group)
        
        # Acoustic targets
        acoustic_group = QGroupBox("Acoustic Target")
        acoustic_layout = QFormLayout()
        
        self.target_rt60_spin = QDoubleSpinBox()
        self.target_rt60_spin.setRange(0.3, 3.0)
        self.target_rt60_spin.setValue(0.8)
        self.target_rt60_spin.setSuffix(" seconds")
        self.target_rt60_spin.setSingleStep(0.1)
        acoustic_layout.addRow("Target RT60:", self.target_rt60_spin)
        
        acoustic_group.setLayout(acoustic_layout)
        manual_layout.addWidget(acoustic_group)
        
        self.manual_widget.setLayout(manual_layout)
        
        # Drawing-based creation widget
        self.drawing_widget = QWidget()
        drawing_layout = QVBoxLayout()
        
        # Drawing selection
        drawing_select_group = QGroupBox("Select Drawing and Rectangle")
        drawing_select_layout = QVBoxLayout()
        
        self.drawings_combo = QComboBox()
        self.drawings_combo.currentIndexChanged.connect(self.drawing_selected)
        drawing_select_layout.addWidget(QLabel("Drawing:"))
        drawing_select_layout.addWidget(self.drawings_combo)
        
        self.rectangles_list = QListWidget()
        self.rectangles_list.setMaximumHeight(150)
        self.rectangles_list.itemSelectionChanged.connect(self.rectangle_selected)
        drawing_select_layout.addWidget(QLabel("Available Rectangles:"))
        drawing_select_layout.addWidget(self.rectangles_list)
        
        # Instructions
        instructions = QLabel(
            "💡 Instructions:\n"
            "1. First, select a drawing from the dropdown\n"
            "2. Choose a rectangle from the list\n"
            "3. The space will be created with precise measurements from the rectangle"
        )
        instructions.setStyleSheet("color: #2c3e50; background-color: #ecf0f1; padding: 10px; border-radius: 5px;")
        drawing_select_layout.addWidget(instructions)
        
        drawing_select_group.setLayout(drawing_select_layout)
        drawing_layout.addWidget(drawing_select_group)
        
        # Selected rectangle info
        self.rect_info_group = QGroupBox("Selected Rectangle Details")
        rect_info_layout = QFormLayout()
        
        self.rect_area_label = QLabel("No rectangle selected")
        self.rect_dimensions_label = QLabel("No rectangle selected")
        
        rect_info_layout.addRow("Area:", self.rect_area_label)
        rect_info_layout.addRow("Dimensions:", self.rect_dimensions_label)
        
        self.rect_info_group.setLayout(rect_info_layout)
        drawing_layout.addWidget(self.rect_info_group)
        
        # Space properties for drawing method
        drawing_props_group = QGroupBox("Space Properties")
        drawing_props_layout = QFormLayout()
        
        self.drawing_name_edit = QLineEdit()
        self.drawing_name_edit.setPlaceholderText("Enter space name")
        drawing_props_layout.addRow("Space Name:", self.drawing_name_edit)
        
        self.drawing_height_spin = QDoubleSpinBox()
        self.drawing_height_spin.setRange(6.0, 30.0)
        self.drawing_height_spin.setValue(9.0)
        self.drawing_height_spin.setSuffix(" ft")
        drawing_props_layout.addRow("Ceiling Height:", self.drawing_height_spin)
        
        drawing_props_group.setLayout(drawing_props_layout)
        drawing_layout.addWidget(drawing_props_group)
        
        self.drawing_widget.setLayout(drawing_layout)
        
    def set_method(self, method):
        """Set the creation method"""
        self.creation_method = method
        
        if method == "manual":
            self.manual_widget.show()
            self.drawing_widget.hide()
        elif method == "from_drawing":
            self.manual_widget.hide()
            self.drawing_widget.show()
            
    def load_drawings(self):
        """Load available drawings"""
        if not self.project_id:
            return
            
        try:
            session = get_session()
            drawings = session.query(Drawing).filter(Drawing.project_id == self.project_id).all()
            
            self.drawings_combo.clear()
            self.drawings_combo.addItem("Select a drawing...", None)
            
            for drawing in drawings:
                self.drawings_combo.addItem(drawing.name, drawing.id)
                
            session.close()
            
        except Exception as e:
            print(f"Error loading drawings: {e}")
            
    def drawing_selected(self):
        """Handle drawing selection"""
        drawing_id = self.drawings_combo.currentData()
        if not drawing_id:
            self.rectangles_list.clear()
            return
            
        # Load rectangles for this drawing
        # This is a placeholder - in a real implementation, you'd load
        # drawing elements from the database
        self.rectangles_list.clear()
        
        # Add some sample rectangles for demonstration
        for i in range(3):
            item = QListWidgetItem(f"🔲 Rectangle {i+1} - {100 + i*50} sf")
            item.setData(Qt.UserRole, {
                'area_real': 100 + i*50,
                'width_real': 10 + i*2,
                'height_real': 10 + i*1,
                'x': 100 + i*50,
                'y': 200 + i*30
            })
            self.rectangles_list.addItem(item)
            
    def rectangle_selected(self):
        """Handle rectangle selection"""
        current_item = self.rectangles_list.currentItem()
        if not current_item:
            self.rect_area_label.setText("No rectangle selected")
            self.rect_dimensions_label.setText("No rectangle selected")
            return
            
        rect_data = current_item.data(Qt.UserRole)
        self.selected_rectangle = rect_data
        
        # Update info labels
        area = rect_data.get('area_real', 0)
        width = rect_data.get('width_real', 0)
        height = rect_data.get('height_real', 0)
        
        self.rect_area_label.setText(f"{area:.1f} sf")
        self.rect_dimensions_label.setText(f"{width:.1f} ft × {height:.1f} ft")
        
    def apply_room_preset(self):
        """Apply room type preset"""
        room_type_key = self.room_type_combo.currentData()
        if not room_type_key or room_type_key not in ROOM_TYPE_DEFAULTS:
            return
            
        room_type = ROOM_TYPE_DEFAULTS[room_type_key]
        
        # Set target RT60
        self.target_rt60_spin.setValue(room_type['target_rt60'])
        
    def create_space(self):
        """Create the space based on selected method"""
        if self.creation_method == "manual":
            self.create_manual_space()
        elif self.creation_method == "from_drawing":
            self.create_space_from_drawing()
            
    def create_manual_space(self):
        """Create space manually"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Space name is required.")
            return
            
        try:
            session = get_session()
            
            # Get room type preset for materials
            room_type_key = self.room_type_combo.currentData()
            room_type = ROOM_TYPE_DEFAULTS.get(room_type_key, {}) if room_type_key else {}
            
            space = Space(
                project_id=self.project_id,
                name=name,
                description=self.description_edit.toPlainText().strip(),
                floor_area=self.floor_area_spin.value(),
                ceiling_height=self.ceiling_height_spin.value(),
                wall_area=self.wall_area_spin.value(),
                target_rt60=self.target_rt60_spin.value(),
                # Set materials from preset or defaults
                ceiling_material=room_type.get('ceiling_material', 'acoustic_ceiling_tile'),
                wall_material=room_type.get('wall_material', 'painted_drywall'),
                floor_material=room_type.get('floor_material', 'carpet_on_concrete')
            )
            
            # Calculate volume
            space.calculate_volume()
            
            session.add(space)
            session.commit()
            session.close()
            
            QMessageBox.information(
                self,
                "Space Created",
                f"Space '{name}' created successfully!\n\n"
                f"Area: {space.floor_area:.1f} sf\n"
                f"Volume: {space.volume:.1f} cf\n"
                f"Target RT60: {space.target_rt60:.1f} seconds"
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create space:\n{str(e)}")
            
    def create_space_from_drawing(self):
        """Create space from drawing rectangle"""
        name = self.drawing_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Space name is required.")
            return
            
        if not self.selected_rectangle:
            QMessageBox.warning(self, "Validation Error", "Please select a rectangle.")
            return
            
        drawing_id = self.drawings_combo.currentData()
        if not drawing_id:
            QMessageBox.warning(self, "Validation Error", "Please select a drawing.")
            return
            
        # This would integrate with the existing RoomPropertiesDialog workflow
        QMessageBox.information(
            self,
            "Feature Integration",
            "This feature will integrate with the existing drawing interface.\n\n"
            "For now, please:\n"
            "1. Go to the drawing interface\n"
            "2. Draw a rectangle on the PDF\n"
            "3. Right-click the rectangle and select 'Create Room/Space'"
        )
        
        self.reject()