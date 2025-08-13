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
            item.setData(Qt.UserRole, segment)
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
        
        # Components and segments for this path
        self.components = []
        self.segments = []
        
        # Drawing data (for creating from drawing elements)
        self.drawing_components = []
        self.drawing_segments = []
        self.drawing_id = None
        
        # Calculator
        self.path_calculator = HVACPathCalculator()
        
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
        header_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(header_label)
        
        # Main content: tabs on the left + ASCII path diagram on the right
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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

        # Ensure tabs expand with window
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_splitter.addWidget(self.tabs)

        # Right side: ASCII diagram panel
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
        """Create the right-side panel showing an ASCII path diagram."""
        panel = QWidget()
        v = QVBoxLayout()
        title = QLabel("Path Diagram")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        v.addWidget(title)

        self.diagram_text = PathDiagramText()
        self.diagram_text.setPlaceholderText("ASCII diagram will appear here when components/segments are defined.")
        self.diagram_text.line_clicked.connect(self.on_diagram_line_clicked)
        self.diagram_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v.addWidget(self.diagram_text)

        panel.setLayout(v)
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
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Analysis options
        options_group = QGroupBox("Analysis Options")
        options_layout = QVBoxLayout()
        
        self.auto_calculate_cb = QCheckBox("Automatically calculate when path changes")
        self.auto_calculate_cb.setChecked(True)
        options_layout.addWidget(self.auto_calculate_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        layout.addStretch()
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
    
    def update_segment_list(self):
        """Update the segment list display"""
        self.segment_list.set_segments(self.segments)
        self.update_path_diagram()
    
    def update_summary(self):
        """Update the path summary"""
        if not self.components:
            self.summary_label.setText("No components added yet.")
            return
        
        source = self.components[0].name if self.components else "Unknown"
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
        """Return components ordered by segment traversal if possible.
        Falls back to current self.components order when segments are missing."""
        try:
            if not self.segments:
                return list(self.components)
            # Sort segments by segment_order and stitch components
            ordered = []
            seen_ids = set()
            for seg in sorted(self.segments, key=lambda s: getattr(s, 'segment_order', 0)):
                for comp in [getattr(seg, 'from_component', None), getattr(seg, 'to_component', None)]:
                    if comp is None:
                        continue
                    cid = getattr(comp, 'id', None) or id(comp)
                    if cid not in seen_ids:
                        ordered.append(comp)
                        seen_ids.add(cid)
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
        def seg_label(seg):
            length = getattr(seg, 'length', 0) or 0
            shape = getattr(seg, 'duct_shape', '') or ''
            w = getattr(seg, 'duct_width', '') or ''
            h = getattr(seg, 'duct_height', '') or ''
            dim = f" {int(w)}x{int(h)}" if w and h else ""
            return f"segment {getattr(seg, 'segment_order', '?')}: {length:.1f} ft{dim} {shape}".strip()

        for i, comp in enumerate(components[1:], start=1):
            # arrow + segment info block if available
            lines.append("     |")
            if i-1 < len(segs):
                seg_text = seg_label(segs[i-1])
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
                if not unit:
                    session.close()
                    return
                # Persist selection on path
                if self.path:
                    db_path = session.query(HVACPath).filter(HVACPath.id == self.path.id).first()
                    if db_path:
                        db_path.primary_source_id = unit.id
                        session.commit()
                        self.path = db_path
                # Refresh summary/diagram to reflect change
                self.update_summary()
            finally:
                session.close()
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
        
        # If this is a MechanicalUnit, wrap into a lightweight component-like object
        if isinstance(data_obj, MechanicalUnit):
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
        
        dialog = HVACSegmentDialog(self, self.path.id if self.path else None, 
                                 from_component, to_component, None)
        if dialog.exec() == QDialog.Accepted:
            # Segment was created, refresh list
            self.update_segment_list()
    
    def edit_segment(self, segment=None):
        """Edit a segment"""
        if not segment:
            # Get selected segment
            current_item = self.segment_list.currentItem()
            if not current_item:
                return
            segment = current_item.data(Qt.UserRole)
        
        dialog = HVACSegmentDialog(self, self.path.id if self.path else None,
                                 segment.from_component, segment.to_component, segment)
        if dialog.exec() == QDialog.Accepted:
            # Segment was updated, refresh list
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
        if not self.components or not self.segments:
            QMessageBox.warning(self, "Incomplete Path", 
                               "Need components and segments to calculate noise.")
            return
        
        try:
            # Build path data for calculation
            path_data = {
                'source_component': {
                    'component_type': getattr(self.components[0], 'component_type', 'unit'),
                    'noise_level': getattr(self.components[0], 'noise_level', 50.0)
                },
                'terminal_component': {
                    'component_type': getattr(self.components[-1], 'component_type', 'terminal'),
                    'noise_level': getattr(self.components[-1], 'noise_level', 50.0)
                },
                'segments': []
            }
            
            # Add segments
            for segment in self.segments:
                segment_data = {
                    'length': segment.length,
                    'duct_width': segment.duct_width,
                    'duct_height': segment.duct_height,
                    'duct_shape': segment.duct_shape,
                    'duct_type': segment.duct_type,
                    'insulation': segment.insulation,
                    'fittings': []
                }
                
                # Add fittings
                for fitting in getattr(segment, 'fittings', []) or []:
                    fitting_data = {
                        'fitting_type': fitting.fitting_type,
                        'noise_adjustment': fitting.noise_adjustment
                    }
                    segment_data['fittings'].append(fitting_data)
                
                path_data['segments'].append(segment_data)
            
            # Calculate noise
            results = self.path_calculator.noise_calculator.calculate_hvac_path_noise(path_data)
            
            # Display results
            self.display_analysis_results(results)
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate noise:\n{str(e)}")
    
    def display_analysis_results(self, results):
        """Display analysis results"""
        html = "<h3>HVAC Path Noise Analysis</h3>"
        
        if results['calculation_valid']:
            html += f"<p><b>Source Noise:</b> {results['source_noise']:.1f} dB(A)<br>"
            html += f"<b>Terminal Noise:</b> {results['terminal_noise']:.1f} dB(A)<br>"
            total_att = results.get('total_attenuation') or results.get('total_attenuation_dba') or 0.0
            html += f"<b>Total Attenuation:</b> {float(total_att):.1f} dB<br>"
            html += f"<b>NC Rating:</b> NC-{results['nc_rating']:.0f}</p>"
            
            # Segment breakdown
            html += "<h4>Segment Breakdown</h4>"
            html += "<table border='1' cellpadding='5'>"
            html += "<tr><th>Segment</th><th>Length</th><th>Noise Before</th><th>Noise After</th><th>Attenuation</th></tr>"
            
            for segment_result in results['path_segments']:
                seg_num = segment_result.get('segment_number') or segment_result.get('element_order') or ''
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
                html += f"<tr><td>{seg_num}</td>"
                html += f"<td>{float(length):.1f} ft</td>"
                html += f"<td>{nb:.1f} dB</td>"
                html += f"<td>{na:.1f} dB</td>"
                html += f"<td>{float(att or 0.0):.1f} dB</td></tr>"
            
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
            # If we have drawing data, use the path calculator
            if self.drawing_components and self.drawing_segments:
                # Add drawing ID to components
                for comp in self.drawing_components:
                    comp['drawing_id'] = self.drawing_id
                
                drawing_data = {
                    'components': self.drawing_components,
                    'segments': self.drawing_segments
                }
                
                # Create HVAC path using the calculator
                created_path = self.path_calculator.create_hvac_path_from_drawing(
                    self.project_id, drawing_data
                )
                
                if created_path:
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
                        session.commit()
                        # Assign updated object back for emit
                        self.path = db_path
                        self.path_saved.emit(db_path)
                        self.accept()
                    finally:
                        session.close()
                else:
                    QMessageBox.warning(self, "Creation Failed", "Failed to create HVAC path from drawing elements.")
                    return
            else:
                # Standard database path creation / update
                session = get_session()
                
                if self.is_editing:
                    # Update existing path (reload session-bound)
                    db_path = session.query(HVACPath).filter(HVACPath.id == self.path.id).first()
                    if db_path is None:
                        session.close()
                        QMessageBox.warning(self, "Update Failed", "Selected path could not be found.")
                        return
                    db_path.name = name
                    db_path.path_type = self.type_combo.currentText()
                    db_path.description = self.description_text.toPlainText()
                    # Update target space
                    space_id = self.space_combo.currentData()
                    db_path.target_space_id = space_id
                    session.commit()
                    path = db_path
                else:
                    # Create new path
                    space_id = self.space_combo.currentData()
                    
                    path = HVACPath(
                        project_id=self.project_id,
                        name=name,
                        path_type=self.type_combo.currentText(),
                        description=self.description_text.toPlainText(),
                        target_space_id=space_id
                    )
                    session.add(path)
                    session.flush()  # Get ID
                    
                    # Create segments (persist new records based on dialog segment stubs)
                    for i, segment in enumerate(self.segments):
                        seg = HVACSegment(
                            hvac_path_id=path.id,
                            from_component_id=getattr(segment, 'from_component_id', None) or (segment.from_component.id if hasattr(segment, 'from_component') and segment.from_component else None),
                            to_component_id=getattr(segment, 'to_component_id', None) or (segment.to_component.id if hasattr(segment, 'to_component') and segment.to_component else None),
                            length=getattr(segment, 'length', None) or getattr(segment, 'length_real', 0) or 0,
                            segment_order=i + 1,
                            duct_width=getattr(segment, 'duct_width', None) or 12,
                            duct_height=getattr(segment, 'duct_height', None) or 8,
                            duct_shape=getattr(segment, 'duct_shape', None) or 'rectangular',
                            duct_type=getattr(segment, 'duct_type', None) or 'sheet_metal',
                        )
                        session.add(seg)
                    session.commit()
                
                session.close()
                
                self.path = path
                self.path_saved.emit(path)
                self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save path:\n{str(e)}")
    
    def delete_path(self):
        """Delete the HVAC path"""
        if not self.is_editing or not self.path:
            return
            
        reply = QMessageBox.question(
            self, "Delete Path",
            f"Are you sure you want to delete '{self.path.name}'?\n\n"
            "This will also remove all segments and fittings associated with this path.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                session.delete(self.path)
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