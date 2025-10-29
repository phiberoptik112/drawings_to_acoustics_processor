"""
HVAC Path Dialog - Create and manage complete HVAC paths with components and segments
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QListWidget,
                             QListWidgetItem, QSplitter, QTabWidget, QWidget,
                             QPlainTextEdit, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import get_session
from models.mechanical import MechanicalUnit
from models.hvac import HVACPath, HVACComponent, HVACSegment
from sqlalchemy.orm import selectinload
from models.space import Space
from calculations.hvac_path_calculator import HVACPathCalculator
from .hvac_component_dialog import HVACComponentDialog
from .component_library_dialog import ComponentLibraryDialog
from .hvac_receiver_dialog import HVACReceiverDialog
from .hvac_segment_dialog import HVACSegmentDialog


class ComponentListWidget(QListWidget):
    """List widget for displaying HVAC components in a path"""
    
    component_selected = Signal(HVACComponent)
    component_double_clicked = Signal(HVACComponent)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.components = []
        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
    def set_components(self, components):
        """Set components to display"""
        self.components = components
        self.clear()
        
        for i, component in enumerate(components):
            item_text = f"{i+1}. {component.name} ({component.component_type})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, component)
            self.addItem(item)
    
    def on_item_clicked(self, item):
        """Handle item click"""
        component = item.data(Qt.UserRole)
        self.component_selected.emit(component)
    
    def on_item_double_clicked(self, item):
        """Handle item double click"""
        component = item.data(Qt.UserRole)
        self.component_double_clicked.emit(component)


class SegmentListWidget(QListWidget):
    """List widget for displaying HVAC segments in a path"""
    
    segment_selected = Signal(HVACSegment)
    segment_double_clicked = Signal(HVACSegment)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []
        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
    def set_segments(self, segments):
        """Set segments to display"""
        self.segments = segments
        self.clear()
        
        for segment in segments:
            from_comp = segment.from_component.name if segment.from_component else "Unknown"
            to_comp = segment.to_component.name if segment.to_component else "Unknown"
            item_text = f"{from_comp} → {to_comp} ({segment.length:.1f} ft)"
            item = QListWidgetItem(item_text)
            # Store segment ID instead of the object to avoid DetachedInstanceError
            item.setData(Qt.UserRole, segment.id if hasattr(segment, 'id') else segment)
            self.addItem(item)
    
    def on_item_clicked(self, item):
        """Handle item click"""
        segment = item.data(Qt.UserRole)
        self.segment_selected.emit(segment)
    
    def on_item_double_clicked(self, item):
        """Handle item double click"""
        segment = item.data(Qt.UserRole)
        self.segment_double_clicked.emit(segment)


class PathDiagramText(QPlainTextEdit):
    """Read-only ASCII diagram viewer that reports clicked line numbers."""
    line_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFont(QFont("Courier New", 10))

    def mousePressEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        self.line_clicked.emit(cursor.blockNumber())
        super().mousePressEvent(event)


class HVACPathDialog(QDialog):
    """Dialog for creating and managing HVAC paths"""
    
    path_saved = Signal(HVACPath)  # Emits saved path
    
    def __init__(self, parent=None, project_id=None, path=None):
        super().__init__(parent)
        self.project_id = project_id
        self.path = path  # Existing path for editing
        self.is_editing = path is not None
        # Store primitive path id to avoid detached SQLAlchemy access
        self.path_id = getattr(path, 'id', None)
        
        # Components and segments for this path
        self.components = []
        self.segments = []
        
        # Drawing data (for creating from drawing elements)
        self.drawing_components = []
        self.drawing_segments = []
        self.drawing_id = None
        
        # Calculator
        self.path_calculator = HVACPathCalculator(self.project_id)
        # Last calculation element results for component context lookups
        self._last_element_results = []
        # Selected Mechanical Unit (library) source data for calculations
        self.source_octave_bands = None  # list[float] | None
        self.source_noise_dba = None     # float | None
        self._selected_source_label = None
        
        self.init_ui()
        if self.is_editing:
            self.load_path_data()
        else:
            self.load_project_components()
    
    def set_drawing_data(self, components, segments, drawing_id):
        """Set drawing data for creating path from drawing elements"""
        print(f"DEBUG: set_drawing_data called with {len(components)} components and {len(segments)} segments")
        
        self.drawing_components = components
        self.drawing_segments = segments
        self.drawing_id = drawing_id
        
        # Convert drawing components to dialog format
        self.components = []
        for comp_data in components:
            print(f"DEBUG: Processing component: {comp_data.get('component_type', 'unknown')} at ({comp_data.get('x', 0)}, {comp_data.get('y', 0)})")
            # Create a simple component object for the dialog
            component = type('Component', (), {
                'id': len(self.components) + 1,
                'name': f"{comp_data.get('component_type', 'unknown').upper()}-{len(self.components) + 1}",
                'component_type': comp_data.get('component_type', 'unknown'),
                'x_position': comp_data.get('x', 0),
                'y_position': comp_data.get('y', 0),
                'noise_level': comp_data.get('noise_level', 50.0)
            })()
            self.components.append(component)
        
        # Convert drawing segments to dialog format
        self.segments = []
        for i, seg_data in enumerate(segments):
            print(f"DEBUG: Processing segment {i}: from_component={seg_data.get('from_component') is not None}, to_component={seg_data.get('to_component') is not None}")
            
            # Find connected components
            from_comp = None
            to_comp = None
            
            if seg_data.get('from_component'):
                from_comp = self.find_component_by_data(seg_data['from_component'])
                print(f"DEBUG: Found from_component: {from_comp is not None}")
            if seg_data.get('to_component'):
                to_comp = self.find_component_by_data(seg_data['to_component'])
                print(f"DEBUG: Found to_component: {to_comp is not None}")
            
            # Accept segments with at least one component connection
            if from_comp or to_comp:
                print(f"DEBUG: Creating segment {i} from {from_comp.component_type if from_comp else 'None'} to {to_comp.component_type if to_comp else 'None'}")
                # Create a simple segment object for the dialog
                segment = type('Segment', (), {
                    'id': len(self.segments) + 1,
                    'hvac_path_id': None,
                    'from_component_id': from_comp.id if from_comp else None,
                    'to_component_id': to_comp.id if to_comp else None,
                    'from_component': from_comp,
                    'to_component': to_comp,
                    'length': seg_data.get('length_real', 0),
                    'segment_order': i + 1,
                    'duct_width': 12,
                    'duct_height': 8,
                    'duct_shape': 'rectangular',
                    'duct_type': 'sheet_metal',
                    'insulation': None,
                    'distance_loss': 0,
                    'duct_loss': 0,
                    'fitting_additions': 0
                })()
                self.segments.append(segment)
            else:
                print(f"DEBUG: Skipping segment {i} - no component connections")
        
        print(f"DEBUG: Created {len(self.components)} dialog components and {len(self.segments)} dialog segments")
        
        # Update the UI
        self.update_component_list()
        self.update_segment_list()
        self.update_summary()
    
    def find_component_by_data(self, comp_data):
        """Find component by drawing data"""
        for comp in self.components:
            if (comp.x_position == comp_data.get('x', 0) and 
                comp.y_position == comp_data.get('y', 0) and
                comp.component_type == comp_data.get('component_type', 'unknown')):
                return comp
        return None
        
    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit HVAC Path" if self.is_editing else "Create HVAC Path"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(900, 700)
        self.setSizeGripEnabled(True)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel(title)
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(header_label)
        
        # Main content: tabs on the left + ASCII path diagram on the right
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Tabs (left side)
        self.tabs = QTabWidget()

        # Path Information tab
        info_tab = self.create_path_info_tab()
        self.info_tab_index = self.tabs.addTab(info_tab, "Path Information")

        # Components tab
        components_tab = self.create_components_tab()
        self.components_tab_index = self.tabs.addTab(components_tab, "Components")

        # Segments tab
        segments_tab = self.create_segments_tab()
        self.segments_tab_index = self.tabs.addTab(segments_tab, "Segments")

        # Analysis tab
        analysis_tab = self.create_analysis_tab()
        self.analysis_tab_index = self.tabs.addTab(analysis_tab, "Analysis")
        
        # Compare Paths tab
        compare_tab = self.create_compare_paths_tab()
        self.compare_tab_index = self.tabs.addTab(compare_tab, "Compare Paths")

        # Ensure tabs expand with window
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_splitter.addWidget(self.tabs)

        # Right side: NC summary + ASCII diagram panel
        diagram_panel = self.create_ascii_diagram_panel()
        self.main_splitter.addWidget(diagram_panel)
        self.main_splitter.setSizes([650, 250])
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)

        layout.addWidget(self.main_splitter)
        # Give the splitter all extra vertical space
        layout.setStretch(0, 0)  # header
        layout.setStretch(1, 1)  # splitter
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if self.is_editing:
            self.delete_btn = QPushButton("Delete Path")
            self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            self.delete_btn.clicked.connect(self.delete_path)
            button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.calculate_btn = QPushButton("Calculate Noise")
        self.calculate_btn.clicked.connect(self.calculate_path_noise)
        button_layout.addWidget(self.calculate_btn)
        
        # Debug button (only show if HVAC_DEBUG_EXPORT is enabled or if we have a path ID)
        import os
        if os.environ.get('HVAC_DEBUG_EXPORT') or (hasattr(self, 'path_id') and self.path_id):
            self.debug_btn = QPushButton("Debug Info")
            self.debug_btn.clicked.connect(self.show_debug_dialog)
            button_layout.addWidget(self.debug_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        save_text = "Update Path" if self.is_editing else "Create Path"
        self.save_btn = QPushButton(save_text)
        self.save_btn.clicked.connect(self.save_path)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_path_info_tab(self):
        """Create the path information tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Path Information
        info_group = QGroupBox("Path Information")
        info_layout = QFormLayout()
        
        # Path name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Supply Path A, Return Path 1")
        info_layout.addRow("Path Name:", self.name_edit)
        
        # Path type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["supply", "return", "exhaust"])
        info_layout.addRow("Path Type:", self.type_combo)
        
        # Target space
        self.space_combo = QComboBox()
        self.load_spaces()
        # Update ASCII diagram when target space changes
        self.space_combo.currentIndexChanged.connect(self.update_path_diagram)
        info_layout.addRow("Target Space:", self.space_combo)
        
        # Drawing set
        self.drawing_set_combo = QComboBox()
        self.load_drawing_sets()
        info_layout.addRow("Drawing Set:", self.drawing_set_combo)
        
        # Description
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(100)
        self.description_text.setPlaceholderText("Description of this HVAC path...")
        info_layout.addRow("Description:", self.description_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Path Summary
        summary_group = QGroupBox("Path Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_label = QLabel("No components or segments added yet.")
        self.summary_label.setStyleSheet("color: #666; font-style: italic;")
        summary_layout.addWidget(self.summary_label)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_ascii_diagram_panel(self):
        """Create the right-side panel showing Path NC summary and ASCII path diagram."""
        panel = QWidget()
        root_v = QVBoxLayout()

        # Header
        header = QHBoxLayout()
        title_left = QLabel("Path NC")
        title_left.setFont(QFont("Arial", 12, QFont.Bold))
        title_right = QLabel("Path Diagram")
        title_right.setFont(QFont("Arial", 12, QFont.Bold))
        header.addWidget(title_left)
        header.addStretch()
        header.addWidget(title_right)
        root_v.addLayout(header)

        # Content area: left NC list, right ASCII diagram
        content = QHBoxLayout()

        # NC list
        self.nc_list = QListWidget()
        self.nc_list.setFixedWidth(90)
        self.nc_list.setSelectionMode(QListWidget.NoSelection)
        self.nc_list.setFocusPolicy(Qt.NoFocus)
        content.addWidget(self.nc_list)

        # ASCII diagram
        self.diagram_text = PathDiagramText()
        self.diagram_text.setPlaceholderText("ASCII diagram will appear here when components/segments are defined.")
        self.diagram_text.line_clicked.connect(self.on_diagram_line_clicked)
        self.diagram_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content.addWidget(self.diagram_text)

        root_v.addLayout(content)
        panel.setLayout(root_v)
        return panel
        
    def create_components_tab(self):
        """Create the components tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Component management
        component_group = QGroupBox("Path Components")
        component_layout = QVBoxLayout()
        
        # Component list
        self.component_list = ComponentListWidget()
        self.component_list.component_double_clicked.connect(self.edit_component)
        component_layout.addWidget(self.component_list)
        
        # Component buttons
        comp_button_layout = QHBoxLayout()
        
        self.add_comp_btn = QPushButton("Add Component")
        self.add_comp_btn.clicked.connect(self.add_component)
        comp_button_layout.addWidget(self.add_comp_btn)
        
        self.edit_comp_btn = QPushButton("Edit Component")
        self.edit_comp_btn.setEnabled(False)
        self.edit_comp_btn.clicked.connect(self.edit_component)
        comp_button_layout.addWidget(self.edit_comp_btn)
        
        self.remove_comp_btn = QPushButton("Remove Component")
        self.remove_comp_btn.setEnabled(False)
        self.remove_comp_btn.clicked.connect(self.remove_component)
        comp_button_layout.addWidget(self.remove_comp_btn)
        
        comp_button_layout.addStretch()
        component_layout.addLayout(comp_button_layout)
        
        component_group.setLayout(component_layout)
        layout.addWidget(component_group)
        
        # Available components
        available_group = QGroupBox("Available Components")
        available_layout = QVBoxLayout()
        
        self.available_list = QListWidget()
        self.available_list.itemDoubleClicked.connect(self.add_existing_component)
        available_layout.addWidget(self.available_list)
        
        available_group.setLayout(available_layout)
        layout.addWidget(available_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_segments_tab(self):
        """Create the segments tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Segment management
        segment_group = QGroupBox("Path Segments")
        segment_layout = QVBoxLayout()
        
        # Segment list
        self.segment_list = SegmentListWidget()
        self.segment_list.segment_double_clicked.connect(self.edit_segment)
        segment_layout.addWidget(self.segment_list)
        
        # Segment buttons
        seg_button_layout = QHBoxLayout()
        
        self.add_seg_btn = QPushButton("Add Segment")
        self.add_seg_btn.setEnabled(False)
        self.add_seg_btn.clicked.connect(self.add_segment)
        seg_button_layout.addWidget(self.add_seg_btn)
        
        self.edit_seg_btn = QPushButton("Edit Segment")
        self.edit_seg_btn.setEnabled(False)
        self.edit_seg_btn.clicked.connect(self.edit_segment)
        seg_button_layout.addWidget(self.edit_seg_btn)
        
        self.remove_seg_btn = QPushButton("Remove Segment")
        self.remove_seg_btn.setEnabled(False)
        self.remove_seg_btn.clicked.connect(self.remove_segment)
        seg_button_layout.addWidget(self.remove_seg_btn)
        
        seg_button_layout.addStretch()
        segment_layout.addLayout(seg_button_layout)
        
        segment_group.setLayout(segment_layout)
        layout.addWidget(segment_group)
        
        # Segment info
        info_group = QGroupBox("Segment Information")
        info_layout = QVBoxLayout()
        
        self.segment_info_label = QLabel("Select a segment to view details.")
        self.segment_info_label.setStyleSheet("color: #666; font-style: italic;")
        info_layout.addWidget(self.segment_info_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_analysis_tab(self):
        """Create the analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Analysis results
        results_group = QGroupBox("Noise Analysis Results")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setHtml("<i>Click 'Calculate Noise' to analyze this path</i>")
        # Ensure the results area can grow to use vertical space
        self.results_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        results_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(results_group)
        
        # Analysis options
        options_group = QGroupBox("Analysis Options")
        options_layout = QVBoxLayout()
        
        self.auto_calculate_cb = QCheckBox("Automatically calculate when path changes")
        self.auto_calculate_cb.setChecked(True)
        options_layout.addWidget(self.auto_calculate_cb)
        
        options_group.setLayout(options_layout)
        # Keep options compact so results get the extra space
        options_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(options_group)
        
        # Give most of the vertical space to the results group
        layout.setStretch(0, 1)
        layout.setStretch(1, 0)
        widget.setLayout(layout)
        return widget
    
    def create_compare_paths_tab(self):
        """Create the Compare Paths tab for side-by-side path comparison"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Path selection
        selection_group = QGroupBox("Select Path to Compare")
        selection_layout = QHBoxLayout()
        
        self.compare_path_combo = QComboBox()
        self.load_comparison_paths()
        selection_layout.addWidget(QLabel("Compare with:"))
        selection_layout.addWidget(self.compare_path_combo, 1)
        
        self.compare_btn = QPushButton("Load Comparison")
        self.compare_btn.clicked.connect(self.load_comparison_data)
        selection_layout.addWidget(self.compare_btn)
        
        selection_group.setLayout(selection_layout)
        selection_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(selection_group)
        
        # Side-by-side comparison view
        comparison_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Current path
        current_group = QGroupBox("Current Path")
        current_layout = QVBoxLayout()
        self.current_comparison_text = QTextEdit()
        self.current_comparison_text.setReadOnly(True)
        current_layout.addWidget(self.current_comparison_text)
        current_group.setLayout(current_layout)
        comparison_splitter.addWidget(current_group)
        
        # Right panel: Comparison path
        compare_group = QGroupBox("Comparison Path")
        compare_layout = QVBoxLayout()
        self.compare_comparison_text = QTextEdit()
        self.compare_comparison_text.setReadOnly(True)
        self.compare_comparison_text.setHtml("<i>Select a path to compare and click 'Load Comparison'</i>")
        compare_layout.addWidget(self.compare_comparison_text)
        compare_group.setLayout(compare_layout)
        comparison_splitter.addWidget(compare_group)
        
        comparison_splitter.setSizes([400, 400])
        comparison_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(comparison_splitter)
        
        # Give comparison view all available vertical space
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        
        widget.setLayout(layout)
        return widget
        
    def load_spaces(self):
        """Load spaces for target space selection"""
        try:
            session = get_session()
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            
            self.space_combo.addItem("None", None)
            for space in spaces:
                self.space_combo.addItem(space.name, space.id)
            
            session.close()
            
        except Exception as e:
            print(f"Error loading spaces: {e}")
    
    def load_drawing_sets(self):
        """Load drawing sets for path association"""
        try:
            from models.drawing_sets import DrawingSet
            session = get_session()
            drawing_sets = session.query(DrawingSet).filter(
                DrawingSet.project_id == self.project_id
            ).order_by(DrawingSet.name).all()
            
            self.drawing_set_combo.addItem("None", None)
            for ds in drawing_sets:
                display_name = f"{ds.name} ({ds.phase_type})" if ds.phase_type else ds.name
                self.drawing_set_combo.addItem(display_name, ds.id)
            
            session.close()
            
        except Exception as e:
            print(f"Error loading drawing sets: {e}")
    
    def load_comparison_paths(self):
        """Load available paths for comparison"""
        try:
            if not hasattr(self, 'compare_path_combo'):
                return
            
            from models.drawing_sets import DrawingSet
            from sqlalchemy.orm import selectinload
            
            session = get_session()
            paths = (
                session.query(HVACPath)
                .options(selectinload(HVACPath.drawing_set))
                .filter(HVACPath.project_id == self.project_id)
                .order_by(HVACPath.name)
                .all()
            )
            
            self.compare_path_combo.clear()
            self.compare_path_combo.addItem("-- Select a path --", None)
            
            for path in paths:
                # Skip current path
                if self.path_id and path.id == self.path_id:
                    continue
                
                ds_info = ""
                if hasattr(path, 'drawing_set') and path.drawing_set:
                    ds_info = f" [{path.drawing_set.name}]"
                
                display_name = f"{path.name} ({path.path_type}){ds_info}"
                self.compare_path_combo.addItem(display_name, path.id)
            
            session.close()
            
        except Exception as e:
            print(f"Error loading comparison paths: {e}")
    
    def load_project_components(self):
        """Load existing components from project"""
        try:
            session = get_session()
            components = session.query(HVACComponent).filter(
                HVACComponent.project_id == self.project_id
            ).all()
            # Also load project-level Mechanical Units for use as source components
            mechanical_units = (
                session.query(MechanicalUnit)
                .filter(MechanicalUnit.project_id == self.project_id)
                .order_by(MechanicalUnit.name)
                .all()
            )
            
            self.available_list.clear()
            # Drawing-placed HVAC components
            for component in components:
                item = QListWidgetItem(f"🔧 {component.name} ({component.component_type})")
                item.setData(Qt.UserRole, component)
                self.available_list.addItem(item)
            # Mechanical Units (project-level library)
            for unit in mechanical_units:
                label_type = unit.unit_type or "unit"
                item = QListWidgetItem(f"🏭 {unit.name} ({label_type}) [Mechanical Unit]")
                # Store the MechanicalUnit directly; we'll wrap on add
                item.setData(Qt.UserRole, unit)
                self.available_list.addItem(item)
            
            session.close()
            
        except Exception as e:
            print(f"Error loading components: {e}")
    
    def suggest_mechanical_unit_for_component(self, component):
        """Suggest a mechanical unit match for the given HVAC component"""
        try:
            from src.calculations.hvac_path_calculator import HVACPathCalculator
            calculator = HVACPathCalculator(self.project_id)
            matched_unit = calculator.find_matching_mechanical_unit(component, self.project_id)
            
            if matched_unit:
                import os
                if os.environ.get('HVAC_DEBUG_EXPORT'):
                    print(f"DEBUG: Path dialog suggests unit '{matched_unit.name}' for component '{getattr(component, 'name', 'unnamed')}'")
                
                # Show suggestion dialog
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self, 
                    "Mechanical Unit Match", 
                    f"Found mechanical unit match:\n\n"
                    f"Component: {getattr(component, 'name', 'unnamed')} ({getattr(component, 'component_type', 'unknown')})\n"
                    f"Suggested Unit: {matched_unit.name} ({matched_unit.unit_type or 'unknown'})\n\n"
                    f"Add this mechanical unit as the source for this path?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Add the mechanical unit to the path as primary source
                    unit = matched_unit
                    # Create a lightweight component stub for the mechanical unit
                    mech_component = type('Component', (), {
                        'id': None,  # not persisted to hvac_components
                        'name': unit.name,
                        'component_type': unit.unit_type or 'ahu',
                        'noise_level': 80.0,  # Placeholder
                        '_mechanical_unit_id': unit.id,  # Store reference
                    })()
                    
                    # Insert at the beginning as primary source
                    self.components.insert(0, mech_component)
                    self.update_component_list()
                    self.update_summary()
                    return True
            
        except Exception as e:
            import os
            if os.environ.get('HVAC_DEBUG_EXPORT'):
                print(f"DEBUG: Mechanical unit suggestion failed: {e}")
        
        return False

    def show_validation_results(self, validation_result):
        """Show validation results to the user"""
        # Disabled: validation info is available in debug dialog and other places
        # Only show critical errors that prevent calculation
        if not validation_result or not validation_result.has_messages():
            return
        
        from PySide6.QtWidgets import QMessageBox
        
        # Only show critical errors, skip warnings and info messages
        if validation_result.errors:
            message_parts = ["ERRORS:"]
            for error in validation_result.errors:
                message_parts.append(f"• {error}")
            
            QMessageBox.critical(self, "Path Validation Issues", "\n".join(message_parts))
        
        # Warnings and info messages are suppressed to reduce popup distraction
        # They are still available in the debug dialog and validation output

    def show_debug_dialog(self):
        """Show the HVAC debug dialog"""
        try:
            from src.ui.dialogs.hvac_debug_dialog import HVACDebugDialog
            
            path_id = getattr(self, 'path_id', None) or (self.path.id if hasattr(self, 'path') and self.path else None)
            
            if not path_id:
                QMessageBox.warning(self, "Debug Not Available", 
                                  "Debug information is only available for saved paths.")
                return
            
            debug_dialog = HVACDebugDialog(self, self.project_id, path_id)
            debug_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Debug Error", f"Failed to open debug dialog:\n{str(e)}")

    def load_path_data(self):
        """Load existing path data for editing"""
        if not self.path:
            return
            
        self.name_edit.setText(self.path.name)
        
        # Set path type
        index = self.type_combo.findText(self.path.path_type or "supply")
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # Set target space
        if self.path.target_space_id:
            for i in range(self.space_combo.count()):
                if self.space_combo.itemData(i) == self.path.target_space_id:
                    self.space_combo.setCurrentIndex(i)
                    break
        
        # Set drawing set
        if hasattr(self.path, 'drawing_set_id') and self.path.drawing_set_id:
            for i in range(self.drawing_set_combo.count()):
                if self.drawing_set_combo.itemData(i) == self.path.drawing_set_id:
                    self.drawing_set_combo.setCurrentIndex(i)
                    break
        
        if self.path.description:
            self.description_text.setPlainText(self.path.description)
        
        # Load components and segments
        # Segments: prefer a fresh DB read to avoid stale or partially loaded relationships
        try:
            session = get_session()
            segs = (
                session.query(HVACSegment)
                .options(
                    selectinload(HVACSegment.from_component),
                    selectinload(HVACSegment.to_component),
                    selectinload(HVACSegment.fittings),
                )
                .filter(HVACSegment.hvac_path_id == self.path.id)
                .order_by(HVACSegment.segment_order)
                .all()
            )
            # Build an ordered, de-duplicated component list from segments
            ordered_components = []
            seen_ids = set()
            for seg in segs:
                for comp in [seg.from_component, seg.to_component]:
                    if comp is None:
                        continue
                    if comp.id not in seen_ids:
                        ordered_components.append(comp)
                        seen_ids.add(comp.id)
            self.segments = list(segs)
            
            # Debug: Check if segments have correct data when loaded
            import os
            debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
            if debug_enabled:
                print(f"\nDEBUG_UI: load_path_data loaded {len(self.segments)} segments:")
                for i, seg in enumerate(self.segments):
                    print(f"DEBUG_UI: Segment {i+1} (ID {seg.id}):")
                    print(f"DEBUG_UI:   length = {getattr(seg, 'length', 'missing')}")
                    print(f"DEBUG_UI:   duct_width = {getattr(seg, 'duct_width', 'missing')}")
                    print(f"DEBUG_UI:   duct_height = {getattr(seg, 'duct_height', 'missing')}")
                    print(f"DEBUG_UI:   duct_shape = {getattr(seg, 'duct_shape', 'missing')}")
            
            # Components used by this path, in traversal order
            self.components = ordered_components
            # Also populate "Available Components" from the project for adding to the path
            try:
                comps = session.query(HVACComponent).filter(HVACComponent.project_id == self.project_id).all()
            except Exception:
                comps = []
            finally:
                session.close()
            # Fill the available list widget
            self.available_list.clear()
            for component in comps:
                item = QListWidgetItem(f"{component.name} ({component.component_type})")
                item.setData(Qt.UserRole, component)
                self.available_list.addItem(item)
        except Exception:
            # Fallback to any segments present on the provided object
            self.segments = list(self.path.segments) if getattr(self.path, 'segments', None) else []
            # Derive components from those segments as best-effort
            ordered_components = []
            seen_ids = set()
            for seg in self.segments:
                for comp in [getattr(seg, 'from_component', None), getattr(seg, 'to_component', None)]:
                    if comp is None:
                        continue
                    cid = getattr(comp, 'id', None)
                    if cid is not None and cid not in seen_ids:
                        ordered_components.append(comp)
                        seen_ids.add(cid)
            self.components = ordered_components
        
        self.update_component_list()
        self.update_segment_list()
        self.update_summary()
    
    def update_component_list(self):
        """Update the component list display"""
        self.component_list.set_components(self.components)
        self.add_seg_btn.setEnabled(len(self.components) >= 2)
        self.update_path_diagram()
        # Auto-calc when enabled and path is minimally defined
        try:
            if getattr(self, 'auto_calculate_cb', None) and self.auto_calculate_cb.isChecked():
                if len(self.components) >= 2 and len(self.segments) >= 1:
                    self.calculate_path_noise()
        except Exception:
            pass
    
    def update_segment_list(self):
        """Update the segment list display"""
        # Use unified segment ordering from path calculator for consistency
        try:
            from src.calculations.hvac_path_calculator import HVACPathCalculator
            
            # Get preferred source ID if available
            preferred_source_id = getattr(self, 'primary_source_component_id', None)
            
            # Use the centralized ordering algorithm
            if hasattr(self, 'project_id'):
                calculator = HVACPathCalculator(self.project_id)
                ordered = calculator.order_segments_for_path(list(self.segments), preferred_source_id)
                # Sync display order into the in-memory segment objects so labels match
                for idx, seg in enumerate(ordered, start=1):
                    try:
                        setattr(seg, 'segment_order', idx)
                    except Exception:
                        pass
                self.segments = ordered
            else:
                # Fallback to stored order if no project context
                self.segments = sorted(list(self.segments), key=lambda s: getattr(s, 'segment_order', 0))
                
        except Exception as e:
            import os
            if os.environ.get('HVAC_DEBUG_EXPORT'):
                print(f"DEBUG: Segment ordering in dialog failed: {e}, using stored order")
            # Fallback to stored order
            self.segments = sorted(list(self.segments), key=lambda s: getattr(s, 'segment_order', 0))

        # Ensure segments have fresh data before displaying
        self._refresh_segments_if_needed()
        self.segment_list.set_segments(self.segments)
        self.update_path_diagram()
        # Auto-calc when enabled and path is minimally defined
        try:
            if getattr(self, 'auto_calculate_cb', None) and self.auto_calculate_cb.isChecked():
                if len(self.components) >= 2 and len(self.segments) >= 1:
                    self.calculate_path_noise()
        except Exception:
            pass
    
    def reload_segments_from_db(self):
        """Force reload of segments from the database to reflect latest edits."""
        if not hasattr(self, 'path_id') or not self.path_id:
            return
        try:
            session = get_session()
            segs = (
                session.query(HVACSegment)
                .options(
                    selectinload(HVACSegment.from_component),
                    selectinload(HVACSegment.to_component),
                    selectinload(HVACSegment.fittings),
                )
                .filter(HVACSegment.hvac_path_id == self.path_id)
                .order_by(HVACSegment.segment_order)
                .all()
            )
            self.segments = list(segs)
            session.close()
            import os
            if os.environ.get('HVAC_DEBUG_EXPORT'):
                print(f"DEBUG_UI: Reloaded {len(self.segments)} segments from DB after edit")
        except Exception as e:
            try:
                session.close()
            except Exception:
                pass
            import os
            if os.environ.get('HVAC_DEBUG_EXPORT'):
                print(f"DEBUG_UI: Failed to reload segments from DB: {e}")

    def _refresh_segments_if_needed(self):
        """Refresh segments from database if they appear to be detached or missing data"""
        if not self.segments or not hasattr(self, 'path_id') or not self.path_id:
            return
        
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        try:
            # Check if any segments are missing key data or appear detached
            needs_refresh = False
            for seg in self.segments:
                if not hasattr(seg, 'length') or seg.length is None:
                    needs_refresh = True
                    break
                if not hasattr(seg, 'duct_width') or seg.duct_width is None:
                    needs_refresh = True
                    break
            
            if needs_refresh:
                if debug_enabled:
                    print(f"DEBUG_UI: Segments appear to be missing data, refreshing from database...")
                
                # Re-load segments from database with proper eager loading
                from models.database import get_session
                from models.hvac import HVACSegment
                from sqlalchemy.orm import selectinload
                
                session = get_session()
                try:
                    fresh_segments = (
                        session.query(HVACSegment)
                        .options(
                            selectinload(HVACSegment.from_component),
                            selectinload(HVACSegment.to_component),
                            selectinload(HVACSegment.fittings),
                        )
                        .filter(HVACSegment.hvac_path_id == self.path_id)
                        .order_by(HVACSegment.segment_order)
                        .all()
                    )
                    
                    if fresh_segments:
                        self.segments = list(fresh_segments)
                        if debug_enabled:
                            print(f"DEBUG_UI: Refreshed {len(self.segments)} segments from database")
                            for i, seg in enumerate(self.segments):
                                print(f"DEBUG_UI: Refreshed Segment {i+1}: length={seg.length}, width={seg.duct_width}")
                
                finally:
                    session.close()
                    
        except Exception as e:
            if debug_enabled:
                print(f"DEBUG_UI: Could not refresh segments: {e}")
    
    def update_summary(self):
        """Update the path summary"""
        if not self.components:
            self.summary_label.setText("No components added yet.")
            return
        
        source = self._selected_source_label or (self.components[0].name if self.components else "Unknown")
        terminal = self.components[-1].name if self.components else "Unknown"
        segment_count = len(self.segments)
        
        summary = f"<b>Path Summary:</b><br>"
        summary += f"Source: {source}<br>"
        summary += f"Terminal: {terminal}<br>"
        summary += f"Components: {len(self.components)}<br>"
        summary += f"Segments: {segment_count}<br>"
        
        if self.path and self.path.calculated_noise:
            summary += f"Calculated Noise: {self.path.calculated_noise:.1f} dB(A)<br>"
            summary += f"NC Rating: NC-{self.path.calculated_nc:.0f}"
        
        self.summary_label.setText(summary)
        # Keep diagram in sync with summary updates
        self.update_path_diagram()

    def _ordered_components_from_segments(self):
        """Return components ordered by connectivity traversal if possible.
        Falls back to current self.components order when segments are missing."""
        try:
            if not self.segments:
                return list(self.components)
            # Build adjacency and in-degree to locate a starting component
            from_to = {}
            in_degree = {}
            comp_ref_by_id = {}
            for seg in self.segments:
                f = getattr(seg, 'from_component', None)
                t = getattr(seg, 'to_component', None)
                if f is None or t is None:
                    continue
                fid = getattr(f, 'id', None) or id(f)
                tid = getattr(t, 'id', None) or id(t)
                comp_ref_by_id[fid] = f
                comp_ref_by_id[tid] = t
                if fid not in from_to:
                    from_to[fid] = tid
                in_degree[tid] = in_degree.get(tid, 0) + 1
                in_degree.setdefault(fid, in_degree.get(fid, 0))
            # Choose start: in-degree 0 if available; else current first component
            start_id = None
            for cid, deg in in_degree.items():
                if deg == 0:
                    start_id = cid
                    break
            if start_id is None and self.components:
                start_id = getattr(self.components[0], 'id', None) or id(self.components[0])
            # Walk chain
            ordered_ids = []
            visited = set()
            current = start_id
            max_iters = len(from_to) + 2
            iters = 0
            while current is not None and iters < max_iters:
                iters += 1
                if current in visited:
                    break
                visited.add(current)
                ordered_ids.append(current)
                current = from_to.get(current)
            ordered = [comp_ref_by_id[cid] for cid in ordered_ids if cid in comp_ref_by_id]
            return ordered if ordered else list(self.components)
        except Exception:
            return list(self.components)

    def update_path_diagram(self):
        """Rebuild and display the ASCII path diagram on the right panel."""
        if not hasattr(self, 'diagram_text'):
            return

        # Map line index -> (kind, ref)
        # kind in { 'component', 'segment', 'source', 'receiver' }
        self._diagram_line_to_item = {}

        components = self._ordered_components_from_segments()
        if not components:
            self.diagram_text.setPlainText("No components yet.")
            return

        # Resolve receiver space name
        space_name = None
        try:
            idx = self.space_combo.currentIndex() if hasattr(self, 'space_combo') else -1
            space_name = self.space_combo.currentText() if idx >= 0 else None
            if space_name == "None":
                space_name = None
        except Exception:
            space_name = None

        lines = []
        box = lambda text: [
            "+" + "-" * (len(text) + 2) + "+",
            "| " + text + " |",
            "+" + "-" * (len(text) + 2) + "+",
        ]

        # Helper to register mapping for a box just appended
        def register_box_mapping(start_line, kind, ref):
            # Map center text line primarily, but include all three lines
            for offset in range(3):
                self._diagram_line_to_item[start_line + offset] = (kind, ref)

        # Top: source/mechanical component
        top_label = f"Source: {getattr(components[0], 'name', 'Unknown')}"
        start_idx = len(lines)
        lines.extend(box(top_label))
        register_box_mapping(start_idx, 'source', components[0])

        # Iterate segments between components
        segs = sorted(self.segments, key=lambda s: getattr(s, 'segment_order', 0)) if self.segments else []
        def seg_label(seg, idx):
            length = getattr(seg, 'length', 0) or 0
            shape = getattr(seg, 'duct_shape', '') or ''
            if shape.lower() == 'circular':
                d = getattr(seg, 'diameter', 0) or 0
                dim = f" Ø{int(d)}" if d else ""
            else:
                w = getattr(seg, 'duct_width', '') or ''
                h = getattr(seg, 'duct_height', '') or ''
                dim = f" {int(w)}x{int(h)}" if w and h else ""
            return f"segment {idx}: {length:.1f} ft{dim} {shape}".strip()

        for i, comp in enumerate(components[1:], start=1):
            # arrow + segment info block if available
            lines.append("     |")
            if i-1 < len(segs):
                seg_text = seg_label(segs[i-1], i)
                start_idx = len(lines)
                for l in box(seg_text):
                    lines.append("     " + l)
                lines.append("     v")
                # map three lines of the segment box (shifted by 1 indent)
                register_box_mapping(start_idx, 'segment', segs[i-1])
            else:
                lines.append("     v")
            comp_label = getattr(comp, 'name', 'Component')
            start_idx = len(lines)
            lines.extend(box(comp_label))
            register_box_mapping(start_idx, 'component', comp)

        # Receiver space at bottom
        if space_name:
            lines.append("     |")
            lines.append("     v")
            start_idx = len(lines)
            lines.extend(box(f"Receiver: {space_name}"))
            register_box_mapping(start_idx, 'receiver', space_name)

        self.diagram_text.setPlainText("\n".join(lines))

    def on_diagram_line_clicked(self, line_index: int) -> None:
        """Handle clicks in the diagram and switch left panel accordingly."""
        item = getattr(self, '_diagram_line_to_item', {}).get(line_index)
        if not item:
            return
        kind, ref = item
        if kind == 'component':
            # Go to Components tab and select matching component
            self.tabs.setCurrentIndex(self.components_tab_index)
            # Select in list
            for row in range(self.component_list.count()):
                it = self.component_list.item(row)
                if it.data(Qt.UserRole) is ref:
                    self.component_list.setCurrentRow(row)
                    break
            # Open edit dialog for details
            self.edit_component(ref)
        elif kind == 'segment':
            self.tabs.setCurrentIndex(self.segments_tab_index)
            for row in range(self.segment_list.count()):
                it = self.segment_list.item(row)
                if it.data(Qt.UserRole) is ref:
                    self.segment_list.setCurrentRow(row)
                    break
            self.edit_segment(ref)
        elif kind in ('receiver', 'source'):
            # For 'source' click: open component library selector to choose primary Mechanical Unit
            if kind == 'source':
                self.select_primary_source_from_library()
            else:
                self.open_receiver_dialog()

    def select_primary_source_from_library(self):
        """Open component library to select a Mechanical Unit as the path's primary source."""
        try:
            lib = ComponentLibraryDialog(self, project_id=self.project_id)
            if lib.exec() != QDialog.Accepted:
                return
            # After closing, get currently selected unit id from the list
            current = getattr(lib, 'mechanical_list', None)
            if not current or not current.currentItem():
                return
            unit_id = current.currentItem().data(Qt.UserRole)
            if not unit_id:
                return
            session = get_session()
            try:
                from models.mechanical import MechanicalUnit
                unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == unit_id).first()
            finally:
                session.close()

            if not unit:
                return

            # Extract octave-band data from the unit (prefer outlet -> inlet -> radiated)
            import json
            def parse_bands(js):
                if not js:
                    return None
                try:
                    data = json.loads(js)
                    order = ["63","125","250","500","1000","2000","4000","8000"]
                    vals = []
                    for k in order:
                        v = data.get(k)
                        vals.append(float(v) if v is not None and str(v).strip() != '' else 0.0)
                    return vals
                except Exception:
                    return None

            bands = (parse_bands(getattr(unit, 'outlet_levels_json', None)) or
                     parse_bands(getattr(unit, 'inlet_levels_json', None)) or
                     parse_bands(getattr(unit, 'radiated_levels_json', None)))

            # Compute A-weighted if we have bands; fallback to 80 dB(A)
            if bands:
                try:
                    dba = self.path_calculator.noise_calculator.hvac_engine._calculate_dba_from_spectrum(bands)
                except Exception:
                    dba = 80.0
            else:
                dba = 80.0

            self.source_octave_bands = bands
            self.source_noise_dba = dba
            self._selected_source_label = unit.name or unit.unit_type or "Mechanical Unit"

            # Persist selection on path when editing
            try:
                if self.path:
                    session = get_session()
                    db_path = session.query(HVACPath).filter(HVACPath.id == self.path.id).first()
                    if db_path:
                        db_path.primary_source_id = getattr(unit, 'id', None)
                        session.commit()
                        self.path = db_path
                    session.close()
            except Exception:
                pass

            # Refresh summary/diagram to reflect change
            self.update_summary()
        except Exception as e:
            print(f"Error selecting primary source: {e}")

    def open_receiver_dialog(self):
        """Open the Edit Space HVAC Receiver dialog for the currently selected target space."""
        try:
            space_id = self.space_combo.currentData() if hasattr(self, 'space_combo') else None
            if not space_id:
                self.tabs.setCurrentIndex(self.info_tab_index)
                return
            dlg = HVACReceiverDialog(self, space_id=int(space_id))
            dlg.exec()
        except Exception as e:
            print(f"Error opening receiver dialog: {e}")
    
    def add_component(self):
        """Add a new component to the path"""
        dialog = HVACComponentDialog(self, self.project_id, None, None)
        if dialog.exec() == QDialog.Accepted:
            # Component was created, refresh available list
            self.load_project_components()
    
    def edit_component(self, component=None):
        """Edit a component"""
        if not component:
            # Get selected component
            current_item = self.component_list.currentItem()
            if not current_item:
                return
            component = current_item.data(Qt.UserRole)
        
        dialog = HVACComponentDialog(self, self.project_id, None, component)
        # If we have recent analysis, provide context for passive components
        try:
            if hasattr(self, '_last_element_results') and self._last_element_results:
                # Prefer segment leaving this component, else entering
                seg = next((s for s in self.segments if getattr(s, 'from_component', None) is component), None)
                if seg is None:
                    seg = next((s for s in self.segments if getattr(s, 'to_component', None) is component), None)
                if seg is not None:
                    order = int(getattr(seg, 'segment_order', 0) or 0)
                    # Index 0 in results is source pseudo; segments start at index 1
                    if order >= 1 and order < len(self._last_element_results):
                        elem_res = self._last_element_results[order]
                        # Apply to the dialog if it exposes the helper
                        if hasattr(dialog, 'apply_passive_context_from_element_result'):
                            dialog.apply_passive_context_from_element_result(elem_res)
        except Exception:
            pass
        if dialog.exec() == QDialog.Accepted:
            # Component was updated, refresh lists
            self.load_project_components()
            self.update_component_list()
    
    def remove_component(self):
        """Remove a component from the path"""
        current_item = self.component_list.currentItem()
        if not current_item:
            return
        
        component = current_item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Remove Component",
            f"Remove '{component.name}' from this path?\n\n"
            "This will also remove any connected segments.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove component and connected segments
            self.components.remove(component)
            
            # Remove segments connected to this component
            self.segments = [seg for seg in self.segments 
                           if seg.from_component_id != component.id and 
                              seg.to_component_id != component.id]
            
            self.update_component_list()
            self.update_segment_list()
            self.update_summary()
    
    def add_existing_component(self, item):
        """Add an existing component to the path"""
        data_obj = item.data(Qt.UserRole)
        is_mechanical_unit = isinstance(data_obj, MechanicalUnit)
        
        # If this is a MechanicalUnit, wrap into a lightweight component-like object
        if is_mechanical_unit:
            unit = data_obj
            # Create a simple, dialog-scoped component stub
            component = type('Component', (), {
                'id': None,  # not persisted to hvac_components
                'name': unit.name,
                'component_type': unit.unit_type or 'ahu',
                # Placeholder overall noise level; can be refined from schedule later
                'noise_level': 80.0,
            })()
        else:
            component = data_obj
        
        if component in self.components:
            QMessageBox.information(self, "Component Already Added", 
                                   f"'{getattr(component, 'name', 'Component')}' is already in this path.")
            return
        
        self.components.append(component)
        
        # Auto-suggest mechanical unit for drawn components (but not for already selected mechanical units)
        if not is_mechanical_unit and len(self.components) == 1:
            # This is the first component and it's a drawn component, suggest mechanical unit
            try:
                self.suggest_mechanical_unit_for_component(component)
            except Exception as e:
                import os
                if os.environ.get('HVAC_DEBUG_EXPORT'):
                    print(f"DEBUG: Could not suggest mechanical unit: {e}")
        
        self.update_component_list()
        self.update_summary()
    
    def add_segment(self):
        """Add a new segment to the path"""
        if len(self.components) < 2:
            QMessageBox.warning(self, "Not Enough Components", 
                               "Need at least 2 components to create a segment.")
            return
        
        # Determine from and to components
        from_component = self.components[-2] if len(self.components) > 1 else self.components[0]
        to_component = self.components[-1]
        
        dialog = HVACSegmentDialog(self, self.path_id if self.path_id else None, 
                                 from_component, to_component, None)
        if dialog.exec() == QDialog.Accepted:
            # Segment was created, refresh list
            self.update_segment_list()
    
    def edit_segment(self, segment=None):
        """Edit a segment"""
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if not segment:
            # Get selected segment
            current_item = self.segment_list.currentItem()
            if not current_item:
                return
            segment_data = current_item.data(Qt.UserRole)
            
            # Check if we got a segment ID or a segment object
            if isinstance(segment_data, int):
                # We have a segment ID, load from database
                segment_id = segment_data
                if debug_enabled:
                    print(f"DEBUG_UI: Got segment ID {segment_id} from list, loading from database")
                
                try:
                    from models.database import get_hvac_session
                    from models.hvac import HVACSegment
                    from sqlalchemy.orm import selectinload
                    
                    with get_hvac_session() as session:
                        segment = (
                            session.query(HVACSegment)
                            .options(
                                selectinload(HVACSegment.from_component),
                                selectinload(HVACSegment.to_component),
                                selectinload(HVACSegment.fittings)
                            )
                            .filter_by(id=segment_id)
                            .first()
                        )
                        
                        if not segment:
                            QMessageBox.warning(self, "Error", f"Segment with ID {segment_id} not found")
                            return
                            
                        # Pre-load component relationships while session is active
                        from_component = segment.from_component
                        to_component = segment.to_component
                        _ = list(segment.fittings)  # Force load fittings
                        
                        if debug_enabled:
                            print(f"DEBUG_UI: Loaded segment {segment_id} from database:")
                            print(f"DEBUG_UI:   length = {segment.length}")
                            print(f"DEBUG_UI:   duct_width = {segment.duct_width}")
                            print(f"DEBUG_UI:   duct_height = {segment.duct_height}")
                            
                except Exception as e:
                    QMessageBox.critical(self, "Database Error", f"Failed to load segment: {e}")
                    return
            else:
                # We have a segment object (fallback for compatibility)
                segment = segment_data
        else:
            # segment was passed directly to edit_segment() method
            # Check if it's an integer ID that needs loading
            if isinstance(segment, int):
                segment_id = segment
                if debug_enabled:
                    print(f"DEBUG_UI: Got segment ID {segment_id} as parameter, loading from database")
                
                try:
                    from models.database import get_hvac_session
                    from models.hvac import HVACSegment
                    from sqlalchemy.orm import selectinload
                    
                    with get_hvac_session() as session:
                        segment = (
                            session.query(HVACSegment)
                            .options(
                                selectinload(HVACSegment.from_component),
                                selectinload(HVACSegment.to_component),
                                selectinload(HVACSegment.fittings)
                            )
                            .filter_by(id=segment_id)
                            .first()
                        )
                        
                        if not segment:
                            QMessageBox.warning(self, "Error", f"Segment with ID {segment_id} not found")
                            return
                            
                        # Pre-load component relationships while session is active
                        from_component = segment.from_component
                        to_component = segment.to_component
                        _ = list(segment.fittings)  # Force load fittings
                        
                        if debug_enabled:
                            print(f"DEBUG_UI: Loaded segment {segment_id} from database (parameter):")
                            print(f"DEBUG_UI:   length = {segment.length}")
                            print(f"DEBUG_UI:   duct_width = {segment.duct_width}")
                            print(f"DEBUG_UI:   duct_height = {segment.duct_height}")
                            
                except Exception as e:
                    QMessageBox.critical(self, "Database Error", f"Failed to load segment: {e}")
                    return
        
        if debug_enabled:
            print(f"DEBUG_UI: Final segment for dialog:")
            print(f"DEBUG_UI: segment ID = {getattr(segment, 'id', 'unknown')}")
            print(f"DEBUG_UI: segment.length = {getattr(segment, 'length', 'missing')}")
            print(f"DEBUG_UI: segment.duct_width = {getattr(segment, 'duct_width', 'missing')}")
            print(f"DEBUG_UI: segment.duct_height = {getattr(segment, 'duct_height', 'missing')}")
        
        # Get component relationships safely
        try:
            from_component = getattr(segment, 'from_component', None)
        except Exception:
            from_component = None
            
        try:
            to_component = getattr(segment, 'to_component', None)
        except Exception:
            to_component = None
        
        if debug_enabled:
            print(f"DEBUG_UI: Opening dialog with from_component={from_component}, to_component={to_component}")
            print(f"DEBUG_UI: Final segment being passed to dialog:")
            print(f"DEBUG_UI:   segment.length = {getattr(segment, 'length', 'missing')}")
            print(f"DEBUG_UI:   segment.duct_width = {getattr(segment, 'duct_width', 'missing')}")
            print(f"DEBUG_UI:   segment.duct_height = {getattr(segment, 'duct_height', 'missing')}")
        
        if os.environ.get('HVAC_DEBUG_EXPORT'):
            print("DEBUG_UI: Opening HVACSegmentDialog (pre) with segment dims:",
                  getattr(segment, 'duct_width', None), getattr(segment, 'duct_height', None))
        dialog = HVACSegmentDialog(self, self.path_id if self.path_id else None,
                                 from_component, to_component, segment)
        if os.environ.get('HVAC_DEBUG_EXPORT'):
            try:
                seg_after = getattr(dialog, 'segment', None) or segment
                print("DEBUG_UI: Returned from HVACSegmentDialog (post) dims:",
                      getattr(seg_after, 'duct_width', None), getattr(seg_after, 'duct_height', None))
            except Exception:
                pass
        if dialog.exec() == QDialog.Accepted:
            # Segment was updated, refresh list
            self.reload_segments_from_db()
            self.update_segment_list()
    
    def remove_segment(self):
        """Remove a segment from the path"""
        current_item = self.segment_list.currentItem()
        if not current_item:
            return
        
        segment = current_item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Remove Segment",
            f"Remove this segment from the path?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.segments.remove(segment)
            self.update_segment_list()
    
    def calculate_path_noise(self):
        """Calculate noise for the current path"""
        try:
            # If we have a persisted path, prefer the database-backed calculator so that
            # selections like primary source Mechanical Unit (set from the Component dialog)
            # are honored in the analysis.
            if self.path_id and not self.drawing_components:
                import os
                debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
                
                if debug_enabled:
                    print(f"\nDEBUG_UI: Using database-backed path calculation for path_id={self.path_id}")
                
                res = self.path_calculator.calculate_path_noise(int(self.path_id))
                
                if debug_enabled:
                    print(f"DEBUG_UI: Path calculator returned:")
                    print(f"DEBUG_UI:   result type: {type(res)}")
                    print(f"DEBUG_UI:   calculation_valid: {res.calculation_valid}")
                    print(f"DEBUG_UI:   source_noise: {res.source_noise}")
                    print(f"DEBUG_UI:   terminal_noise: {res.terminal_noise}")
                    print(f"DEBUG_UI:   error_message: {res.error_message}")
                    print(f"DEBUG_UI:   segment_results count: {len(res.segment_results) if res.segment_results else 0}")
                
                results = {
                    'calculation_valid': bool(res.calculation_valid),
                    'source_noise': float(res.source_noise or 0.0),
                    'terminal_noise': float(res.terminal_noise or 0.0),
                    'total_attenuation': float(res.total_attenuation or 0.0),
                    'nc_rating': int(res.nc_rating or 0),
                    'path_segments': list(res.segment_results or []),
                    'path_elements': list(res.segment_results or []),
                    'warnings': list(res.warnings or []),
                    'error': res.error_message
                }
                
                if debug_enabled:
                    print(f"DEBUG_UI: Converted to results dict:")
                    print(f"DEBUG_UI:   calculation_valid: {results['calculation_valid']}")
                
                # If database-backed calculation failed, try direct calculation as fallback
                if not results['calculation_valid']:
                    if debug_enabled:
                        print(f"DEBUG_UI: Database-backed calculation failed, trying direct calculation fallback...")
                    
                    # Build path_data and try direct calculation
                    try:
                        path_data = self.path_calculator.build_path_data_from_db(self.path_id)
                        if path_data:
                            fallback_results = self.path_calculator.noise_calculator.calculate_hvac_path_noise(path_data)
                            if fallback_results.get('calculation_valid'):
                                if debug_enabled:
                                    print(f"DEBUG_UI: Fallback calculation succeeded! Using fallback results.")
                                results = fallback_results
                    except Exception as e:
                        if debug_enabled:
                            print(f"DEBUG_UI: Fallback calculation also failed: {e}")
                
                self._last_element_results = results['path_elements']
                self.display_analysis_results(results)
                self.update_nc_summary(results)
                
                # Show validation results if available
                try:
                    path_data = self.path_calculator.build_path_data_from_db(self.path)
                    if path_data and path_data.get('validation_result'):
                        self.show_validation_results(path_data['validation_result'])
                except Exception as e:
                    import os
                    if os.environ.get('HVAC_DEBUG_EXPORT'):
                        print(f"DEBUG: Could not show validation results: {e}")
                
                return

            # In-memory preview for unsaved/new paths
            if not self.components or not self.segments:
                QMessageBox.warning(self, "Incomplete Path", 
                                   "Need components and segments to calculate noise.")
                return

            # Build path data for calculation (unchanged logic for new/unsaved paths)
            source_payload = {
                'component_type': getattr(self.components[0], 'component_type', 'unit'),
                'noise_level': (self.source_noise_dba if isinstance(self.source_noise_dba, (int, float)) else getattr(self.components[0], 'noise_level', 50.0))
            }
            if isinstance(self.source_octave_bands, list) and len(self.source_octave_bands) >= 8:
                source_payload['octave_band_levels'] = list(self.source_octave_bands)

            path_data = {
                'source_component': source_payload,
                'terminal_component': {
                    'component_type': getattr(self.components[-1], 'component_type', 'terminal'),
                    'noise_level': getattr(self.components[-1], 'noise_level', 50.0)
                },
                'segments': []
            }

            for segment in self.segments:
                segment_data = {
                    'length': segment.length,
                    'duct_width': segment.duct_width,
                    'duct_height': segment.duct_height,
                    'diameter': getattr(segment, 'diameter', 0) or 0,
                    'duct_shape': segment.duct_shape,
                    'duct_type': segment.duct_type,
                    'insulation': segment.insulation,
                    'lining_thickness': getattr(segment, 'lining_thickness', 0) or 0,
                    'fittings': []
                }

                first_fitting_type = None
                for fitting in getattr(segment, 'fittings', []) or []:
                    fitting_data = {
                        'fitting_type': fitting.fitting_type,
                        'noise_adjustment': fitting.noise_adjustment
                    }
                    segment_data['fittings'].append(fitting_data)
                    if not first_fitting_type and getattr(fitting, 'fitting_type', None):
                        first_fitting_type = fitting.fitting_type
                if first_fitting_type:
                    segment_data['fitting_type'] = first_fitting_type

                path_data['segments'].append(segment_data)

            import os
            debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
            
            if debug_enabled:
                print(f"\nDEBUG_UI: About to call calculate_hvac_path_noise")
                print(f"DEBUG_UI: path_data keys: {list(path_data.keys())}")
                if path_data.get('source_component'):
                    sc = path_data['source_component']
                    print(f"DEBUG_UI: source_component octave_bands: {sc.get('octave_band_levels')}")
            
            results = self.path_calculator.noise_calculator.calculate_hvac_path_noise(path_data)
            
            if debug_enabled:
                print(f"DEBUG_UI: Received results from calculate_hvac_path_noise")
                print(f"DEBUG_UI: results type: {type(results)}")
                print(f"DEBUG_UI: results keys: {list(results.keys()) if isinstance(results, dict) else 'Not a dict'}")
                if isinstance(results, dict):
                    print(f"DEBUG_UI: calculation_valid in results: {results.get('calculation_valid')}")
            
            self._last_element_results = results.get('path_elements', results.get('path_segments', [])) or []
            self.display_analysis_results(results)
            self.update_nc_summary(results)

        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate noise:\n{str(e)}")
    
    def display_analysis_results(self, results):
        """Display analysis results"""
        import os
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        if debug_enabled:
            print(f"\nDEBUG_UI: display_analysis_results called")
            print(f"DEBUG_UI: results keys: {list(results.keys())}")
            print(f"DEBUG_UI: calculation_valid = {results.get('calculation_valid')}")
            print(f"DEBUG_UI: source_noise = {results.get('source_noise')}")
            print(f"DEBUG_UI: terminal_noise = {results.get('terminal_noise')}")
            print(f"DEBUG_UI: nc_rating = {results.get('nc_rating')}")
            print(f"DEBUG_UI: error = {results.get('error')}")
            if results.get('path_segments'):
                print(f"DEBUG_UI: path_segments count = {len(results.get('path_segments'))}")
        
        html = "<h3>HVAC Path Noise Analysis</h3>"
        
        if results['calculation_valid']:
            html += f"<p><b>Source Noise:</b> {results['source_noise']:.1f} dB(A)<br>"
            html += f"<b>Terminal Noise:</b> {results['terminal_noise']:.1f} dB(A)<br>"
            total_att = results.get('total_attenuation') or results.get('total_attenuation_dba') or 0.0
            html += f"<b>Total Attenuation:</b> {float(total_att):.1f} dB<br>"
            html += f"<b>NC Rating:</b> NC-{results['nc_rating']:.0f}</p>"
            
            # Segment breakdown (exclude non-geometry elements and renumber sequentially)
            html += "<h4>Segment Breakdown</h4>"
            html += "<table border='1' cellpadding='5'>"
            html += "<tr><th>Segment</th><th>Length</th><th>Noise Before</th><th>Noise After</th><th>Attenuation</th></tr>"
            
            seg_rows = [s for s in (results.get('path_segments') or []) if (s.get('element_type') in {"duct", "elbow", "junction", "flex_duct"})]
            for idx, segment_result in enumerate(seg_rows, start=1):
                length = segment_result.get('length', 0.0) or 0.0
                nb = float(segment_result.get('noise_before', 0.0) or 0.0)
                na = float(segment_result.get('noise_after', 0.0) or 0.0)
                # Support both legacy 'total_attenuation' and engine 'attenuation_dba'
                att = segment_result.get('total_attenuation')
                if att is None:
                    att = segment_result.get('attenuation_dba')
                if att is None:
                    # fallback from parts
                    att = (segment_result.get('duct_loss') or 0.0) - (segment_result.get('generated_dba') or 0.0)
                html += f"<tr><td>{idx}</td>"
                html += f"<td>{float(length):.1f} ft</td>"
                html += f"<td>{nb:.1f} dB</td>"
                html += f"<td>{na:.1f} dB</td>"
                html += f"<td>{float(att or 0.0):.1f} dB</td></tr>"
            
            html += "</table>"

            # Components and fittings breakdown with NC and spectra
            html += "<h4>Components & Elements</h4>"
            html += "<table border='1' cellpadding='5'>"
            html += "<tr><th>#</th><th>Type</th><th>Noise After</th><th>NC</th><th>Octave Bands (63-8k Hz)</th></tr>"
            for element in results.get('path_elements', results.get('path_segments', [])):
                order = element.get('segment_number') or element.get('element_order') or ''
                etype = element.get('element_type') or 'segment'
                na = float(element.get('noise_after', 0.0) or 0.0)
                nc = element.get('nc_rating', '')
                bands = element.get('noise_after_spectrum') or []
                bands_str = ", ".join(f"{float(b):.1f}" for b in bands) if bands else ""
                html += f"<tr><td>{order}</td><td>{etype}</td><td>{na:.1f} dB(A)</td><td>{nc}</td><td>{bands_str}</td></tr>"
            html += "</table>"
            
            # Warnings
            if results.get('warnings'):
                html += "<h4>Warnings</h4><ul>"
                for warning in results['warnings']:
                    html += f"<li>{warning}</li>"
                html += "</ul>"
        else:
            html += f"<p style='color: red;'>Calculation failed: {results.get('error', 'Unknown error')}</p>"
        
        self.results_text.setHtml(html)

    def update_nc_summary(self, results: dict) -> None:
        """Update the compact NC list aligned with the path diagram.
        Expects each element to include 'nc_rating'. Falls back to blank.
        """
        try:
            self.nc_list.clear()
            elements = results.get('path_elements', results.get('path_segments', []))
            # Build a simple list of NC values, color-coded
            for elem in elements:
                nc = elem.get('nc_rating')
                label = f"NC {int(nc)}" if isinstance(nc, (int, float)) and nc > 0 else ""
                item = QListWidgetItem(label)
                # Background by NC performance
                if isinstance(nc, (int, float)):
                    if nc <= 30:
                        item.setBackground(Qt.green)
                    elif nc <= 40:
                        item.setBackground(Qt.yellow)
                    else:
                        item.setBackground(Qt.red)
                self.nc_list.addItem(item)
        except Exception:
            # Keep UI resilient
            pass
    
    def load_comparison_data(self):
        """Load and display comparison data for selected path"""
        try:
            compare_path_id = self.compare_path_combo.currentData()
            if not compare_path_id:
                QMessageBox.information(self, "No Path Selected", "Please select a path to compare.")
                return
            
            # Load current path analysis
            current_html = self.generate_comparison_html(self.path_id, is_current=True)
            self.current_comparison_text.setHtml(current_html)
            
            # Load comparison path analysis
            compare_html = self.generate_comparison_html(compare_path_id, is_current=False)
            self.compare_comparison_text.setHtml(compare_html)
            
        except Exception as e:
            QMessageBox.critical(self, "Comparison Error", f"Failed to load comparison:\n{str(e)}")
    
    def generate_comparison_html(self, path_id, is_current=True):
        """Generate HTML for path comparison display"""
        try:
            if not path_id:
                return "<i>Path not saved yet. Save the path to enable comparison.</i>"
            
            session = get_session()
            from sqlalchemy.orm import selectinload
            from models.drawing_sets import DrawingSet
            
            path = (
                session.query(HVACPath)
                .options(
                    selectinload(HVACPath.target_space),
                    selectinload(HVACPath.drawing_set),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                )
                .filter(HVACPath.id == path_id)
                .first()
            )
            
            if not path:
                session.close()
                return f"<i>Path ID {path_id} not found</i>"
            
            # Calculate noise for this path
            results = self.path_calculator.calculate_path_noise(int(path_id))
            
            html = "<h3>Path Information</h3>"
            html += f"<p><b>Name:</b> {path.name}<br>"
            html += f"<b>Type:</b> {path.path_type}<br>"
            
            # Drawing set info
            if hasattr(path, 'drawing_set') and path.drawing_set:
                ds_name = path.drawing_set.name
                ds_phase = path.drawing_set.phase_type or ""
                html += f"<b>Drawing Set:</b> {ds_name}"
                if ds_phase:
                    html += f" ({ds_phase})"
                html += "<br>"
            else:
                html += "<b>Drawing Set:</b> None<br>"
            
            # Target space
            if path.target_space:
                html += f"<b>Target Space:</b> {path.target_space.name}<br>"
            
            html += f"<b>Components:</b> {len(path.segments) + 1 if path.segments else 0}<br>"
            html += f"<b>Segments:</b> {len(path.segments)}</p>"
            
            # Analysis results
            if results and results.calculation_valid:
                html += "<h4>Noise Analysis</h4>"
                html += f"<p><b>Source Noise:</b> {results.source_noise:.1f} dB(A)<br>"
                html += f"<b>Terminal Noise:</b> {results.terminal_noise:.1f} dB(A)<br>"
                total_att = results.total_attenuation or 0.0
                html += f"<b>Total Attenuation:</b> {float(total_att):.1f} dB<br>"
                html += f"<b>NC Rating:</b> NC-{results.nc_rating:.0f}</p>"
                
                # Segment breakdown
                html += "<h4>Segment Breakdown</h4>"
                html += "<table border='1' cellpadding='3' cellspacing='0' style='border-collapse: collapse;'>"
                html += "<tr style='background-color: #333;'><th>Seg</th><th>Length (ft)</th><th>Before (dB)</th><th>After (dB)</th><th>Atten (dB)</th></tr>"
                
                seg_rows = [s for s in (results.segment_results or []) if (s.get('element_type') in {"duct", "elbow", "junction", "flex_duct"})]
                for idx, seg_result in enumerate(seg_rows, start=1):
                    length = seg_result.get('length', 0.0) or 0.0
                    nb = float(seg_result.get('noise_before', 0.0) or 0.0)
                    na = float(seg_result.get('noise_after', 0.0) or 0.0)
                    att = seg_result.get('total_attenuation') or seg_result.get('attenuation_dba') or 0.0
                    
                    html += f"<tr><td>{idx}</td>"
                    html += f"<td>{float(length):.1f}</td>"
                    html += f"<td>{nb:.1f}</td>"
                    html += f"<td>{na:.1f}</td>"
                    html += f"<td>{float(att or 0.0):.1f}</td></tr>"
                
                html += "</table>"
                
            else:
                html += "<p><i>No analysis results available. Click 'Calculate Noise' to analyze this path.</i></p>"
            
            session.close()
            return html
            
        except Exception as e:
            return f"<p style='color: red;'>Error generating comparison: {str(e)}</p>"
    
    def save_path(self):
        """Save the HVAC path"""
        # Validate inputs
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a path name.")
            return
        
        if len(self.components) < 2:
            QMessageBox.warning(self, "Validation Error", "Need at least 2 components for a path.")
            return
        
        if len(self.segments) == 0:
            QMessageBox.warning(self, "Validation Error", "Need at least 1 segment for a path.")
            return
        
        try:
            # If we have drawing data AND we are creating a new path, use the calculator
            if (not self.is_editing) and self.drawing_components and self.drawing_segments:
                # Add drawing ID to components
                for comp in self.drawing_components:
                    comp['drawing_id'] = self.drawing_id
                
                drawing_data = {
                    'components': self.drawing_components,
                    'segments': self.drawing_segments
                }
                
                # Create HVAC path using the calculator
                created_path_result = self.path_calculator.create_hvac_path_from_drawing(
                    self.project_id, drawing_data
                )
                
                if created_path_result.success:
                    created_path = created_path_result.data
                    # Update path using a fresh session-bound instance
                    session = get_session()
                    try:
                        db_path = session.query(HVACPath).filter(HVACPath.id == created_path.id).first()
                        if db_path is None:
                            session.close()
                            QMessageBox.warning(self, "Creation Warning", "Path was created but could not be reloaded for update.")
                            self.path = created_path
                            self.path_saved.emit(created_path)
                            self.accept()
                            return
                        db_path.name = name
                        db_path.path_type = self.type_combo.currentText()
                        db_path.description = self.description_text.toPlainText()
                        # Update target space
                        space_id = self.space_combo.currentData()
                        db_path.target_space_id = space_id
                        # Update drawing set
                        drawing_set_id = self.drawing_set_combo.currentData()
                        db_path.drawing_set_id = drawing_set_id
                        session.commit()
                        # Assign updated object back for emit
                        self.path = db_path
                        self.path_saved.emit(db_path)
                        self.accept()
                    finally:
                        session.close()
                else:
                    error_msg = getattr(created_path_result, 'error_message', 'Unknown error occurred')
                    QMessageBox.warning(self, "Creation Failed", f"Failed to create HVAC path from drawing elements.\n\nError: {error_msg}")
                    return
            else:
                # Standard database path creation / update using unified session management
                from models.database import get_hvac_session
                
                if self.is_editing:
                    # Update existing path using session context manager
                    with get_hvac_session() as session:
                        db_path = session.query(HVACPath).filter(HVACPath.id == self.path.id).first()
                        if db_path is None:
                            QMessageBox.warning(self, "Update Failed", "Selected path could not be found.")
                            return
                        db_path.name = name
                        db_path.path_type = self.type_combo.currentText()
                        db_path.description = self.description_text.toPlainText()
                        # Update target space
                        space_id = self.space_combo.currentData()
                        db_path.target_space_id = space_id
                        # Update drawing set
                        drawing_set_id = self.drawing_set_combo.currentData()
                        db_path.drawing_set_id = drawing_set_id
                        
                        # Persist current segment ordering and keep any edited geometry
                        try:
                            import os
                            debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
                            # Build desired order from the in-memory list
                            order_map = {}
                            for idx, seg in enumerate(self.segments, start=1):
                                sid = getattr(seg, 'id', None)
                                if sid is not None:
                                    order_map[sid] = idx
                            if debug_enabled:
                                print(f"DEBUG_UI: Updating segment_order for {len(order_map)} segments on save")
                            # Load current DB segments and apply new order
                            db_segs = (
                                session.query(HVACSegment)
                                .filter(HVACSegment.hvac_path_id == db_path.id)
                                .all()
                            )
                            for s in db_segs:
                                if s.id in order_map:
                                    if debug_enabled and getattr(s, 'segment_order', None) != order_map[s.id]:
                                        print(f"DEBUG_UI: Segment {s.id} order {getattr(s, 'segment_order', None)} -> {order_map[s.id]}")
                                    s.segment_order = order_map[s.id]
                        except Exception as seg_e:
                            import os
                            if os.environ.get('HVAC_DEBUG_EXPORT'):
                                print(f"DEBUG_UI: Failed to update segment ordering on save: {seg_e}")
                        
                        path = db_path
                        # Commit handled by context manager
                else:
                    # Create new path using session context manager
                    with get_hvac_session() as session:
                        space_id = self.space_combo.currentData()
                        drawing_set_id = self.drawing_set_combo.currentData()
                        
                        path = HVACPath(
                            project_id=self.project_id,
                            name=name,
                            path_type=self.type_combo.currentText(),
                            description=self.description_text.toPlainText(),
                            target_space_id=space_id,
                            drawing_set_id=drawing_set_id
                        )
                        session.add(path)
                        session.flush()  # Get ID
                        
                        # Create segments with unified ordering before saving
                        # Ensure segments are ordered consistently before persisting to database
                        from src.calculations.hvac_path_calculator import HVACPathCalculator
                        
                        ordered_segments = self.segments
                        try:
                            calculator = HVACPathCalculator(self.project_id)
                            preferred_source_id = getattr(path, 'primary_source_id', None)
                            ordered_segments = calculator.order_segments_for_path(
                                list(self.segments), 
                                preferred_source_id
                            )
                            
                            # Debug logging for save ordering
                            import os
                            if os.environ.get('HVAC_DEBUG_EXPORT'):
                                print(f"DEBUG: Saving {len(ordered_segments)} segments in ordered sequence")
                                for i, seg in enumerate(ordered_segments):
                                    seg_id = getattr(seg, 'id', f'new_{i}')
                                    from_id = getattr(seg, 'from_component_id', None) or (getattr(getattr(seg, 'from_component', None), 'id', None))
                                    to_id = getattr(seg, 'to_component_id', None) or (getattr(getattr(seg, 'to_component', None), 'id', None))
                                    print(f"DEBUG: Save position {i+1}: Segment {seg_id}: {from_id} -> {to_id}")
                                    
                        except Exception as e:
                            import os
                            if os.environ.get('HVAC_DEBUG_EXPORT'):
                                print(f"DEBUG: Failed to order segments for save: {e}, using current order")
                        
                        # Create segments (persist new records based on ordered dialog segment stubs)
                        for i, segment in enumerate(ordered_segments):
                            seg = HVACSegment(
                                hvac_path_id=path.id,
                                from_component_id=getattr(segment, 'from_component_id', None) or (segment.from_component.id if hasattr(segment, 'from_component') and segment.from_component else None),
                                to_component_id=getattr(segment, 'to_component_id', None) or (segment.to_component.id if hasattr(segment, 'to_component') and segment.to_component else None),
                                length=getattr(segment, 'length', None) or getattr(segment, 'length_real', 0) or 0,
                                segment_order=i + 1,  # Now reflects connectivity order
                                duct_width=getattr(segment, 'duct_width', None) or 12,
                                duct_height=getattr(segment, 'duct_height', None) or 8,
                                duct_shape=getattr(segment, 'duct_shape', None) or 'rectangular',
                                duct_type=getattr(segment, 'duct_type', None) or 'sheet_metal',
                            )
                            session.add(seg)
                        # Commit handled by context manager
                
                self.path = path
                self.path_saved.emit(path)
                self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save path:\n{str(e)}")
    
    def delete_path(self):
        """Delete the HVAC path"""
        if not self.is_editing or not self.path:
            return
            
        # Safely resolve path name without triggering lazy-load on a detached instance
        try:
            name_str = str(getattr(self.path, 'name'))
        except Exception:
            name_str = None
        if not name_str:
            try:
                session = get_session()
                try:
                    dbp = session.query(HVACPath).filter(HVACPath.id == (self.path_id or getattr(self.path, 'id', None))).first()
                    name_str = getattr(dbp, 'name', 'this path') if dbp else 'this path'
                finally:
                    session.close()
            except Exception:
                name_str = 'this path'

        reply = QMessageBox.question(
            self, "Delete Path",
            f"Are you sure you want to delete '{name_str}'?\n\n"
            "This will also remove all segments and fittings associated with this path.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                # Delete using a session-bound instance to avoid DetachedInstanceError
                db_path = session.query(HVACPath).filter(HVACPath.id == (self.path_id or getattr(self.path, 'id', None))).first()
                if not db_path:
                    session.close()
                    QMessageBox.warning(self, "Delete Path", "Selected path could not be found in the database.")
                    return
                session.delete(db_path)
                session.commit()
                session.close()
                
                self.accept()
                
            except Exception as e:
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Error", f"Failed to delete path:\n{str(e)}")


# Convenience function to show dialog
def show_hvac_path_dialog(parent=None, project_id=None, path=None):
    """Show HVAC path dialog"""
    dialog = HVACPathDialog(parent, project_id, path)
    return dialog.exec() 