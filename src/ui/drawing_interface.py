"""
Drawing Interface - PDF viewer with drawing overlay tools
"""

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QToolBar, QAction, QButtonGroup, QPushButton, 
                             QLabel, QComboBox, QLineEdit, QGroupBox, 
                             QListWidget, QMessageBox, QFileDialog, QSplitter,
                             QFrame, QSpinBox)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from models import get_session, Drawing, Project, Space, RoomBoundary, DrawingElementManager
from drawing import PDFViewer, DrawingOverlay, ScaleManager, ToolType
from ui.dialogs.scale_dialog import ScaleDialog
from ui.dialogs.room_properties import RoomPropertiesDialog
from data import STANDARD_COMPONENTS
from calculations import RT60Calculator


class DrawingInterface(QMainWindow):
    """Drawing interface for PDF viewing and drawing tools"""
    
    # Signals
    finished = pyqtSignal()
    
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
        dialog.exec_()
        
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
        
        from PyQt5.QtWidgets import QMenu
        
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
            dialog.exec_()
            
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
            
    def closeEvent(self, event):
        """Handle window close event"""
        self.save_drawing_to_db()
        self.finished.emit()
        event.accept()