"""
Drawing Interface - PDF viewer with drawing overlay tools
"""

import os
from typing import Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QToolBar, QButtonGroup, QPushButton, 
                             QLabel, QComboBox, QLineEdit, QGroupBox, 
                             QListWidget, QMessageBox, QFileDialog, QSplitter,
                             QFrame, QSpinBox)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QFont, QAction

from models import get_session, Drawing, Project, Space, RoomBoundary, DrawingElementManager
from drawing import PDFViewer, DrawingOverlay, ScaleManager, ToolType
from ui.dialogs.scale_dialog import ScaleDialog
from ui.dialogs.room_properties import RoomPropertiesDialog
from data import STANDARD_COMPONENTS, ExcelExporter, ExportOptions, EXCEL_EXPORT_AVAILABLE
from calculations import RT60Calculator, NoiseCalculator, HVACPathCalculator


class DrawingInterface(QMainWindow):
    """Drawing interface for PDF viewing and drawing tools"""
    
    # Signals
    finished = Signal()
    
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
        
        self.load_drawing_data()
        self.init_ui()
        self.setup_connections()
        
        if self.drawing and self.drawing.file_path:
            self.load_pdf()
            
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
        edit_menu.addAction('Clear All', self.clear_all_elements)
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
        
        # Measure tool
        measure_action = QAction('📏 Measure', self)
        measure_action.setCheckable(True)
        measure_action.triggered.connect(lambda: self.set_drawing_tool(ToolType.MEASURE))
        toolbar.addAction(measure_action)
        self.tool_group.addButton(toolbar.widgetForAction(measure_action))
        
        toolbar.addSeparator()
        
        # Quick actions
        toolbar.addAction('💾 Save', self.save_drawing)
        toolbar.addAction('🗑️ Clear', self.clear_all_elements)
        
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
        self.component_combo.currentDataChanged.connect(self.component_type_changed)
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
        
        self.create_room_btn = QPushButton("Create Room")
        self.create_room_btn.clicked.connect(self.create_room_from_selected)
        self.create_room_btn.setEnabled(False)
        
        self.delete_element_btn = QPushButton("Delete")
        self.delete_element_btn.clicked.connect(self.delete_selected_element)
        self.delete_element_btn.setEnabled(False)
        
        element_actions_layout.addWidget(self.create_room_btn)
        element_actions_layout.addWidget(self.delete_element_btn)
        
        elements_layout.addLayout(element_actions_layout)
        elements_group.setLayout(elements_layout)
        layout.addWidget(elements_group)
        
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
            self.pdf_viewer.scale_changed.connect(self.pdf_zoom_changed)
            
        if self.drawing_overlay:
            self.drawing_overlay.element_created.connect(self.element_created)
            self.drawing_overlay.measurement_taken.connect(self.measurement_taken)
            
        self.scale_manager.scale_changed.connect(self.scale_updated)
        
        # Element list selection
        self.elements_list.itemSelectionChanged.connect(self.element_selected)
        
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
            
            # Update scale manager with page dimensions
            pdf_width, pdf_height = self.pdf_viewer.get_page_dimensions()
            self.scale_manager.set_page_dimensions(pdf_width, pdf_height)
            
    def load_scale_from_drawing(self):
        """Load scale information from drawing record"""
        if self.drawing and self.drawing.scale_string:
            self.scale_manager.set_scale_from_string(self.drawing.scale_string)
            
    def set_drawing_tool(self, tool_type):
        """Set the active drawing tool"""
        if self.drawing_overlay:
            self.drawing_overlay.set_tool(tool_type)
            self.mode_label.setText(f"Current Tool: {tool_type.value.title()}")
            
            # Show/hide component selection
            self.component_group.setVisible(tool_type == ToolType.COMPONENT)
            
    def component_type_changed(self, component_key):
        """Handle component type change"""
        if self.drawing_overlay and component_key:
            self.drawing_overlay.set_component_type(component_key)
            
    def pdf_coordinates_clicked(self, x, y):
        """Handle PDF coordinates clicked"""
        # Update status bar with coordinates
        real_x = self.scale_manager.pixels_to_real(x)
        real_y = self.scale_manager.pixels_to_real(y)
        
        coord_text = f"Clicked: ({x:.0f}, {y:.0f}) px = ({real_x:.1f}, {real_y:.1f}) {self.scale_manager.units}"
        self.status_bar.showMessage(coord_text, 3000)
        
    def pdf_zoom_changed(self, zoom_factor):
        """Handle PDF zoom change"""
        self.update_overlay_size()
        
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
                    self.drawing.id, self.project_id, overlay_data
                )
                
                if elements_saved > 0:
                    self.status_bar.showMessage(f"Saved {elements_saved} drawing elements", 2000)
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not save drawing:\n{str(e)}")
            
    def load_saved_elements(self):
        """Load saved drawing elements from database"""
        if not self.drawing or not self.drawing_overlay:
            return
            
        try:
            overlay_data = self.element_manager.load_elements(self.drawing.id)
            
            if any(overlay_data.values()):  # If there are any elements
                self.drawing_overlay.load_elements_data(overlay_data)
                
                # Rebuild elements list
                self.rebuild_elements_list(overlay_data)
                
                elements_count = sum(len(elements) for elements in overlay_data.values())
                self.status_bar.showMessage(f"Loaded {elements_count} saved elements", 2000)
                
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load saved elements:\n{str(e)}")
            
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
        self.set_drawing_tool(ToolType.MEASURE)
        QMessageBox.information(self, "Scale Calibration", 
                               "Use the measurement tool to measure a known distance,\nthen right-click to set the scale.")
        
    def element_selected(self):
        """Handle element list selection change"""
        current_item = self.elements_list.currentItem()
        
        if current_item:
            element_data = current_item.data(Qt.UserRole)
            element_type = element_data.get('type') if element_data else None
            
            # Enable appropriate buttons
            self.create_room_btn.setEnabled(element_type == 'rectangle')
            self.delete_element_btn.setEnabled(True)
            
            if element_type == 'rectangle':
                self.selected_rectangle = element_data
        else:
            self.create_room_btn.setEnabled(False)
            self.delete_element_btn.setEnabled(False)
            self.selected_rectangle = None
            
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
            
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Delete Element")
        delete_action.triggered.connect(lambda: self.delete_element(item))
        
        menu.exec_(self.elements_list.mapToGlobal(position))
        
    def create_room_from_selected(self):
        """Create room from selected rectangle"""
        if self.selected_rectangle:
            self.create_room_from_rectangle(self.selected_rectangle)
            
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
        try:
            session = get_session()
            
            # Create space record
            space = Space(
                project_id=self.project_id,
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
            
            # Calculate RT60
            rt60_results = self.rt60_calculator.calculate_space_rt60(space_data)
            if rt60_results and 'rt60' in rt60_results:
                space.calculated_rt60 = rt60_results['rt60']
                
            # Create room boundary record
            rectangle_data = space_data.get('rectangle_data', {})
            if rectangle_data and self.drawing:
                boundary = RoomBoundary(
                    space_id=space.id,
                    drawing_id=self.drawing.id,
                    x_position=rectangle_data.get('x', 0),
                    y_position=rectangle_data.get('y', 0),
                    width=rectangle_data.get('width', 0),
                    height=rectangle_data.get('height', 0),
                    calculated_area=rectangle_data.get('area_real', 0)
                )
                
                session.add(boundary)
                
            session.commit()
            session.close()
            
            # Update UI
            QMessageBox.information(self, "Success", 
                                   f"Space '{space_data['name']}' created successfully!\n"
                                   f"Calculated RT60: {space.calculated_rt60:.2f} seconds")
            
            # Remove rectangle from elements and add space indicator
            self.update_elements_after_space_creation(space_data['name'])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create space:\n{str(e)}")
            
    def update_elements_after_space_creation(self, space_name):
        """Update elements list after space creation"""
        # Find and update the rectangle item
        for i in range(self.elements_list.count()):
            item = self.elements_list.item(i)
            element_data = item.data(Qt.UserRole)
            
            if element_data and element_data.get('type') == 'rectangle':
                # Check if this is the rectangle we just converted
                if element_data == self.selected_rectangle:
                    # Update item text to indicate it's now a space
                    area_text = element_data.get('area_formatted', '')
                    item.setText(f"🏠 Space: {space_name} - {area_text}")
                    
                    # Update element data to mark as converted
                    element_data['converted_to_space'] = True
                    element_data['space_name'] = space_name
                    item.setData(Qt.UserRole, element_data)
                    break
                    
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
        """Create HVAC path from drawing elements and save to database"""
        try:
            # Get HVAC components and segments from drawing elements
            overlay_data = self.drawing_overlay.get_elements_data() if self.drawing_overlay else {}
            components = overlay_data.get('components', [])
            segments = overlay_data.get('segments', [])
            
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
            
            # Add drawing ID to components
            for comp in components:
                comp['drawing_id'] = self.drawing.id
            
            drawing_data = {
                'components': components,
                'segments': segments
            }
            
            # Create HVAC path in database
            hvac_path = self.hvac_path_calculator.create_hvac_path_from_drawing(
                self.project_id, drawing_data
            )
            
            if hvac_path:
                QMessageBox.information(self, "HVAC Path Created", 
                                       f"Successfully created HVAC path: {hvac_path.name}\n"
                                       f"Terminal Noise: {hvac_path.calculated_noise:.1f} dB(A)\n"
                                       f"NC Rating: NC-{hvac_path.calculated_nc}")
            else:
                QMessageBox.warning(self, "Creation Failed", "Failed to create HVAC path from drawing elements.")
                
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
        message += f"Total Attenuation: {results['total_attenuation']:.1f} dB\n"
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

    def closeEvent(self, event):
        """Handle window close event"""
        self.save_drawing_to_db()
        self.finished.emit()
        event.accept()