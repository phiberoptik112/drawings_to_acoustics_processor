"""
Drawing Interface - PDF viewer with drawing overlay tools
"""

import os
from typing import Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QToolBar, QButtonGroup, QPushButton, 
                             QLabel, QComboBox, QLineEdit, QGroupBox, 
                             QListWidget, QListWidgetItem, QMessageBox, QFileDialog, QSplitter,
                             QFrame, QSpinBox, QDialog, QCheckBox)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QFont, QAction

from models import get_session, Drawing, Project, Space, RoomBoundary, DrawingElementManager
from drawing import PDFViewer, DrawingOverlay, ScaleManager, ToolType
from ui.dialogs.scale_dialog import ScaleDialog
from ui.dialogs.room_properties import RoomPropertiesDialog
from ui.dialogs.hvac_path_dialog import HVACPathDialog
from ui.dialogs.hvac_component_dialog import HVACComponentDialog
from ui.dialogs.hvac_segment_dialog import HVACSegmentDialog
from data.components import STANDARD_COMPONENTS
from data.excel_exporter import ExcelExporter, ExportOptions, EXCEL_EXPORT_AVAILABLE
from calculations import RT60Calculator, NoiseCalculator, HVACPathCalculator


class DrawingInterface(QMainWindow):
    """Drawing interface for PDF viewing and drawing tools"""
    
    # Signals
    finished = Signal()
    paths_updated = Signal()
    
    def __init__(self, drawing_id, project_id):
        super().__init__()
        self.drawing_id = drawing_id
        self.project_id = project_id
        self.drawing = None
        self.project = None
        
        # Components
        self.pdf_viewer = None
        self.drawing_overlay = None
        self.scale_manager = ScaleManager()
        self.rt60_calculator = RT60Calculator()
        self.noise_calculator = NoiseCalculator()
        self.hvac_path_calculator = HVACPathCalculator()
        self.element_manager = DrawingElementManager(get_session)
        
        # Selected element for context operations
        self.selected_rectangle = None
        self.selected_hvac_element = None
        
        # Current page tracking
        self.current_page_number = 1
        
        # Path visibility tracking
        self.visible_paths = set()  # Set of path IDs that are currently visible
        
        # Initialize base scale ratio for zoom adjustments
        self._base_scale_ratio = 1.0
        
        self.load_drawing_data()
        self.init_ui()
        self.setup_connections()
        
        if self.drawing and self.drawing.file_path:
            self.load_pdf()
            
        # Load saved paths
        self.load_saved_paths()
            
    def load_drawing_data(self):
        """Load drawing and project data from database"""
        try:
            session = get_session()
            self.drawing = session.query(Drawing).filter(Drawing.id == self.drawing_id).first()
            self.project = session.query(Project).filter(Project.id == self.project_id).first()
            session.close()
            
            if not self.drawing:
                raise Exception(f"Drawing with ID {self.drawing_id} not found")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load drawing:\n{str(e)}")
            self.close()
            
    def init_ui(self):
        """Initialize the user interface"""
        title = f"Drawing: {self.drawing.name}" if self.drawing else "Drawing Interface"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 1400, 900)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - tools and properties
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Center panel - PDF viewer with overlay
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 1100])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Create status bar
        self.status_bar = self.statusBar()
        self.update_status_bar()
        
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('Open PDF', self.open_pdf)
        file_menu.addAction('Save Drawing', self.save_drawing)
        file_menu.addSeparator()
        file_menu.addAction('Export Elements', self.export_elements)
        if EXCEL_EXPORT_AVAILABLE:
            file_menu.addAction('Export to Excel', self.export_to_excel)
        file_menu.addSeparator()
        file_menu.addAction('Close', self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        edit_menu.addAction('Clear Unsaved', self.clear_unsaved_elements)
        edit_menu.addAction('Clear Measurements', self.clear_measurements)
        
        # View menu
        view_menu = menubar.addMenu('View')
        view_menu.addAction('Fit Width', self.fit_width)
        view_menu.addAction('Fit Page', self.fit_page)
        view_menu.addAction('Zoom 100%', lambda: self.pdf_viewer.set_zoom(1.0) if self.pdf_viewer else None)
        view_menu.addSeparator()
        view_menu.addAction('Toggle Grid', self.toggle_grid)
        view_menu.addAction('Toggle Measurements', self.toggle_measurements)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        tools_menu.addAction('Set Scale', self.set_scale)
        tools_menu.addAction('Calibrate Scale', self.calibrate_scale)
        tools_menu.addSeparator()
        tools_menu.addAction('Create HVAC Path', self.create_hvac_path_from_drawing)
        tools_menu.addAction('Analyze HVAC Path', self.analyze_hvac_path)
        tools_menu.addAction('Calculate All Paths', self.calculate_all_hvac_paths)
        tools_menu.addSeparator()
        tools_menu.addAction('NC Compliance Analysis', self.analyze_nc_compliance)
        
    def create_toolbar(self):
        """Create the main toolbar"""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        
        # Tool selection buttons
        self.tool_group = QButtonGroup()
        
        # Rectangle tool
        rect_action = QAction('🔲 Rectangle', self)
        rect_action.setCheckable(True)
        rect_action.setChecked(True)
        rect_action.triggered.connect(lambda: self.set_drawing_tool(ToolType.RECTANGLE))
        toolbar.addAction(rect_action)
        self.tool_group.addButton(toolbar.widgetForAction(rect_action))
        
        # Component tool
        comp_action = QAction('🔧 Component', self)
        comp_action.setCheckable(True)
        comp_action.triggered.connect(lambda: self.set_drawing_tool(ToolType.COMPONENT))
        toolbar.addAction(comp_action)
        self.tool_group.addButton(toolbar.widgetForAction(comp_action))
        
        # Segment tool
        seg_action = QAction('━ Segment', self)
        seg_action.setCheckable(True)
        seg_action.triggered.connect(lambda: self.set_drawing_tool(ToolType.SEGMENT))
        toolbar.addAction(seg_action)
        self.tool_group.addButton(toolbar.widgetForAction(seg_action))

        # Edit/Select tool
        edit_action = QAction('✏️ Edit', self)
        edit_action.setCheckable(True)
        edit_action.triggered.connect(lambda: self.set_drawing_tool(ToolType.SELECT))
        toolbar.addAction(edit_action)
        self.tool_group.addButton(toolbar.widgetForAction(edit_action))
        
        # Measure tool
        measure_action = QAction('📏 Measure', self)
        measure_action.setCheckable(True)
        measure_action.triggered.connect(lambda: self.set_drawing_tool(ToolType.MEASURE))
        toolbar.addAction(measure_action)
        self.tool_group.addButton(toolbar.widgetForAction(measure_action))
        
        toolbar.addSeparator()
        
        # Quick actions
        toolbar.addAction('💾 Save', self.save_drawing)
        # Clear only unsaved/transient elements so saved path visuals persist
        toolbar.addAction('🗑️ Clear', self.clear_unsaved_elements)
        
    def create_left_panel(self):
        """Create the left panel with tools and properties"""
        panel = QWidget()
        panel.setMaximumWidth(300)
        layout = QVBoxLayout()
        
        # Drawing mode group
        mode_group = QGroupBox("Drawing Mode")
        mode_layout = QVBoxLayout()
        
        self.mode_label = QLabel("Current Tool: Rectangle")
        self.mode_label.setFont(QFont("Arial", 10, QFont.Bold))
        mode_layout.addWidget(self.mode_label)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Component selection (for component tool)
        self.component_group = QGroupBox("Component Type")
        comp_layout = QVBoxLayout()
        
        self.component_combo = QComboBox()
        for key, comp in STANDARD_COMPONENTS.items():
            self.component_combo.addItem(f"{comp['name']} ({key})", key)
        self.component_combo.currentIndexChanged.connect(self.component_index_changed)
        comp_layout.addWidget(self.component_combo)
        
        self.component_group.setLayout(comp_layout)
        layout.addWidget(self.component_group)
        
        # Scale information
        scale_group = QGroupBox("Scale Information")
        scale_layout = QVBoxLayout()
        
        self.scale_label = QLabel("Scale: Not set")
        scale_layout.addWidget(self.scale_label)
        
        scale_btn_layout = QHBoxLayout()
        self.set_scale_btn = QPushButton("Set Scale")
        self.set_scale_btn.clicked.connect(self.set_scale)
        
        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.clicked.connect(self.calibrate_scale)
        
        scale_btn_layout.addWidget(self.set_scale_btn)
        scale_btn_layout.addWidget(self.calibrate_btn)
        scale_layout.addLayout(scale_btn_layout)
        
        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)
        
        # Elements summary
        summary_group = QGroupBox("Elements Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_label = QLabel("No elements drawn")
        summary_layout.addWidget(self.summary_label)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Element list
        elements_group = QGroupBox("Element List")
        elements_layout = QVBoxLayout()
        
        self.elements_list = QListWidget()
        self.elements_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.elements_list.customContextMenuRequested.connect(self.show_element_context_menu)
        elements_layout.addWidget(self.elements_list)
        
        # Element actions
        element_actions_layout = QHBoxLayout()
        
        self.create_room_btn = QPushButton("🏠 New Space")
        self.create_room_btn.clicked.connect(self.create_room_from_selected)
        self.create_room_btn.setEnabled(False)
        self.create_room_btn.setToolTip("Convert selected rectangle to a space with acoustic properties")
        
        self.create_path_btn = QPushButton("🔀 New Path")
        self.create_path_btn.clicked.connect(self.create_path_from_selected)
        self.create_path_btn.setEnabled(False)
        self.create_path_btn.setToolTip("Create HVAC path from selected components and segments")
        
        self.delete_element_btn = QPushButton("Delete")
        self.delete_element_btn.clicked.connect(self.delete_selected_element)
        self.delete_element_btn.setEnabled(False)
        
        element_actions_layout.addWidget(self.create_room_btn)
        element_actions_layout.addWidget(self.create_path_btn)
        element_actions_layout.addWidget(self.delete_element_btn)
        
        elements_layout.addLayout(element_actions_layout)
        elements_group.setLayout(elements_layout)
        layout.addWidget(elements_group)
        
        # Saved Paths section
        paths_group = QGroupBox("Saved Paths")
        paths_layout = QVBoxLayout()
        
        # Paths summary
        self.paths_summary_label = QLabel("No paths saved")
        paths_layout.addWidget(self.paths_summary_label)
        
        # Paths list with checkboxes
        self.paths_list = QListWidget()
        self.paths_list.setMaximumHeight(120)  # Limit height to save space
        self.paths_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.paths_list.customContextMenuRequested.connect(self.show_path_context_menu)
        paths_layout.addWidget(self.paths_list)
        
        # Path mode toggle
        self.path_only_mode = QCheckBox("Show only visible paths")
        self.path_only_mode.setToolTip("Hide all drawing elements except those belonging to visible paths")
        self.path_only_mode.stateChanged.connect(self.toggle_path_only_mode)
        paths_layout.addWidget(self.path_only_mode)
        
        # Path actions
        path_actions_layout = QHBoxLayout()
        
        self.refresh_paths_btn = QPushButton("🔄 Refresh")
        self.refresh_paths_btn.clicked.connect(self.load_saved_paths)
        self.refresh_paths_btn.setToolTip("Refresh saved paths list")
        
        self.show_all_paths_btn = QPushButton("👁️ Show All")
        self.show_all_paths_btn.clicked.connect(self.show_all_paths)
        self.show_all_paths_btn.setToolTip("Show all paths on drawing")
        
        self.hide_all_paths_btn = QPushButton("👁️‍🗨️ Hide All")
        self.hide_all_paths_btn.clicked.connect(self.hide_all_paths)
        self.hide_all_paths_btn.setToolTip("Hide all paths from drawing")
        
        path_actions_layout.addWidget(self.refresh_paths_btn)
        path_actions_layout.addWidget(self.show_all_paths_btn)
        path_actions_layout.addWidget(self.hide_all_paths_btn)
        
        # Advanced path actions
        path_actions_layout2 = QHBoxLayout()
        
        self.register_all_btn = QPushButton("🔗 Register All to Path 1")
        self.register_all_btn.clicked.connect(lambda: self.register_all_elements_to_path(1))
        self.register_all_btn.setToolTip("Register all drawing elements to Path 1 for complete hide/show control")
        
        self.force_show_btn = QPushButton("👁️ Force Show Path 1")
        self.force_show_btn.clicked.connect(lambda: self.force_show_path(1))
        self.force_show_btn.setToolTip("Force show Path 1 (debug button)")
        
        # Debug checkbox test
        self.debug_checkbox = QCheckBox("Debug Test Toggle")
        self.debug_checkbox.stateChanged.connect(lambda state: print(f"DEBUG: Debug checkbox state: {state} (checked={state == Qt.Checked})"))
        
        path_actions_layout2.addWidget(self.register_all_btn)
        path_actions_layout2.addWidget(self.force_show_btn)
        path_actions_layout2.addWidget(self.debug_checkbox)
        
        paths_layout.addLayout(path_actions_layout)
        paths_layout.addLayout(path_actions_layout2)
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        
        return panel
        
    def create_center_panel(self):
        """Create the center panel with PDF viewer and overlay"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # PDF viewer
        self.pdf_viewer = PDFViewer()
        
        # Drawing overlay
        self.drawing_overlay = DrawingOverlay()
        self.drawing_overlay.set_scale_manager(self.scale_manager)
        
        # Stack overlay on top of PDF viewer
        # Create a container widget
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout()
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        
        viewer_layout.addWidget(self.pdf_viewer)
        viewer_container.setLayout(viewer_layout)
        
        # Position overlay on top
        self.drawing_overlay.setParent(self.pdf_viewer.pdf_label)
        
        layout.addWidget(viewer_container)
        panel.setLayout(layout)
        
        return panel
        
    def setup_connections(self):
        """Setup signal connections"""
        if self.pdf_viewer:
            self.pdf_viewer.coordinates_clicked.connect(self.pdf_coordinates_clicked)
            self.pdf_viewer.screen_coordinates_clicked.connect(self.screen_coordinates_clicked)
            self.pdf_viewer.scale_changed.connect(self.pdf_zoom_changed)
            self.pdf_viewer.page_changed.connect(self.page_changed)
            
        if self.drawing_overlay:
            self.drawing_overlay.element_created.connect(self.element_created)
            self.drawing_overlay.measurement_taken.connect(self.measurement_taken)
            # Open edit dialogs on double-clicks in overlay
            self.drawing_overlay.element_double_clicked.connect(self.overlay_element_double_clicked)
            
        self.scale_manager.scale_changed.connect(self.scale_updated)
        
        # Element list selection
        self.elements_list.itemSelectionChanged.connect(self.element_selected)
        # Saved paths list double-click to edit path
        self.paths_list.itemDoubleClicked.connect(self.open_path_editor_from_item)
        
    def load_pdf(self):
        """Load the PDF file"""
        if self.drawing and self.drawing.file_path:
            if os.path.exists(self.drawing.file_path):
                success = self.pdf_viewer.load_pdf(self.drawing.file_path)
                if success:
                    self.update_overlay_size()
                    self.load_scale_from_drawing()
                    self.load_saved_elements()
            else:
                QMessageBox.warning(self, "Warning", f"PDF file not found:\n{self.drawing.file_path}")
                
    def update_overlay_size(self):
        """Update overlay size to match PDF display"""
        if self.pdf_viewer and self.pdf_viewer.pixmap and self.drawing_overlay:
            # Get PDF display size
            pdf_size = self.pdf_viewer.pixmap.size()
            self.drawing_overlay.resize(pdf_size)

            # Align overlay origin with the pixmap content origin inside the centered QLabel
            try:
                label = self.pdf_viewer.pdf_label
                pixmap = self.pdf_viewer.pixmap
                if label and pixmap:
                    offset_x = max((label.width() - pixmap.width()) // 2, 0)
                    offset_y = max((label.height() - pixmap.height()) // 2, 0)
                    self.drawing_overlay.move(offset_x, offset_y)
                else:
                    self.drawing_overlay.move(0, 0)
            except Exception:
                # Fallback to (0,0) if anything unexpected
                self.drawing_overlay.move(0, 0)
            
            # Update scale manager with page dimensions
            pdf_width, pdf_height = self.pdf_viewer.get_page_dimensions()
            self.scale_manager.set_page_dimensions(pdf_width, pdf_height)
            
    def load_scale_from_drawing(self):
        """Load scale information from drawing record"""
        if self.drawing and self.drawing.scale_string:
            self.scale_manager.set_scale_from_string(self.drawing.scale_string)
            # Store the base scale ratio (at 100% zoom)
            self._base_scale_ratio = self.scale_manager.scale_ratio
            # Apply current zoom factor
            current_zoom = self.pdf_viewer.zoom_factor if self.pdf_viewer else 1.0
            self.scale_manager.scale_ratio = self._base_scale_ratio * current_zoom
            
    def set_drawing_tool(self, tool_type):
        """Set the active drawing tool"""
        if self.drawing_overlay:
            self.drawing_overlay.set_tool(tool_type)
            self.mode_label.setText(f"Current Tool: {tool_type.value.title()}")
            
            # Show/hide component selection
            self.component_group.setVisible(tool_type == ToolType.COMPONENT)
            
    def component_index_changed(self, index):
        """Handle component combo box index change"""
        if index >= 0:
            component_key = self.component_combo.itemData(index)
            self.component_type_changed(component_key)
    
    def component_type_changed(self, component_key):
        """Handle component type change"""
        if self.drawing_overlay and component_key:
            self.drawing_overlay.set_component_type(component_key)
            
    def pdf_coordinates_clicked(self, x, y):
        """Handle PDF coordinates clicked"""
        # This receives PDF coordinates (normalized to 100% zoom)
        # Use for display purposes only
        pass
        
    def screen_coordinates_clicked(self, x, y):
        """Handle screen pixel coordinates clicked"""
        # Update status bar with coordinates using screen pixels for scale calculation
        real_x = self.scale_manager.pixels_to_real(x)
        real_y = self.scale_manager.pixels_to_real(y)
        
        coord_text = f"Clicked: ({x:.0f}, {y:.0f}) px = ({real_x:.1f}, {real_y:.1f}) {self.scale_manager.units}"
        self.status_bar.showMessage(coord_text, 3000)
        
    def pdf_zoom_changed(self, zoom_factor):
        """Handle PDF zoom change"""
        self.update_overlay_size()
        
        # Update scale manager to account for zoom factor
        # The scale ratio needs to be adjusted because pixel distances on screen change with zoom
        # but the real-world scale relationship remains constant
        if hasattr(self, '_base_scale_ratio'):
            # Adjust the scale ratio: more zoom = more pixels per real unit
            self.scale_manager.scale_ratio = self._base_scale_ratio * zoom_factor
            # Emit the scale change to update the UI
            self.scale_manager.scale_changed.emit(self.scale_manager.scale_ratio, self.scale_manager.scale_string)

        # Re-scale overlay geometry so items remain anchored while background zooms
        if self.drawing_overlay:
            try:
                self.drawing_overlay.set_zoom_factor(zoom_factor)
            except Exception as e:
                print(f"DEBUG: overlay zoom update failed: {e}")
        
    def page_changed(self, page_number):
        """Handle PDF page change - save current page elements and load new page elements"""
        # Save current page elements before changing
        if self.drawing_overlay and hasattr(self, 'current_page_number'):
            try:
                overlay_data = self.drawing_overlay.get_elements_data()
                if any(overlay_data.values()):  # If there are any elements to save
                    self.element_manager.save_elements(
                        self.drawing.id, self.project_id, overlay_data, self.current_page_number
                    )
            except Exception as e:
                print(f"Warning: Could not save elements for page {self.current_page_number}: {e}")
        
        # Update current page number (page_number is 0-indexed, we store 1-indexed)
        self.current_page_number = page_number + 1
        
        # Clear overlay elements for new page
        if self.drawing_overlay:
            self.drawing_overlay.clear_all_elements()
            self.elements_list.clear()
            self.update_elements_display()
            
        # Update overlay size for new page
        self.update_overlay_size()
        
        # Load elements for the new page
        self.load_saved_elements()
        
        # Update status bar
        self.status_bar.showMessage(f"Page {self.current_page_number} - Loaded page-specific elements", 3000)
        
    def element_created(self, element_data):
        """Handle new drawing element creation"""
        self.update_elements_display()
        self.update_status_bar()
        
        # Add to elements list with data storage
        element_type = element_data.get('type', 'unknown')
        item = None
        
        if element_type == 'rectangle':
            area_text = element_data.get('area_formatted', '')
            item = QListWidgetItem(f"🔲 Rectangle - {area_text}")
            item.setData(Qt.UserRole, element_data)  # Store element data
        elif element_type == 'component':
            comp_type = element_data.get('component_type', 'unknown')
            item = QListWidgetItem(f"🔧 {comp_type.upper()}")
            item.setData(Qt.UserRole, element_data)
        elif element_type == 'segment':
            length_text = element_data.get('length_formatted', '')
            item = QListWidgetItem(f"━ Segment - {length_text}")
            item.setData(Qt.UserRole, element_data)
        elif element_type == 'measurement':
            length_text = element_data.get('length_formatted', '')
            item = QListWidgetItem(f"📏 Measurement - {length_text}")
            item.setData(Qt.UserRole, element_data)
            
        if item:
            self.elements_list.addItem(item)
            
    def measurement_taken(self, length_real, length_formatted):
        """Handle measurement taken"""
        QMessageBox.information(self, "Measurement", f"Distance measured: {length_formatted}")
        
    def scale_updated(self, scale_ratio, scale_string):
        """Handle scale update"""
        self.scale_label.setText(f"Scale: {scale_string}")
        
        # Store the base scale ratio (normalize to 100% zoom)
        current_zoom = self.pdf_viewer.zoom_factor if self.pdf_viewer else 1.0
        self._base_scale_ratio = scale_ratio / current_zoom
        
        self.update_elements_display()
        
    def update_elements_display(self):
        """Update the elements summary display"""
        if self.drawing_overlay:
            summary = self.drawing_overlay.get_elements_summary()
            
            text = f"Rectangles: {summary['rectangles']}\n"
            text += f"Components: {summary['components']}\n" 
            text += f"Segments: {summary['segments']}\n"
            text += f"Measurements: {summary['measurements']}\n\n"
            
            if summary['total_area'] > 0:
                area_formatted = self.scale_manager.format_area(summary['total_area'])
                text += f"Total Area: {area_formatted}\n"
                
            if summary['total_duct_length'] > 0:
                length_formatted = self.scale_manager.format_distance(summary['total_duct_length'])
                text += f"Total Duct: {length_formatted}"
                
            self.summary_label.setText(text)
            
    def update_status_bar(self):
        """Update the status bar"""
        if self.drawing:
            status_text = f"Drawing: {self.drawing.name}"
            if self.drawing_overlay:
                summary = self.drawing_overlay.get_elements_summary()
                status_text += f" | Elements: {summary['rectangles']}R {summary['components']}C {summary['segments']}S"
            self.status_bar.showMessage(status_text)
            
    # Menu and toolbar actions
    def open_pdf(self):
        """Open a PDF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            success = self.pdf_viewer.load_pdf(file_path)
            if success:
                # Update drawing record
                self.drawing.file_path = file_path
                self.save_drawing_to_db()
                self.update_overlay_size()
                
    def save_drawing(self):
        """Save current drawing state"""
        self.save_drawing_to_db()
        QMessageBox.information(self, "Saved", "Drawing saved successfully.")
        
    def save_drawing_to_db(self):
        """Save drawing data and elements to database"""
        if not self.drawing:
            return
            
        try:
            session = get_session()
            
            # Update drawing record
            if self.scale_manager.scale_string:
                self.drawing.scale_string = self.scale_manager.scale_string
                self.drawing.scale_ratio = self.scale_manager.scale_ratio
                
            if self.pdf_viewer and self.pdf_viewer.page_width:
                self.drawing.width_pixels = self.pdf_viewer.page_width
                self.drawing.height_pixels = self.pdf_viewer.page_height
                
            session.merge(self.drawing)
            session.commit()
            session.close()
            
            # Save drawing elements
            if self.drawing_overlay:
                overlay_data = self.drawing_overlay.get_elements_data()
                elements_saved = self.element_manager.save_elements(
                    self.drawing.id, self.project_id, overlay_data, self.current_page_number
                )
                
                if elements_saved > 0:
                    self.status_bar.showMessage(f"Saved {elements_saved} drawing elements", 2000)
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not save drawing:\n{str(e)}")
            
    def load_saved_elements(self):
        """Load saved drawing elements from database for current page"""
        if not self.drawing or not self.drawing_overlay:
            return
            
        try:
            overlay_data = self.element_manager.load_elements(self.drawing.id, self.current_page_number)
            
            if any(overlay_data.values()):  # If there are any elements
                self.drawing_overlay.load_elements_data(overlay_data)
                
                # Rebuild elements list
                self.rebuild_elements_list(overlay_data)
                
                elements_count = sum(len(elements) for elements in overlay_data.values())
                self.status_bar.showMessage(f"Loaded {elements_count} saved elements", 2000)
            
            # Also load space rectangles from RoomBoundary records
            self.load_space_rectangles()
                
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load saved elements:\n{str(e)}")
            
    def load_space_rectangles(self):
        """Load space rectangles from RoomBoundary records in the database for current page"""
        if not self.drawing:
            return
            
        try:
            session = get_session()
            
            # Get all room boundaries for this drawing and page
            from models.space import RoomBoundary, Space
            boundaries = session.query(RoomBoundary).filter(
                RoomBoundary.drawing_id == self.drawing.id,
                RoomBoundary.page_number == self.current_page_number
            ).all()
            
            space_rectangles = []
            for boundary in boundaries:
                # Get the associated space name
                space_name = boundary.space.name if boundary.space else f"Space {boundary.space_id}"
                
                # Create rectangle data compatible with drawing overlay
                rect_data = {
                    'type': 'rectangle',
                    'bounds': {
                        'x': int(boundary.x_position),
                        'y': int(boundary.y_position), 
                        'width': int(boundary.width),
                        'height': int(boundary.height)
                    },
                    'x': int(boundary.x_position),
                    'y': int(boundary.y_position),
                    'width': int(boundary.width),
                    'height': int(boundary.height),
                    'area_real': boundary.calculated_area or 0,
                    'area_formatted': f"{boundary.calculated_area:.0f} sf" if boundary.calculated_area else "0 sf",
                    'space_id': boundary.space_id,
                    'space_name': space_name,
                    'boundary_id': boundary.id,
                    'converted_to_space': True,  # Mark as already converted
                    'width_real': self.scale_manager.pixels_to_real(boundary.width) if self.scale_manager else boundary.width / 50,
                    'height_real': self.scale_manager.pixels_to_real(boundary.height) if self.scale_manager else boundary.height / 50
                }
                
                space_rectangles.append(rect_data)
                
            session.close()
            
            if space_rectangles:
                # Add space rectangles to the overlay
                self.drawing_overlay.rectangles.extend(space_rectangles)
                
                # Add to elements list
                for rect_data in space_rectangles:
                    area_formatted = rect_data.get('area_formatted', '0 sf')
                    space_name = rect_data.get('space_name', 'Unknown Space')
                    item = QListWidgetItem(f"🏠 {space_name} - {area_formatted}")
                    item.setData(Qt.UserRole, rect_data)
                    self.elements_list.addItem(item)
                
                # Trigger repaint
                self.drawing_overlay.update()
                
                self.status_bar.showMessage(f"Loaded {len(space_rectangles)} space rectangles", 2000)
                
        except Exception as e:
            print(f"Error loading space rectangles: {e}")
            # Don't show error to user as this is optional functionality
            
    def rebuild_elements_list(self, overlay_data):
        """Rebuild elements list from loaded data"""
        self.elements_list.clear()
        
        # Add rectangles
        for rect_data in overlay_data.get('rectangles', []):
            area_formatted = rect_data.get('area_formatted', f"{rect_data.get('area_real', 0):.0f} sf")
            item = QListWidgetItem(f"🔲 Rectangle - {area_formatted}")
            item.setData(Qt.UserRole, rect_data)
            self.elements_list.addItem(item)
            
        # Add components
        for comp_data in overlay_data.get('components', []):
            comp_type = comp_data.get('component_type', 'unknown')
            item = QListWidgetItem(f"🔧 {comp_type.upper()}")
            item.setData(Qt.UserRole, comp_data)
            self.elements_list.addItem(item)
            
        # Add segments
        for seg_data in overlay_data.get('segments', []):
            length_formatted = seg_data.get('length_formatted', f"{seg_data.get('length_real', 0):.1f} ft")
            item = QListWidgetItem(f"━ Segment - {length_formatted}")
            item.setData(Qt.UserRole, seg_data)
            self.elements_list.addItem(item)
            
        # Add measurements (if persistent)
        for meas_data in overlay_data.get('measurements', []):
            if meas_data.get('persistent', True):
                length_formatted = meas_data.get('length_formatted', f"{meas_data.get('length_real', 0):.1f} ft")
                item = QListWidgetItem(f"📏 Measurement - {length_formatted}")
                item.setData(Qt.UserRole, meas_data)
                self.elements_list.addItem(item)
                
        # Update displays
        self.update_elements_display()
            
    def export_elements(self):
        """Export drawing elements"""
        if self.drawing_overlay:
            data = self.drawing_overlay.get_elements_data()
            QMessageBox.information(self, "Export", f"Export functionality will save:\n{len(data['rectangles'])} rectangles\n{len(data['components'])} components\n{len(data['segments'])} segments")
            
    def clear_all_elements(self):
        """Clear all drawing elements"""
        if self.drawing_overlay:
            self.drawing_overlay.clear_all_elements()
            self.elements_list.clear()
            self.update_elements_display()

    def clear_unsaved_elements(self):
        """Clear only elements not registered to saved HVAC paths.

        Preserves the visuals for saved paths by delegating to the overlay's
        `clear_unsaved_elements` method. Also refreshes the elements list.
        """
        if self.drawing_overlay:
            self.drawing_overlay.clear_unsaved_elements()
            self.elements_list.clear()
            # Rebuild list from remaining overlay data
            overlay_data = self.drawing_overlay.get_elements_data()
            self.rebuild_elements_list(overlay_data)
            
    def clear_measurements(self):
        """Clear measurement lines"""
        if self.drawing_overlay:
            self.drawing_overlay.clear_measurements()
            self.update_elements_display()
            
    def fit_width(self):
        """Fit PDF to width"""
        if self.pdf_viewer:
            self.pdf_viewer.fit_width()
            
    def fit_page(self):
        """Fit PDF to page"""
        if self.pdf_viewer:
            self.pdf_viewer.fit_page()
            
    def toggle_grid(self):
        """Toggle grid display"""
        if self.drawing_overlay:
            self.drawing_overlay.toggle_grid()
            
    def toggle_measurements(self):
        """Toggle measurement display"""
        if self.drawing_overlay:
            self.drawing_overlay.toggle_measurements()
            
    def set_scale(self):
        """Open scale setting dialog"""
        dialog = ScaleDialog(self, self.scale_manager)
        dialog.exec()
        
    def calibrate_scale(self):
        """Start scale calibration with measurement tool"""
        # Check if we have any measurements to calibrate from
        if self.drawing_overlay and self.drawing_overlay.measurements:
            # Get the most recent measurement
            last_measurement = self.drawing_overlay.measurements[-1]
            pixel_distance = last_measurement.get('length_pixels', 0)
            
            # Ask user for the real-world distance
            from PySide6.QtWidgets import QInputDialog
            real_distance, ok = QInputDialog.getDouble(
                self, "Scale Calibration", 
                f"The measured distance is {pixel_distance:.0f} pixels.\n"
                f"Enter the real-world distance in feet:",
                25.0, 0.1, 1000.0, 1)
            
            if ok and real_distance > 0:
                # Calibrate the scale
                success = self.scale_manager.calibrate_from_known_measurement(
                    pixel_distance, real_distance, self.scale_manager.scale_string)
                
                if success:
                    QMessageBox.information(self, "Calibration Complete", 
                        f"Scale calibrated successfully!\n"
                        f"{pixel_distance:.0f} pixels = {real_distance:.1f} feet\n"
                        f"Scale ratio: {self.scale_manager.scale_ratio:.2f} pixels/foot")
                    
                    # Update the display
                    self.update_elements_display()
                    self.save_drawing_to_db()
                else:
                    QMessageBox.warning(self, "Error", "Failed to calibrate scale.")
        else:
            # No measurements yet - start measurement tool
            self.set_drawing_tool(ToolType.MEASURE)
            QMessageBox.information(self, "Scale Calibration", 
                                   "First, use the measurement tool to measure a known distance.\n"
                                   "Then click 'Calibrate' again to set the real-world scale.")
        
    def element_selected(self):
        """Handle element list selection change"""
        current_item = self.elements_list.currentItem()
        
        if current_item:
            element_data = current_item.data(Qt.UserRole)
            element_type = element_data.get('type') if element_data else None
            
            # Enable appropriate buttons
            self.create_room_btn.setEnabled(element_type == 'rectangle')
            self.create_path_btn.setEnabled(element_type in ['component', 'segment'])
            self.delete_element_btn.setEnabled(True)
            
            if element_type == 'rectangle':
                self.selected_rectangle = element_data
            elif element_type in ['component', 'segment']:
                self.selected_hvac_element = element_data
        else:
            self.create_room_btn.setEnabled(False)
            self.create_path_btn.setEnabled(False)
            self.delete_element_btn.setEnabled(False)
            self.selected_rectangle = None
            self.selected_hvac_element = None
            
    def show_element_context_menu(self, position):
        """Show context menu for element list"""
        item = self.elements_list.itemAt(position)
        if not item:
            return
            
        element_data = item.data(Qt.UserRole)
        element_type = element_data.get('type') if element_data else None
        
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        if element_type == 'rectangle':
            create_room_action = menu.addAction("🏠 Create Room/Space")
            create_room_action.triggered.connect(lambda: self.create_room_from_rectangle(element_data))
        elif element_type in ['component', 'segment']:
            create_path_action = menu.addAction("🔀 Create HVAC Path")
            create_path_action.triggered.connect(lambda: self.create_path_from_element(element_data))
            
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Delete Element")
        delete_action.triggered.connect(lambda: self.delete_element(item))
        
        menu.exec_(self.elements_list.mapToGlobal(position))
        
    def create_room_from_selected(self):
        """Create room from selected rectangle"""
        if self.selected_rectangle:
            self.create_room_from_rectangle(self.selected_rectangle)
    
    def create_path_from_selected(self):
        """Create HVAC path from selected component or segment"""
        if self.selected_hvac_element:
            self.create_path_from_element(self.selected_hvac_element)
            
    def create_path_from_element(self, element_data):
        """Create HVAC path from a selected component or segment"""
        if not element_data:
            QMessageBox.warning(self, "Error", "No HVAC element data available.")
            return
            
        element_type = element_data.get('type')
        
        if element_type == 'component':
            self.create_path_from_component(element_data)
        elif element_type == 'segment':
            self.create_path_from_segment(element_data)
        else:
            QMessageBox.warning(self, "Error", "Selected element is not a valid HVAC component or segment.")
            
    def create_path_from_component(self, component_data):
        """Create HVAC path starting from a selected component"""
        try:
            # Get all components and segments from drawing
            overlay_data = self.drawing_overlay.get_elements_data() if self.drawing_overlay else {}
            components = overlay_data.get('components', [])
            segments = overlay_data.get('segments', [])
            
            if len(components) < 2:
                QMessageBox.information(self, "Create HVAC Path", 
                                       "Need at least 2 HVAC components to create a path.\n"
                                       "Use the Component tool to place more HVAC equipment.")
                return
            
            # Find connected components through segments
            connected_components = self.find_connected_components(component_data, components, segments)
            
            if len(connected_components) < 2:
                QMessageBox.information(self, "Create HVAC Path",
                                       "Selected component is not connected to other components.\n"
                                       "Use the Segment tool to connect HVAC components.")
                return
            
            # Create path from connected components
            self.create_hvac_path_from_components(connected_components, segments)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create HVAC path from component:\n{str(e)}")
    
    def create_path_from_segment(self, segment_data):
        """Create HVAC path from a selected segment"""
        try:
            # Get all components and segments from drawing
            overlay_data = self.drawing_overlay.get_elements_data() if self.drawing_overlay else {}
            components = overlay_data.get('components', [])
            segments = overlay_data.get('segments', [])
            
            if len(components) < 2:
                QMessageBox.information(self, "Create HVAC Path", 
                                       "Need at least 2 HVAC components to create a path.\n"
                                       "Use the Component tool to place HVAC equipment.")
                return
            
            # Find the path that includes this segment
            path_components = self.find_path_from_segment(segment_data, components, segments)
            
            if len(path_components) < 2:
                QMessageBox.information(self, "Create HVAC Path",
                                       "Selected segment is not part of a complete path.\n"
                                       "Ensure components are properly connected.")
                return
            
            # Create path from found components
            self.create_hvac_path_from_components(path_components, segments)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create HVAC path from segment:\n{str(e)}")
    
    def find_connected_components(self, start_component, all_components, all_segments):
        """Find all components connected to the start component through segments"""
        print(f"DEBUG: Finding connected components for {start_component.get('component_type', 'unknown')}")
        print(f"DEBUG: Total segments: {len(all_segments)}")
        
        connected = [start_component]
        visited_ids = set()
        to_visit = [start_component]
        
        # Get unique identifier for component (use position as fallback)
        def get_component_id(comp):
            return comp.get('id', f"{comp.get('x', 0)}_{comp.get('y', 0)}")
        
        while to_visit:
            current = to_visit.pop(0)
            current_id = get_component_id(current)
            
            if current_id in visited_ids:
                continue
                
            visited_ids.add(current_id)
            
            # Find segments connected to this component
            for i, segment in enumerate(all_segments):
                print(f"DEBUG: Checking segment {i}: from_component={segment.get('from_component') is not None}, to_component={segment.get('to_component') is not None}")
                
                # Check if segment connects to current component
                if (segment.get('from_component') == current or 
                    segment.get('to_component') == current):
                    
                    print(f"DEBUG: Found connected segment {i}")
                    
                    # Find the other component in this segment
                    other_component = None
                    if segment.get('from_component') == current:
                        other_component = segment.get('to_component')
                    else:
                        other_component = segment.get('from_component')
                    
                    if other_component:
                        other_id = get_component_id(other_component)
                        if other_id not in visited_ids:
                            print(f"DEBUG: Adding connected component: {other_component.get('component_type', 'unknown')}")
                            connected.append(other_component)
                            to_visit.append(other_component)
        
        print(f"DEBUG: Found {len(connected)} connected components")
        return connected
    
    def find_path_from_segment(self, start_segment, all_components, all_segments):
        """Find all components in the path that includes the start segment"""
        # Start with components connected by this segment
        path_components = []
        
        from_comp = start_segment.get('from_component')
        to_comp = start_segment.get('to_component')
        
        if from_comp:
            path_components.append(from_comp)
        if to_comp:
            path_components.append(to_comp)
        
        # Get unique identifier for component (use position as fallback)
        def get_component_id(comp):
            return comp.get('id', f"{comp.get('x', 0)}_{comp.get('y', 0)}")
        
        # Get unique identifier for segment (use start/end points as fallback)
        def get_segment_id(seg):
            from_comp = seg.get('from_component', {})
            to_comp = seg.get('to_component', {})
            from_id = get_component_id(from_comp) if from_comp else 'none'
            to_id = get_component_id(to_comp) if to_comp else 'none'
            return f"{from_id}_{to_id}"
        
        # Expand the path by finding connected segments
        visited_segment_ids = {get_segment_id(start_segment)}
        to_visit_segments = [start_segment]
        
        while to_visit_segments:
            current_segment = to_visit_segments.pop(0)
            
            # Find segments that connect to components in this segment
            for segment in all_segments:
                segment_id = get_segment_id(segment)
                if segment_id in visited_segment_ids:
                    continue
                    
                # Check if this segment connects to any component in our path
                segment_from = segment.get('from_component')
                segment_to = segment.get('to_component')
                
                # Check if any component in this segment is in our path
                path_component_ids = {get_component_id(comp) for comp in path_components}
                segment_from_id = get_component_id(segment_from) if segment_from else None
                segment_to_id = get_component_id(segment_to) if segment_to else None
                
                if (segment_from_id in path_component_ids or segment_to_id in path_component_ids):
                    visited_segment_ids.add(segment_id)
                    to_visit_segments.append(segment)
                    
                    # Add new components to path
                    if segment_from and segment_from_id not in path_component_ids:
                        path_components.append(segment_from)
                    if segment_to and segment_to_id not in path_component_ids:
                        path_components.append(segment_to)
        
        return path_components
    
    def create_hvac_path_from_components(self, components, segments):
        """Create HVAC path from a list of connected components"""
        try:
            # Add drawing ID to components
            for comp in components:
                comp['drawing_id'] = self.drawing.id
            
            # Filter segments that connect to any components in our path
            # Be permissive: include a segment if EITHER endpoint is in the path's component set.
            # The calculator later validates and creates DB segments only when at least one
            # endpoint is resolvable, so over-including here is safe and avoids false negatives
            # due to identity/equality nuances in dicts.
            path_segments = []
            print(f"DEBUG: Preparing path from {len(components)} components and {len(segments)} segments (pre-filter)")
            for i, segment in enumerate(segments):
                from_comp = segment.get('from_component')
                to_comp = segment.get('to_component')
                include = False
                if from_comp and from_comp in components:
                    include = True
                if to_comp and to_comp in components:
                    include = True
                if include:
                    path_segments.append(segment)
                else:
                    # Extra permissive fallback: include if either endpoint matches by position/type
                    def comp_matches(c):
                        if not c:
                            return False
                        for cmp in components:
                            if (cmp.get('x') == c.get('x') and cmp.get('y') == c.get('y') and 
                                cmp.get('component_type') == c.get('component_type')):
                                return True
                        return False
                    if comp_matches(from_comp) or comp_matches(to_comp):
                        path_segments.append(segment)
                        include = True
                print(f"DEBUG: Segment {i} filter include={include}")
            print(f"DEBUG: path_segments after filter: {len(path_segments)}")
            
            drawing_data = {
                'components': components,
                'segments': path_segments
            }
            
            # Create HVAC path in database
            hvac_path = self.hvac_path_calculator.create_hvac_path_from_drawing(
                self.project_id, drawing_data
            )
            
            if hvac_path:
                # Register path elements in drawing overlay for show/hide functionality
                if self.drawing_overlay:
                    self.drawing_overlay.register_path_elements(hvac_path.id, components, path_segments)
                
                # Show success message with path details
                path_info = f"Successfully created HVAC path: {hvac_path.name}\n\n"
                path_info += f"Components: {len(components)}\n"
                path_info += f"Segments: {len(path_segments)}\n"
                
                if hvac_path.calculated_noise:
                    path_info += f"Terminal Noise: {hvac_path.calculated_noise:.1f} dB(A)\n"
                    path_info += f"NC Rating: NC-{hvac_path.calculated_nc:.0f}"
                else:
                    path_info += "Noise calculation pending"
                
                QMessageBox.information(self, "HVAC Path Created", path_info)
                
                # Update status bar
                self.status_bar.showMessage(f"Created HVAC path '{hvac_path.name}' with {len(components)} components", 5000)
                
                # Refresh paths list to show new path
                self.load_saved_paths()
                # Notify listeners (e.g., project dashboard HVAC tab)
                try:
                    self.paths_updated.emit()
                except Exception:
                    pass
            else:
                QMessageBox.warning(self, "Creation Failed", "Failed to create HVAC path from drawing elements.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create HVAC path:\n{str(e)}")
            
    def create_room_from_rectangle(self, rectangle_data):
        """Create a room/space from rectangle data"""
        if not rectangle_data:
            QMessageBox.warning(self, "Error", "No rectangle data available.")
            return
            
        try:
            # Open room properties dialog
            dialog = RoomPropertiesDialog(self, rectangle_data, self.scale_manager)
            dialog.space_created.connect(self.handle_space_created)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create room properties dialog:\n{str(e)}")
            
    def handle_space_created(self, space_data):
        """Handle space creation from room properties dialog"""
        session = None
        try:
            session = get_session()
            
            # Create space record with drawing association
            space = Space(
                project_id=self.project_id,
                drawing_id=self.drawing.id if self.drawing else None,  # Set drawing_id directly
                name=space_data['name'],
                description=space_data['description'],
                floor_area=space_data['floor_area'],
                ceiling_height=space_data['ceiling_height'],
                volume=space_data.get('volume', 0),
                wall_area=space_data.get('wall_area', 0),
                target_rt60=space_data['target_rt60'],
                ceiling_material=space_data['ceiling_material'],
                wall_material=space_data['wall_material'],
                floor_material=space_data['floor_material']
            )
            
            session.add(space)
            session.flush()
            
            # Set up multiple materials if available
            from models.space import SurfaceType
            if hasattr(space_data, 'ceiling_materials'):
                space.set_surface_materials(SurfaceType.CEILING, space_data['ceiling_materials'], session)
            if hasattr(space_data, 'wall_materials'):
                space.set_surface_materials(SurfaceType.WALL, space_data['wall_materials'], session)
            if hasattr(space_data, 'floor_materials'):
                space.set_surface_materials(SurfaceType.FLOOR, space_data['floor_materials'], session)
            
            # Calculate RT60
            rt60_results = self.rt60_calculator.calculate_space_rt60(space_data)
            calculated_rt60 = None
            if rt60_results and 'rt60' in rt60_results:
                space.calculated_rt60 = rt60_results['rt60']
                calculated_rt60 = rt60_results['rt60']
                
            # Create room boundary record
            rectangle_data = space_data.get('rectangle_data', {})
            if rectangle_data and self.drawing:
                boundary = RoomBoundary(
                    space_id=space.id,
                    drawing_id=self.drawing.id,
                    page_number=self.current_page_number,
                    x_position=rectangle_data.get('x', 0),
                    y_position=rectangle_data.get('y', 0),
                    width=rectangle_data.get('width', 0),
                    height=rectangle_data.get('height', 0),
                    calculated_area=rectangle_data.get('area_real', 0)
                )
                
                session.add(boundary)
                
            session.commit()
            session.close()
            
            # Update UI with enhanced feedback
            rt60_display = f"{calculated_rt60:.2f} seconds" if calculated_rt60 else "Not calculated"
            
            # Show detailed success message with next steps
            next_steps = (
                "\n💡 Next Steps:\n"
                "• Edit space properties to set materials\n"
                "• Add HVAC components and connect with ducts\n"
                "• View results in the main project dashboard"
            )
            
            QMessageBox.information(
                self, 
                "✅ Space Created Successfully!", 
                f"Space '{space_data['name']}' has been created and linked to this drawing.\n\n"
                f"📏 Dimensions:\n"
                f"  • Area: {space_data['floor_area']:.1f} sf\n"
                f"  • Volume: {space_data.get('volume', 0):.1f} cf\n"
                f"  • Height: {space_data['ceiling_height']:.1f} ft\n\n"
                f"🔊 Acoustics:\n"
                f"  • Target RT60: {space_data['target_rt60']:.1f} seconds\n"
                f"  • Calculated RT60: {rt60_display}\n\n"
                f"📋 Drawing: {self.drawing.name if self.drawing else 'None'}"
                f"{next_steps}"
            )
            
            # Update status bar
            self.status_bar.showMessage(f"Created space '{space_data['name']}' with {space_data['floor_area']:.0f} sf", 5000)
            
            # Update rectangle to show it's now a space
            self.update_elements_after_space_creation(space_data['name'])
            
        except Exception as e:
            if session is not None:
                session.rollback()
                session.close()
            QMessageBox.critical(self, "Error", f"Failed to create space:\n{str(e)}")
            
    def update_elements_after_space_creation(self, space_name):
        """Update elements list and drawing overlay after space creation"""
        # Find and update the rectangle item in the elements list
        for i in range(self.elements_list.count()):
            item = self.elements_list.item(i)
            element_data = item.data(Qt.UserRole)
            
            if element_data and element_data.get('type') == 'rectangle':
                # Check if this is the rectangle we just converted
                if element_data == self.selected_rectangle:
                    # Update item text to show it's now a space
                    area_text = element_data.get('area_formatted', '')
                    item.setText(f"🏠 {space_name} - {area_text}")
                    
                    # Update element data to mark as converted
                    element_data['converted_to_space'] = True
                    element_data['space_name'] = space_name
                    item.setData(Qt.UserRole, element_data)
                    break
        
        # Update drawing overlay to show visual changes
        if self.drawing_overlay and self.selected_rectangle:
            for rect_data in self.drawing_overlay.rectangles:
                if rect_data == self.selected_rectangle:
                    rect_data['converted_to_space'] = True
                    rect_data['space_name'] = space_name
                    break
            
            # Trigger repaint to show the rectangle in green with space name
            self.drawing_overlay.update()
                    
        # Clear selection
        self.elements_list.clearSelection()
        self.selected_rectangle = None
        
    def delete_selected_element(self):
        """Delete the selected element"""
        current_item = self.elements_list.currentItem()
        if current_item:
            self.delete_element(current_item)
            
    def delete_element(self, item):
        """Delete an element from the list and overlay"""
        element_data = item.data(Qt.UserRole)
        element_type = element_data.get('type') if element_data else None
        
        # Confirm deletion
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                   f"Delete this {element_type}?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Remove from overlay (simplified - would need element ID tracking)
            if self.drawing_overlay and element_type:
                if element_type == 'rectangle':
                    # Find and remove from rectangles list
                    rectangles = self.drawing_overlay.rectangles
                    for i, rect in enumerate(rectangles):
                        if rect == element_data:
                            rectangles.pop(i)
                            break
                elif element_type == 'component':
                    # Find and remove from components list
                    components = self.drawing_overlay.components
                    for i, comp in enumerate(components):
                        if comp == element_data:
                            components.pop(i)
                            break
                elif element_type == 'segment':
                    # Find and remove from segments list
                    segments = self.drawing_overlay.segments
                    for i, seg in enumerate(segments):
                        if seg == element_data:
                            segments.pop(i)
                            break
                elif element_type == 'measurement':
                    # Find and remove from measurements list
                    measurements = self.drawing_overlay.measurements
                    for i, meas in enumerate(measurements):
                        if meas == element_data:
                            measurements.pop(i)
                            break
                            
                self.drawing_overlay.update()
                
            # Remove from list
            row = self.elements_list.row(item)
            self.elements_list.takeItem(row)
            
            # Update displays
            self.update_elements_display()
            
    def create_hvac_path_from_drawing(self):
        """Create HVAC path from drawing elements using the dialog"""
        try:
            # Get HVAC components and segments from drawing elements
            overlay_data = self.drawing_overlay.get_elements_data() if self.drawing_overlay else {}
            components = overlay_data.get('components', [])
            segments = overlay_data.get('segments', [])
            
            print(f"DEBUG: create_hvac_path_from_drawing - Found {len(components)} components and {len(segments)} segments")
            
            # Debug: Print component details
            for i, comp in enumerate(components):
                print(f"DEBUG: Component {i}: {comp.get('component_type', 'unknown')} at ({comp.get('x', 0)}, {comp.get('y', 0)})")
            
            # Debug: Print segment details
            for i, seg in enumerate(segments):
                print(f"DEBUG: Segment {i}: from_component={seg.get('from_component') is not None}, to_component={seg.get('to_component') is not None}")
                if seg.get('from_component'):
                    print(f"DEBUG:   From: {seg['from_component'].get('component_type', 'unknown')} at ({seg['from_component'].get('x', 0)}, {seg['from_component'].get('y', 0)})")
                if seg.get('to_component'):
                    print(f"DEBUG:   To: {seg['to_component'].get('component_type', 'unknown')} at ({seg['to_component'].get('x', 0)}, {seg['to_component'].get('y', 0)})")
            
            if len(components) < 2:
                QMessageBox.information(self, "Create HVAC Path", 
                                       "Need at least 2 HVAC components to create a path.\n"
                                       "Use the Component tool to place HVAC equipment.")
                return
            
            if len(segments) == 0:
                QMessageBox.information(self, "Create HVAC Path",
                                       "Need at least 1 segment connection between components.\n"
                                       "Use the Segment tool to connect HVAC components.")
                return
            
            # Open HVAC path dialog with drawing data
            from ui.dialogs.hvac_path_dialog import HVACPathDialog
            dialog = HVACPathDialog(self, self.project_id)
            
            # Pass drawing data to the dialog
            dialog.set_drawing_data(components, segments, self.drawing.id)
            
            if dialog.exec() == QDialog.Accepted:
                QMessageBox.information(self, "HVAC Path Created", 
                                       f"Successfully created HVAC path: {dialog.path.name if dialog.path else 'Unknown'}")
                
                # Refresh paths list to show new path
                self.load_saved_paths()
                self.paths_updated.emit()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create HVAC path:\n{str(e)}")
    
    def analyze_hvac_path(self):
        """Analyze HVAC noise path from selected components"""
        try:
            # Get HVAC components and segments from drawing elements
            overlay_data = self.drawing_overlay.get_elements_data() if self.drawing_overlay else {}
            components = overlay_data.get('components', [])
            segments = overlay_data.get('segments', [])
            
            if len(components) < 2:
                QMessageBox.information(self, "HVAC Analysis", 
                                       "Need at least 2 HVAC components to create a path.\n"
                                       "Use the Component tool to place HVAC equipment.")
                return
            
            if len(segments) == 0:
                QMessageBox.information(self, "HVAC Analysis",
                                       "Need at least 1 segment connection between components.\n"
                                       "Use the Segment tool to connect HVAC components.")
                return
            
            # Create a simple path from first to last component
            source_component = components[0]
            terminal_component = components[-1]
            
            # Build path data structure
            path_data = {
                'source_component': source_component,
                'terminal_component': terminal_component,
                'segments': []
            }
            
            # Convert segments to calculation format
            for i, segment in enumerate(segments):
                segment_calc_data = {
                    'length': segment.get('length_real', 0),
                    'duct_width': 12,  # Default 12 inches
                    'duct_height': 8,  # Default 8 inches
                    'duct_shape': 'rectangular',
                    'duct_type': 'sheet_metal',
                    'insulation': None,
                    'fittings': []  # No fittings data from segments yet
                }
                path_data['segments'].append(segment_calc_data)
            
            # Perform noise calculation
            results = self.noise_calculator.calculate_hvac_path_noise(path_data)
            
            # Display results
            self.display_hvac_analysis_results(results, source_component, terminal_component)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to analyze HVAC path:\n{str(e)}")
    
    def calculate_all_hvac_paths(self):
        """Calculate noise for all HVAC paths in the project"""
        try:
            session = get_session()
            
            # Get all HVAC paths for this project
            from models.hvac import HVACPath
            hvac_paths = session.query(HVACPath).filter(
                HVACPath.project_id == self.project_id
            ).all()
            
            if not hvac_paths:
                QMessageBox.information(self, "HVAC Calculation",
                                       "No HVAC paths found in this project.\n"
                                       "Create HVAC paths using the drawing tools first.")
                session.close()
                return
            
            calculated_paths = 0
            results_summary = []
            
            for hvac_path in hvac_paths:
                # Build path data from database
                path_data = self.build_path_data_from_db(hvac_path)
                
                if path_data:
                    # Calculate noise
                    results = self.noise_calculator.calculate_hvac_path_noise(path_data)
                    
                    if results['calculation_valid']:
                        # Update database with results
                        hvac_path.calculated_noise = results['terminal_noise']
                        hvac_path.calculated_nc = results['nc_rating']
                        
                        calculated_paths += 1
                        results_summary.append({
                            'name': hvac_path.name,
                            'noise': results['terminal_noise'],
                            'nc': results['nc_rating']
                        })
            
            session.commit()
            session.close()
            
            # Display summary
            if calculated_paths > 0:
                summary_text = f"Calculated {calculated_paths} HVAC paths:\n\n"
                for result in results_summary:
                    summary_text += f"• {result['name']}: {result['noise']:.1f} dB(A), NC-{result['nc']}\n"
                
                QMessageBox.information(self, "HVAC Calculation Complete", summary_text)
            else:
                QMessageBox.warning(self, "Calculation Warning", "No valid HVAC paths could be calculated.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to calculate HVAC paths:\n{str(e)}")
    
    def display_hvac_analysis_results(self, results: dict, source_comp: dict, terminal_comp: dict):
        """Display HVAC noise analysis results"""
        if not results['calculation_valid']:
            error_msg = results.get('error', 'Unknown calculation error')
            QMessageBox.warning(self, "Calculation Error", f"HVAC calculation failed:\n{error_msg}")
            return
        
        # Build results message
        source_type = source_comp.get('component_type', 'unknown').upper()
        terminal_type = terminal_comp.get('component_type', 'unknown').upper()
        
        message = f"HVAC Path Analysis Results\n"
        message += f"{'=' * 40}\n\n"
        message += f"Path: {source_type} → {terminal_type}\n\n"
        message += f"Source Noise Level: {results['source_noise']:.1f} dB(A)\n"
        message += f"Terminal Noise Level: {results['terminal_noise']:.1f} dB(A)\n"
        # Be tolerant of key name differences
        total_att = results.get('total_attenuation')
        if total_att is None:
            total_att = results.get('total_attenuation_dba')
        if total_att is None:
            # Fallback: derive from last segment if present
            try:
                segs = results.get('path_segments', [])
                if segs:
                    last = segs[-1]
                    total_att = last.get('total_attenuation')
                    if total_att is None:
                        total_att = last.get('attenuation_dba')
            except Exception:
                total_att = 0.0
        message += f"Total Attenuation: {float(total_att or 0):.1f} dB\n"
        message += f"NC Rating: NC-{results['nc_rating']}\n\n"
        
        # Add NC criteria description
        nc_description = self.noise_calculator.get_nc_criteria_description(results['nc_rating'])
        message += f"NC Criteria: {nc_description}\n\n"
        
        # Add detailed NC analysis if available
        detailed_nc = results.get('detailed_nc_analysis')
        if detailed_nc:
            message += f"Enhanced Analysis:\n"
            message += f"  Overall dB(A): {detailed_nc['overall_dba']:.1f}\n"
            message += f"  Description: {detailed_nc['nc_description']}\n"
            
            if detailed_nc.get('warnings'):
                message += f"  Warnings: {', '.join(detailed_nc['warnings'])}\n"
            message += "\n"
        
        # Add segment details
        if results['path_segments']:
            message += "Segment Analysis:\n"
            for segment in results['path_segments']:
                seg_num = segment['segment_number']
                message += f"  Segment {seg_num}: {segment['noise_before']:.1f} → {segment['noise_after']:.1f} dB(A)\n"
                message += f"    Distance Loss: {segment['distance_loss']:.1f} dB\n"
                message += f"    Duct Loss: {segment['duct_loss']:.1f} dB\n"
                if segment['fitting_additions'] > 0:
                    message += f"    Fitting Additions: +{segment['fitting_additions']:.1f} dB\n"
        
        # Add warnings
        if results.get('warnings'):
            message += f"\nWarnings:\n"
            for warning in results['warnings']:
                message += f"• {warning}\n"
        
        # Show results dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("HVAC Path Analysis")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # Make the dialog wider to show all text
        msg_box.setStyleSheet("QLabel { min-width: 500px; }")
        msg_box.exec()
    
    def build_path_data_from_db(self, hvac_path) -> dict:
        """Build path data structure from database HVAC path"""
        try:
            path_data = {
                'source_component': {},
                'terminal_component': {},
                'segments': []
            }
            
            segments = hvac_path.segments
            if not segments:
                return None
            
            # Get source and terminal components
            first_segment = segments[0]
            last_segment = segments[-1]
            
            if first_segment.from_component:
                comp = first_segment.from_component
                path_data['source_component'] = {
                    'component_type': comp.component_type,
                    'noise_level': comp.noise_level or STANDARD_COMPONENTS.get(comp.component_type, {}).get('noise_level', 50.0)
                }
            
            if last_segment.to_component:
                comp = last_segment.to_component
                path_data['terminal_component'] = {
                    'component_type': comp.component_type,
                    'noise_level': comp.noise_level or STANDARD_COMPONENTS.get(comp.component_type, {}).get('noise_level', 25.0)
                }
            
            # Convert segments
            for segment in segments:
                segment_data = {
                    'length': segment.length or 0,
                    'duct_width': segment.duct_width or 12,
                    'duct_height': segment.duct_height or 8,  
                    'duct_shape': segment.duct_shape or 'rectangular',
                    'duct_type': segment.duct_type or 'sheet_metal',
                    'insulation': segment.insulation,
                    'fittings': []
                }
                
                # Add fittings if any
                for fitting in segment.fittings:
                    fitting_data = {
                        'fitting_type': fitting.fitting_type,
                        'noise_adjustment': fitting.noise_adjustment or 0
                    }
                    segment_data['fittings'].append(fitting_data)
                
                path_data['segments'].append(segment_data)
            
            return path_data
            
        except Exception as e:
            print(f"Error building path data: {e}")
            return None
    
    def analyze_nc_compliance(self):
        """Analyze NC compliance for spaces in the project"""
        try:
            from PySide6.QtWidgets import QInputDialog
            
            # Get available spaces for analysis
            session = get_session()
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            
            if not spaces:
                QMessageBox.information(self, "NC Analysis", 
                                       "No spaces found in this project.\n"
                                       "Create spaces from rectangles first.")
                session.close()
                return
            
            # Let user select a space
            space_names = [f"{space.name} (RT60: {space.calculated_rt60:.2f}s)" for space in spaces]
            space_name, ok = QInputDialog.getItem(
                self, "Select Space", "Choose space for NC analysis:", space_names, 0, False
            )
            
            if not ok:
                session.close()
                return
            
            # Find selected space
            selected_space = None
            for space in spaces:
                if space_name.startswith(space.name):
                    selected_space = space
                    break
            
            if not selected_space:
                session.close()
                return
            
            # Get space type for analysis
            space_types = [
                "Private Office", "Open Office", "Conference Room", "Classroom", 
                "Library", "Hospital Room", "Restaurant", "Retail", 
                "Gymnasium", "Lobby", "Corridor"
            ]
            
            space_type, ok = QInputDialog.getItem(
                self, "Space Type", "Select space type for standards comparison:", 
                space_types, 0, False
            )
            
            if not ok:
                session.close()
                return
            
            # Get target NC if desired
            target_nc, ok = QInputDialog.getInt(
                self, "Target NC", "Enter target NC rating (or 0 for standards-based):", 
                0, 0, 65, 1
            )
            
            target_nc = target_nc if target_nc > 0 else None
            
            # Find HVAC paths targeting this space
            from models.hvac import HVACPath
            hvac_paths = session.query(HVACPath).filter(
                HVACPath.project_id == self.project_id,
                HVACPath.target_space_id == selected_space.id
            ).all()
            
            if not hvac_paths:
                # Use a default noise level for analysis
                noise_level = 35.0  # Default typical office noise
                QMessageBox.information(self, "No HVAC Data", 
                                       f"No HVAC paths found for this space.\n"
                                       f"Using default noise level of {noise_level} dB(A) for analysis.")
            else:
                # Use average noise from HVAC paths
                valid_paths = [p for p in hvac_paths if p.calculated_noise]
                if valid_paths:
                    noise_level = sum(p.calculated_noise for p in valid_paths) / len(valid_paths)
                else:
                    noise_level = 35.0
            
            session.close()
            
            # Perform NC compliance analysis
            compliance_result = self.noise_calculator.analyze_space_nc_compliance(
                noise_level, space_type.lower().replace(" ", "_"), target_nc
            )
            
            # Display results
            self.display_nc_compliance_results(compliance_result, selected_space.name)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to analyze NC compliance:\n{str(e)}")
    
    def display_nc_compliance_results(self, compliance_result: dict, space_name: str):
        """Display NC compliance analysis results"""
        if compliance_result.get('analysis_failed'):
            error_msg = compliance_result.get('error', 'Unknown analysis error')
            QMessageBox.warning(self, "Analysis Error", f"NC compliance analysis failed:\n{error_msg}")
            return
        
        # Build results message
        message = f"NC Compliance Analysis: {space_name}\n"
        message += f"{'=' * 50}\n\n"
        
        # Basic results
        message += f"Measured Noise Level: {compliance_result['measured_noise_dba']:.1f} dB(A)\n"
        message += f"NC Rating: NC-{compliance_result['nc_rating']}\n"
        message += f"Space Type: {compliance_result['space_type'].replace('_', ' ').title()}\n\n"
        
        # Standards comparison
        standards = compliance_result['standards_comparison']
        message += f"Standards Comparison:\n"
        message += f"  Recommended NC: NC-{standards['recommended_nc']}\n"
        message += f"  Maximum NC: NC-{standards['maximum_nc']}\n"
        message += f"  Compliance: {standards['compliance']}\n"
        message += f"  Status: {standards['status']}\n\n"
        
        # NC description
        message += f"NC Criteria: {compliance_result['nc_description']}\n\n"
        
        # Exceedances
        if compliance_result['exceedances']:
            message += f"Frequency Exceedances:\n"
            for freq, exceedance in compliance_result['exceedances']:
                message += f"  {freq} Hz: +{exceedance:.1f} dB over limit\n"
            message += "\n"
        
        # Recommendations
        if compliance_result['recommendations']:
            message += f"Recommendations:\n"
            for i, rec in enumerate(compliance_result['recommendations'], 1):
                message += f"  {i}. {rec}\n"
            message += "\n"
        
        # Warnings
        if compliance_result['warnings']:
            message += f"Warnings:\n"
            for warning in compliance_result['warnings']:
                message += f"• {warning}\n"
        
        # Show results dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("NC Compliance Analysis")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # Make the dialog wider to show all text
        msg_box.setStyleSheet("QLabel { min-width: 600px; font-family: 'Courier New', monospace; }")
        msg_box.exec()
    
    def export_to_excel(self):
        """Export project analysis to Excel"""
        try:
            if not EXCEL_EXPORT_AVAILABLE:
                QMessageBox.warning(self, "Export Not Available", 
                                   "Excel export requires the openpyxl library.\n"
                                   "Please install it using: pip install openpyxl")
                return
            
            # Get export file path
            from PySide6.QtWidgets import QFileDialog
            
            default_name = f"{self.project.name.replace(' ', '_')}_acoustic_analysis.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export to Excel", default_name, 
                "Excel Files (*.xlsx);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Create export options dialog
            export_options = self.get_export_options()
            if not export_options:
                return
            
            # Create exporter and get summary
            exporter = ExcelExporter()
            summary = exporter.get_export_summary(self.project_id)
            
            if "error" in summary:
                QMessageBox.critical(self, "Export Error", f"Failed to prepare export:\n{summary['error']}")
                return
            
            # Confirm export
            confirm_msg = f"Export Summary for '{summary['project_name']}':\n\n"
            confirm_msg += f"• {summary['total_spaces']} spaces ({summary['spaces_with_rt60']} with RT60)\n"
            confirm_msg += f"• {summary['total_hvac_paths']} HVAC paths ({summary['paths_with_noise']} with noise calc)\n"
            confirm_msg += f"• {summary['total_components']} HVAC components\n\n"
            confirm_msg += f"Sheets to export: {', '.join(summary['sheets_to_export'])}\n\n"
            confirm_msg += f"Export to: {file_path}"
            
            reply = QMessageBox.question(self, "Confirm Export", confirm_msg,
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.Yes)
            
            if reply != QMessageBox.Yes:
                return
            
            # Perform export
            success = exporter.export_project_analysis(self.project_id, file_path, export_options)
            
            if success:
                reply = QMessageBox.information(self, "Export Complete", 
                                              f"Successfully exported project analysis to:\n{file_path}\n\n"
                                              f"Would you like to open the file?",
                                              QMessageBox.Yes | QMessageBox.No,
                                              QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    import os
                    import subprocess
                    import platform
                    
                    try:
                        if platform.system() == 'Darwin':  # macOS
                            subprocess.call(['open', file_path])
                        elif platform.system() == 'Windows':  # Windows
                            os.startfile(file_path)
                        else:  # Linux
                            subprocess.call(['xdg-open', file_path])
                    except Exception as e:
                        QMessageBox.information(self, "File Exported", 
                                              f"Export completed but couldn't open file automatically:\n{file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export project analysis to Excel.")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export to Excel:\n{str(e)}")
    
    def get_export_options(self) -> Optional[ExportOptions]:
        """Get export options from user"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel
            
            class ExportOptionsDialog(QDialog):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.setWindowTitle("Excel Export Options")
                    self.setModal(True)
                    self.setFixedSize(400, 350)
                    
                    layout = QVBoxLayout()
                    
                    # Instructions
                    instructions = QLabel("Select what to include in the Excel export:")
                    instructions.setWordWrap(True)
                    layout.addWidget(instructions)
                    
                    # Checkboxes
                    self.spaces_cb = QCheckBox("Spaces Analysis (RT60, materials)")
                    self.spaces_cb.setChecked(True)
                    layout.addWidget(self.spaces_cb)
                    
                    self.hvac_paths_cb = QCheckBox("HVAC Paths (noise calculations)")
                    self.hvac_paths_cb.setChecked(True)
                    layout.addWidget(self.hvac_paths_cb)
                    
                    self.components_cb = QCheckBox("HVAC Components (equipment list)")
                    self.components_cb.setChecked(True)
                    layout.addWidget(self.components_cb)
                    
                    self.rt60_details_cb = QCheckBox("RT60 Compliance Details")
                    self.rt60_details_cb.setChecked(True)
                    layout.addWidget(self.rt60_details_cb)
                    
                    self.nc_analysis_cb = QCheckBox("NC Analysis and Standards")
                    self.nc_analysis_cb.setChecked(True)
                    layout.addWidget(self.nc_analysis_cb)
                    
                    self.recommendations_cb = QCheckBox("Recommendations and Issues")
                    self.recommendations_cb.setChecked(True)
                    layout.addWidget(self.recommendations_cb)
                    
                    self.charts_cb = QCheckBox("Charts and Graphs (future)")
                    self.charts_cb.setChecked(False)
                    self.charts_cb.setEnabled(False)  # Not implemented yet
                    layout.addWidget(self.charts_cb)
                    
                    # Buttons
                    button_layout = QHBoxLayout()
                    
                    select_all_btn = QPushButton("Select All")
                    select_all_btn.clicked.connect(self.select_all)
                    
                    select_none_btn = QPushButton("Select None")
                    select_none_btn.clicked.connect(self.select_none)
                    
                    ok_btn = QPushButton("Export")
                    ok_btn.clicked.connect(self.accept)
                    ok_btn.setDefault(True)
                    
                    cancel_btn = QPushButton("Cancel")
                    cancel_btn.clicked.connect(self.reject)
                    
                    button_layout.addWidget(select_all_btn)
                    button_layout.addWidget(select_none_btn)
                    button_layout.addStretch()
                    button_layout.addWidget(ok_btn)
                    button_layout.addWidget(cancel_btn)
                    
                    layout.addLayout(button_layout)
                    self.setLayout(layout)
                
                def select_all(self):
                    for cb in [self.spaces_cb, self.hvac_paths_cb, self.components_cb, 
                              self.rt60_details_cb, self.nc_analysis_cb, self.recommendations_cb]:
                        cb.setChecked(True)
                
                def select_none(self):
                    for cb in [self.spaces_cb, self.hvac_paths_cb, self.components_cb, 
                              self.rt60_details_cb, self.nc_analysis_cb, self.recommendations_cb]:
                        cb.setChecked(False)
                
                def get_options(self):
                    return ExportOptions(
                        include_spaces=self.spaces_cb.isChecked(),
                        include_hvac_paths=self.hvac_paths_cb.isChecked(),
                        include_components=self.components_cb.isChecked(),
                        include_rt60_details=self.rt60_details_cb.isChecked(),
                        include_nc_analysis=self.nc_analysis_cb.isChecked(),
                        include_recommendations=self.recommendations_cb.isChecked(),
                        include_charts=self.charts_cb.isChecked()
                    )
            
            dialog = ExportOptionsDialog(self)
            if dialog.exec() == QDialog.Accepted:
                return dialog.get_options()
            else:
                return None
                
        except Exception as e:
            QMessageBox.warning(self, "Options Error", f"Error getting export options:\n{str(e)}")
            return ExportOptions()  # Default options

    # Path visibility methods
    def load_saved_paths(self):
        """Load saved HVAC paths from database and populate the paths list"""
        session = None
        try:
            session = get_session()
            
            # Import HVACPath model
            from models.hvac import HVACPath
            
            # Query HVAC paths for this project
            hvac_paths = session.query(HVACPath).filter(
                HVACPath.project_id == self.project_id
            ).all()
            
            # Clear the current list
            self.paths_list.clear()
            self.visible_paths.clear()
            
            if not hvac_paths:
                self.paths_summary_label.setText("No paths saved")
                session.close()
                return
                
            # Update summary
            path_count = len(hvac_paths)
            calculated_count = sum(1 for p in hvac_paths if p.calculated_noise)
            self.paths_summary_label.setText(f"{path_count} paths ({calculated_count} calculated)")
            
            # Add paths to list with checkboxes
            for hvac_path in hvac_paths:
                # Register path elements for show/hide functionality
                if self.drawing_overlay:
                    self.register_existing_path_elements(hvac_path)
                
                # Create list item with checkbox
                item = QListWidgetItem()
                
                # Create a widget container for path controls
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(5, 2, 5, 2)
                
                # Path name label
                path_label = QLabel(self.format_path_display_name(hvac_path))
                path_label.setToolTip(self.format_path_tooltip(hvac_path))
                # Let double-clicks pass through label to the list item row
                path_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                
                # Toggle button for show/hide
                toggle_btn = QPushButton("👁️‍🗨️")  # Hidden eye initially
                toggle_btn.setMaximumWidth(35)
                toggle_btn.setMaximumHeight(25)
                toggle_btn.setToolTip("Click to show/hide this path on drawing")
                toggle_btn.setCheckable(True)  # Make it a toggle button
                toggle_btn.setChecked(False)  # Default to hidden
                
                # Style the toggle button
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        border: 1px solid #888;
                        border-radius: 3px;
                        padding: 2px;
                    }
                    QPushButton:checked {
                        background-color: #4CAF50;
                        border: 1px solid #45a049;
                    }
                """)
                
                # Connect toggle button
                toggle_btn.clicked.connect(lambda checked, pid=hvac_path.id, btn=toggle_btn: self.toggle_path_visibility(pid, checked, btn))
                
                layout.addWidget(path_label)
                layout.addStretch()  # Push toggle button to the right
                layout.addWidget(toggle_btn)
                
                # Store path data in the item
                item.setData(Qt.UserRole, hvac_path)
                
                # Set the widget as the item widget
                self.paths_list.addItem(item)
                self.paths_list.setItemWidget(item, widget)
                # Also allow double-clicking the row to open the editor directly
                def _row_dbl_click(event, p=hvac_path):
                    try:
                        if event.button() == Qt.LeftButton:
                            self.open_path_editor(p)
                            event.accept()
                            return
                    except Exception:
                        pass
                    QWidget.mouseDoubleClickEvent(widget, event)
                widget.mouseDoubleClickEvent = _row_dbl_click
            
            session.close()
            
        except Exception as e:
            if session is not None:
                session.close()
            QMessageBox.warning(self, "Error", f"Failed to load saved paths:\n{str(e)}")
    
    def format_path_display_name(self, hvac_path):
        """Format the display name for a path in the list"""
        path_type = hvac_path.path_type or "supply"
        space_name = hvac_path.target_space.name if hvac_path.target_space else "No Space"
        
        # Add noise info if available
        noise_info = ""
        if hvac_path.calculated_noise:
            noise_info = f" [{hvac_path.calculated_noise:.1f} dB(A)]"
            
        return f"{hvac_path.name} ({path_type}) → {space_name}{noise_info}"
    
    def format_path_tooltip(self, hvac_path):
        """Format tooltip information for a path"""
        tooltip = f"Path: {hvac_path.name}\n"
        tooltip += f"Type: {hvac_path.path_type or 'supply'}\n"
        tooltip += f"Target Space: {hvac_path.target_space.name if hvac_path.target_space else 'None'}\n"
        tooltip += f"Components: {len(hvac_path.segments) + 1 if hvac_path.segments else 0}\n"
        
        if hvac_path.calculated_noise:
            tooltip += f"Noise Level: {hvac_path.calculated_noise:.1f} dB(A)\n"
            tooltip += f"NC Rating: NC-{hvac_path.calculated_nc:.0f}" if hvac_path.calculated_nc else "NC Rating: Not calculated"
        else:
            tooltip += "Noise: Not calculated"
            
        return tooltip
    
    def handle_path_visibility_changed(self, path_id: int, visible: bool):
        """Handle path visibility checkbox change"""
        print(f"DEBUG: Path {path_id} visibility changed to {visible}")
        if visible:
            self.visible_paths.add(path_id)
            self.show_path_on_drawing(path_id)
        else:
            self.visible_paths.discard(path_id)
            self.hide_path_on_drawing(path_id)
        print(f"DEBUG: Drawing overlay visible_paths after change: {list(self.drawing_overlay.visible_paths.keys()) if self.drawing_overlay else 'No overlay'}")
    
    def show_path_on_drawing(self, path_id: int):
        """Show a specific path on the drawing overlay"""
        if self.drawing_overlay:
            # Add path to visible paths (this will make path elements visible)
            self.drawing_overlay.visible_paths[path_id] = True
            self.drawing_overlay.update()
            print(f"DEBUG: Showing path {path_id}, visible paths: {list(self.drawing_overlay.visible_paths.keys())}")
        
    def hide_path_on_drawing(self, path_id: int):
        """Hide a specific path from the drawing overlay"""
        if self.drawing_overlay:
            # Remove path from visible paths (this will hide path elements)
            self.drawing_overlay.visible_paths.pop(path_id, None)
            self.drawing_overlay.update()
            print(f"DEBUG: Hiding path {path_id}, visible paths: {list(self.drawing_overlay.visible_paths.keys())}")
    
    def show_all_paths(self):
        """Show all paths on the drawing"""
        for i in range(self.paths_list.count()):
            item = self.paths_list.item(i)
            widget = self.paths_list.itemWidget(item)
            if widget:
                toggle_btn = widget.findChild(QPushButton)
                if toggle_btn and not toggle_btn.isChecked():
                    toggle_btn.setChecked(True)
                    toggle_btn.clicked.emit(True)  # Trigger the click handler
    
    def hide_all_paths(self):
        """Hide all paths from the drawing"""
        for i in range(self.paths_list.count()):
            item = self.paths_list.item(i)
            widget = self.paths_list.itemWidget(item)
            if widget:
                toggle_btn = widget.findChild(QPushButton)
                if toggle_btn and toggle_btn.isChecked():
                    toggle_btn.setChecked(False)
                    toggle_btn.clicked.emit(False)  # Trigger the click handler
    
    def show_path_context_menu(self, position):
        """Show context menu for paths list"""
        item = self.paths_list.itemAt(position)
        if not item:
            return
            
        hvac_path = item.data(Qt.UserRole)
        if not hvac_path:
            return
        
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        # Toggle visibility action
        checkbox = self.paths_list.itemWidget(item)
        if checkbox:
            if checkbox.isChecked():
                hide_action = menu.addAction("👁️‍🗨️ Hide Path")
                hide_action.triggered.connect(lambda: checkbox.setChecked(False))
            else:
                show_action = menu.addAction("👁️ Show Path")
                show_action.triggered.connect(lambda: checkbox.setChecked(True))
        
        menu.addSeparator()
        
        # Path information action
        info_action = menu.addAction("ℹ️ Path Information")
        info_action.triggered.connect(lambda: self.show_path_information(hvac_path))
        
        # Register all elements action
        register_all_action = menu.addAction("🔗 Register All Drawing Elements")
        register_all_action.triggered.connect(lambda: self.register_all_elements_to_path(hvac_path.id))
        register_all_action.setToolTip("Register all currently drawn components and segments to this path")
        
        # Calculate noise action (if not calculated)
        if not hvac_path.calculated_noise:
            calc_action = menu.addAction("🔊 Calculate Noise")
            calc_action.triggered.connect(lambda: self.calculate_path_noise(hvac_path.id))
        
        menu.exec_(self.paths_list.mapToGlobal(position))

    def open_path_editor_from_item(self, item: QListWidgetItem):
        """Open the Edit HVAC Path dialog when a saved path list item is double-clicked."""
        try:
            hvac_path = item.data(Qt.UserRole)
            if not hvac_path:
                return
            # Open in edit mode
            dlg = HVACPathDialog(self, project_id=self.project_id, path=hvac_path)
            if dlg.exec() == QDialog.Accepted:
                # Refresh list and notify listeners
                self.load_saved_paths()
                try:
                    self.paths_updated.emit()
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.warning(self, "Path Editor", f"Failed to open path editor:\n{e}")

    def overlay_element_double_clicked(self, element: dict):
        """Open component or segment editor when double-clicked on the drawing overlay."""
        try:
            etype = (element or {}).get('type')
            if etype == 'component':
                # Prefer DB component id embedded via registration; else try to match by position/type
                db_id = element.get('db_component_id')
                session = None
                try:
                    from models.hvac import HVACComponent
                    if db_id:
                        session = get_session()
                        comp = session.query(HVACComponent).filter(HVACComponent.id == db_id).first()
                        session.close()
                    else:
                        # Fallback lookup by position/type within this drawing; if not found,
                        # relax matching to nearest component within a small pixel tolerance.
                        session = get_session()
                        from models.hvac import HVACComponent as _HC
                        try:
                            comp = (
                                session.query(_HC)
                                .filter(
                                    _HC.project_id == self.project_id,
                                    _HC.drawing_id == (self.drawing.id if self.drawing else None),
                                    _HC.x_position == element.get('x'),
                                    _HC.y_position == element.get('y'),
                                    _HC.component_type == element.get('component_type')
                                )
                                .first()
                            )
                            if comp is None:
                                # Relax: search by proximity (<= 12 px) on same drawing and project
                                ex = float(element.get('x') or 0)
                                ey = float(element.get('y') or 0)
                                candidates = (
                                    session.query(_HC)
                                    .filter(
                                        _HC.project_id == self.project_id,
                                        _HC.drawing_id == (self.drawing.id if self.drawing else None)
                                    )
                                    .all()
                                )
                                best = None
                                best_dist = 999999.0
                                for c in candidates:
                                    dx = float(getattr(c, 'x_position', 0.0) or 0.0) - ex
                                    dy = float(getattr(c, 'y_position', 0.0) or 0.0) - ey
                                    d = abs(dx) + abs(dy)
                                    if d < best_dist:
                                        best = c
                                        best_dist = d
                                # Accept if within tolerance (12 px manhattan)
                                if best is not None and best_dist <= 12.0:
                                    comp = best
                        finally:
                            session.close()
                    if comp is None:
                        QMessageBox.information(self, "Edit Component", "No saved component found at this location.")
                        return
                finally:
                    try:
                        if session is not None:
                            session.close()
                    except Exception:
                        pass
                print("DEBUG[DrawingInterface]: Opening HVACComponentDialog for component id=", getattr(comp, 'id', None),
                      " name=", getattr(comp, 'name', None))
                dlg = HVACComponentDialog(self, self.project_id, self.drawing.id if self.drawing else None, comp)
                dlg.exec()
                return
            if etype == 'segment':
                # Eager-load relationships to avoid detached lazy-loads when dialog accesses them
                seg_id = element.get('db_segment_id')
                session = None
                seg = None
                try:
                    from sqlalchemy.orm import selectinload
                    from models.hvac import HVACSegment
                    session = get_session()
                    if seg_id:
                        seg = (
                            session.query(HVACSegment)
                            .options(
                                selectinload(HVACSegment.from_component),
                                selectinload(HVACSegment.to_component),
                                selectinload(HVACSegment.fittings),
                            )
                            .filter(HVACSegment.id == int(seg_id))
                            .first()
                        )
                    else:
                        # Fallback: find segment on this path whose endpoints are nearest to the clicked overlay endpoints
                        from models.hvac import HVACSegment as _HS
                        segments = (
                            session.query(_HS)
                            .options(
                                selectinload(_HS.from_component),
                                selectinload(_HS.to_component),
                                selectinload(_HS.fittings),
                            )
                            .filter(_HS.hvac_path_id == element.get('db_path_id'))
                            .all()
                        )
                        best = None
                        best_dist = 999999.0
                        tol = 12.0
                        ex_f = element.get('from_component') or {}
                        ex_t = element.get('to_component') or {}
                        fx = float(ex_f.get('x') or 0)
                        fy = float(ex_f.get('y') or 0)
                        tx = float(ex_t.get('x') or 0)
                        ty = float(ex_t.get('y') or 0)
                        for s in segments:
                            if not (s.from_component and s.to_component):
                                continue
                            d1 = abs(float(getattr(s.from_component, 'x_position', 0.0)) - fx) + abs(float(getattr(s.from_component, 'y_position', 0.0)) - fy)
                            d2 = abs(float(getattr(s.to_component, 'x_position', 0.0)) - tx) + abs(float(getattr(s.to_component, 'y_position', 0.0)) - ty)
                            d = d1 + d2
                            if d < best_dist:
                                best = s
                                best_dist = d
                        if best is not None and best_dist <= (2 * tol):
                            seg = best
                    if seg is None:
                        QMessageBox.information(self, "Edit Segment", "No saved segment found here.")
                        return
                    # Access relationships while session is open
                    _ = seg.from_component, seg.to_component
                    try:
                        _ = list(seg.fittings)
                    except Exception:
                        pass
                    # Optionally detach to be safe
                    try:
                        session.expunge(seg)
                        if seg.from_component:
                            session.expunge(seg.from_component)
                        if seg.to_component:
                            session.expunge(seg.to_component)
                    except Exception:
                        pass
                finally:
                    try:
                        if session is not None:
                            session.close()
                    except Exception:
                        pass
                dlg = HVACSegmentDialog(
                    self,
                    hvac_path_id=getattr(seg, 'hvac_path_id', None),
                    from_component=getattr(seg, 'from_component', None),
                    to_component=getattr(seg, 'to_component', None),
                    segment=seg,
                )
                try:
                    # Keep the drawing overlay in sync when a segment is saved from the dialog
                    dlg.segment_saved.connect(self._on_segment_saved)
                except Exception:
                    pass
                dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Edit Element", f"Failed to open editor:\n{e}")
    
    def show_path_information(self, hvac_path):
        """Show detailed information about a path"""
        info = f"HVAC Path Information\n"
        info += f"{'=' * 30}\n\n"
        info += f"Name: {hvac_path.name}\n"
        info += f"Type: {hvac_path.path_type or 'supply'}\n"
        info += f"Description: {hvac_path.description or 'None'}\n"
        info += f"Target Space: {hvac_path.target_space.name if hvac_path.target_space else 'None'}\n"
        info += f"Components: {len(hvac_path.segments) + 1 if hvac_path.segments else 0}\n"
        info += f"Segments: {len(hvac_path.segments) if hvac_path.segments else 0}\n\n"
        
        if hvac_path.calculated_noise:
            info += f"Calculated Noise: {hvac_path.calculated_noise:.1f} dB(A)\n"
            info += f"NC Rating: NC-{hvac_path.calculated_nc:.0f}" if hvac_path.calculated_nc else "NC Rating: Not calculated"
        else:
            info += "Noise: Not calculated"
        
        QMessageBox.information(self, "Path Information", info)

    def open_path_editor(self, hvac_path):
        """Open the Edit HVAC Path dialog for a given HVACPath instance."""
        try:
            if not hvac_path:
                return
            dlg = HVACPathDialog(self, project_id=self.project_id, path=hvac_path)
            if dlg.exec() == QDialog.Accepted:
                self.load_saved_paths()
                try:
                    self.paths_updated.emit()
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.warning(self, "Path Editor", f"Failed to open path editor:\n{e}")
    
    def calculate_path_noise(self, path_id: int):
        """Calculate noise for a specific path"""
        try:
            # Use the existing HVAC path calculator
            result = self.hvac_path_calculator.analyze_hvac_path(path_id)
            
            if result and result.calculation_valid:
                QMessageBox.information(self, "Calculation Complete", 
                                      f"Path '{result.path_name}' calculated:\n"
                                      f"Terminal Noise: {result.terminal_noise:.1f} dB(A)\n"
                                      f"NC Rating: NC-{result.nc_rating:.0f}")
                
                # Refresh the paths list to show updated values
                self.load_saved_paths()
            else:
                QMessageBox.warning(self, "Calculation Failed", 
                                  "Unable to calculate noise for this path.\n"
                                  "Check that all components and segments are properly defined.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to calculate path noise:\n{str(e)}")
    
    def register_existing_path_elements(self, hvac_path):
        """Register existing path elements in the drawing overlay for show/hide functionality"""
        if not self.drawing_overlay:
            return
            
        try:
            path_components = []
            path_segments = []
            
            # Find drawing elements that match the path's components and segments
            overlay_data = self.drawing_overlay.get_elements_data()
            drawing_components = overlay_data.get('components', [])
            drawing_segments = overlay_data.get('segments', [])
            
            # print(f"DEBUG: Registering path {hvac_path.id} with {len(hvac_path.segments)} database segments")
            # print(f"DEBUG: Available drawing elements: {len(drawing_components)} components, {len(drawing_segments)} segments")
            
            # Match path components to drawing components
            for i, segment in enumerate(hvac_path.segments):
                print(f"DEBUG: Processing segment {i}")
                
                if segment.from_component:
                    db_comp = segment.from_component
                    print(f"DEBUG: Looking for from_component: {db_comp.component_type} at ({db_comp.x_position}, {db_comp.y_position})")
                    
                    # Look for matching component in drawing elements
                    found = False
                    for comp in drawing_components:
                        if (comp.get('x') == db_comp.x_position and
                            comp.get('y') == db_comp.y_position and
                            comp.get('component_type') == db_comp.component_type):
                            if comp not in path_components:
                                path_components.append(comp)
                                # Attach DB id for edit lookups
                                comp['db_component_id'] = db_comp.id
                                print(f"DEBUG: Found matching from_component: {comp}")
                            found = True
                            break
                    if not found:
                        print(f"DEBUG: No match found for from_component: {db_comp.component_type} at ({db_comp.x_position}, {db_comp.y_position})")
                
                if segment.to_component:
                    db_comp = segment.to_component
                    print(f"DEBUG: Looking for to_component: {db_comp.component_type} at ({db_comp.x_position}, {db_comp.y_position})")
                    
                    # Look for matching component in drawing elements
                    found = False
                    for comp in drawing_components:
                        if (comp.get('x') == db_comp.x_position and
                            comp.get('y') == db_comp.y_position and
                            comp.get('component_type') == db_comp.component_type):
                            if comp not in path_components:
                                path_components.append(comp)
                                # Attach DB id for edit lookups
                                comp['db_component_id'] = db_comp.id
                                print(f"DEBUG: Found matching to_component: {comp}")
                            found = True
                            break
                    if not found:
                        print(f"DEBUG: No match found for to_component: {db_comp.component_type} at ({db_comp.x_position}, {db_comp.y_position})")
                
                # Match segments (robust: allow small pixel tolerance on endpoints)
                if segment.from_component and segment.to_component:
                    print(f"DEBUG: Looking for segment from {segment.from_component.component_type} to {segment.to_component.component_type}")
                    found = False
                    tol = 12.0  # pixels
                    fx = float(segment.from_component.x_position or 0.0)
                    fy = float(segment.from_component.y_position or 0.0)
                    tx = float(segment.to_component.x_position or 0.0)
                    ty = float(segment.to_component.y_position or 0.0)
                    for seg in drawing_segments:
                        # Check if this segment connects the same components (within tolerance)
                        from_comp = seg.get('from_component')
                        to_comp = seg.get('to_component')
                        if not (from_comp and to_comp):
                            continue
                        d1 = abs(float(from_comp.get('x') or 0) - fx) + abs(float(from_comp.get('y') or 0) - fy)
                        d2 = abs(float(to_comp.get('x') or 0) - tx) + abs(float(to_comp.get('y') or 0) - ty)
                        if d1 <= tol and d2 <= tol:
                            if seg not in path_segments:
                                path_segments.append(seg)
                                # Attach DB ids for edit lookups
                                seg['db_segment_id'] = segment.id
                                seg['db_path_id'] = hvac_path.id
                                # Also synchronize overlay label length with DB value
                                try:
                                    seg['length_real'] = float(getattr(segment, 'length', 0) or 0)
                                    fmtr = self.drawing_overlay.scale_manager.format_distance
                                    seg['length_formatted'] = fmtr(seg['length_real'])
                                except Exception:
                                    pass
                                print(f"DEBUG: Found matching segment (tol {tol}px): {from_comp.get('component_type')} -> {to_comp.get('component_type')}")
                            found = True
                            break
                    if not found:
                        print(f"DEBUG: No matching segment found (with tolerance) for {segment.from_component.component_type} -> {segment.to_component.component_type}")
            
            # Register the found elements
            if path_components or path_segments:
                self.drawing_overlay.register_path_elements(hvac_path.id, path_components, path_segments)
                print(f"DEBUG: Registered path {hvac_path.id} with {len(path_components)} components and {len(path_segments)} segments")
            else:
                print(f"DEBUG: No elements found to register for path {hvac_path.id}")
            
        except Exception as e:
            print(f"Error registering path elements for path {hvac_path.id}: {e}")

    def _on_segment_saved(self, segment) -> None:
        """After editing a segment in the dialog, update any registered overlay
        segment to reflect the new length so UI values stay linked.
        """
        try:
            if not self.drawing_overlay:
                return
            seg_id = getattr(segment, 'id', None)
            if seg_id is None:
                return
            updated = False
            for seg in self.drawing_overlay.segments:
                try:
                    if int(seg.get('db_segment_id')) == int(seg_id):
                        new_len = float(getattr(segment, 'length', 0) or 0)
                        seg['length_real'] = new_len
                        fmtr = self.drawing_overlay.scale_manager.format_distance
                        seg['length_formatted'] = fmtr(new_len)
                        updated = True
                        break
                except Exception:
                    continue
            if updated:
                # Ensure tools see the latest geometry/meta
                try:
                    self.drawing_overlay.update_segment_tool_components()
                except Exception:
                    pass
                self.drawing_overlay.update()
        except Exception:
            pass
    
    def register_all_elements_to_path(self, path_id: int):
        """Register all currently drawn elements to the specified path"""
        if not self.drawing_overlay:
            return
            
        try:
            # Get all current drawing elements
            overlay_data = self.drawing_overlay.get_elements_data()
            all_components = overlay_data.get('components', [])
            all_segments = overlay_data.get('segments', [])
            
            # Register all elements to this path
            self.drawing_overlay.register_path_elements(path_id, all_components, all_segments)
            
            # Show confirmation
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Elements Registered", 
                                  f"Registered {len(all_components)} components and {len(all_segments)} segments to path {path_id}.\n\n"
                                  "Now when you hide this path, all drawing elements will be hidden.")
            
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Registration Error", f"Failed to register elements:\n{str(e)}")
    
    def toggle_path_visibility(self, path_id: int, visible: bool, button: QPushButton):
        """Toggle a path's visibility using the eye button"""
        print(f"DEBUG: Toggle path {path_id} visibility: {visible}")
        
        # Update button appearance
        if visible:
            button.setText("👁️")  # Open eye for visible
        else:
            button.setText("👁️‍🗨️")  # Closed eye for hidden
            
        # Call visibility handler
        self.handle_path_visibility_changed(path_id, visible)
    
    def force_show_path(self, path_id: int):
        """Force show a path (debug method)"""
        print(f"DEBUG: Force showing path {path_id}")
        
        # Find and activate the toggle button
        for i in range(self.paths_list.count()):
            item = self.paths_list.item(i)
            hvac_path = item.data(Qt.UserRole)
            if hvac_path and hvac_path.id == path_id:
                widget = self.paths_list.itemWidget(item)
                if widget:
                    toggle_btn = widget.findChild(QPushButton)
                    if toggle_btn and not toggle_btn.isChecked():
                        toggle_btn.setChecked(True)
                        toggle_btn.clicked.emit(True)
                        print(f"DEBUG: Force-activated toggle button for path {path_id}")
                break
    
    def toggle_path_only_mode(self, checked: bool):
        """Toggle path-only display mode"""
        if self.drawing_overlay:
            self.drawing_overlay.path_only_mode = checked
            self.drawing_overlay.update()
            print(f"DEBUG: Path-only mode set to {checked}")

    def closeEvent(self, event):
        """Handle window close event"""
        self.save_drawing_to_db()
        self.finished.emit()
        event.accept()