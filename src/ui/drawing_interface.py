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

from models import get_session, Drawing, Project
from drawing import PDFViewer, DrawingOverlay, ScaleManager, ToolType
from ui.dialogs.scale_dialog import ScaleDialog
from data import STANDARD_COMPONENTS


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
        elements_layout.addWidget(self.elements_list)
        
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
        
    def load_pdf(self):
        """Load the PDF file"""
        if self.drawing and self.drawing.file_path:
            if os.path.exists(self.drawing.file_path):
                success = self.pdf_viewer.load_pdf(self.drawing.file_path)
                if success:
                    self.update_overlay_size()
                    self.load_scale_from_drawing()
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
        
        # Add to elements list
        element_type = element_data.get('type', 'unknown')
        if element_type == 'rectangle':
            area_text = element_data.get('area_formatted', '')
            self.elements_list.addItem(f"🔲 Room - {area_text}")
        elif element_type == 'component':
            comp_type = element_data.get('component_type', 'unknown')
            self.elements_list.addItem(f"🔧 {comp_type.upper()}")
        elif element_type == 'segment':
            length_text = element_data.get('length_formatted', '')
            self.elements_list.addItem(f"━ Segment - {length_text}")
        elif element_type == 'measurement':
            length_text = element_data.get('length_formatted', '')
            self.elements_list.addItem(f"📏 Measurement - {length_text}")
            
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
        """Save drawing data to database"""
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
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not save drawing:\n{str(e)}")
            
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
        
    def closeEvent(self, event):
        """Handle window close event"""
        self.save_drawing_to_db()
        self.finished.emit()
        event.accept()