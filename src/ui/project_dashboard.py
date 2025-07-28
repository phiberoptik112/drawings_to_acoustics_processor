"""
Project Dashboard - Main project management interface
"""

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QListWidgetItem,
                             QTabWidget, QMenuBar, QStatusBar, QMessageBox,
                             QFileDialog, QSplitter, QTextEdit, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

from models import get_session, Project, Drawing, Space, HVACPath
from ui.drawing_interface import DrawingInterface


class ProjectDashboard(QMainWindow):
    """Main project dashboard window"""
    
    finished = pyqtSignal()
    
    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.project = None
        self.drawing_interface = None
        
        self.load_project()
        self.init_ui()
        self.refresh_all_data()
        
    def load_project(self):
        """Load project from database"""
        try:
            session = get_session()
            self.project = session.query(Project).filter(Project.id == self.project_id).first()
            session.close()
            
            if not self.project:
                raise Exception(f"Project with ID {self.project_id} not found")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{str(e)}")
            self.close()
            
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"Project: {self.project.name}")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Project info header
        self.create_project_header(main_layout)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - project elements
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - details and info
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([800, 400])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Create status bar
        self.create_status_bar()
        
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('Save Project', self.save_project)
        file_menu.addSeparator()
        file_menu.addAction('Export Results', self.export_results)
        file_menu.addSeparator()
        file_menu.addAction('Close Project', self.close)
        
        # Project menu
        project_menu = menubar.addMenu('Project')
        project_menu.addAction('Project Settings', self.project_settings)
        project_menu.addAction('Import Drawing', self.import_drawing)
        
        # Drawings menu
        drawings_menu = menubar.addMenu('Drawings')
        drawings_menu.addAction('Open Drawing', self.open_drawing)
        drawings_menu.addAction('Remove Drawing', self.remove_drawing)
        
        # Calculations menu
        calc_menu = menubar.addMenu('Calculations')
        calc_menu.addAction('Calculate All RT60', self.calculate_all_rt60)
        calc_menu.addAction('Calculate All Noise', self.calculate_all_noise)
        
        # Reports menu
        reports_menu = menubar.addMenu('Reports')
        reports_menu.addAction('Project Summary', self.show_project_summary)
        reports_menu.addAction('Export to Excel', self.export_to_excel)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        help_menu.addAction('About', self.show_about)
        
    def create_project_header(self, layout):
        """Create project information header"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        
        # Project title and info
        title_label = QLabel(self.project.name)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        
        description_label = QLabel(self.project.description or "No description")
        description_label.setStyleSheet("color: #7f8c8d; margin: 10px;")
        
        info_layout = QVBoxLayout()
        info_layout.addWidget(title_label)
        info_layout.addWidget(description_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
        
    def create_left_panel(self):
        """Create the left panel with project elements"""
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Create tabs for different element types
        tabs = QTabWidget()
        
        # Drawings tab
        drawings_tab = self.create_drawings_tab()
        tabs.addTab(drawings_tab, "Drawings")
        
        # Spaces tab
        spaces_tab = self.create_spaces_tab()
        tabs.addTab(spaces_tab, "Spaces")
        
        # HVAC Paths tab
        hvac_tab = self.create_hvac_tab()
        tabs.addTab(hvac_tab, "HVAC Paths")
        
        left_layout.addWidget(tabs)
        left_widget.setLayout(left_layout)
        
        return left_widget
        
    def create_drawings_tab(self):
        """Create the drawings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Drawings list
        self.drawings_list = QListWidget()
        self.drawings_list.itemDoubleClicked.connect(self.open_selected_drawing)
        layout.addWidget(self.drawings_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import Drawing")
        import_btn.clicked.connect(self.import_drawing)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_drawing)
        
        button_layout.addWidget(import_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        widget.setLayout(layout)
        
        return widget
        
    def create_spaces_tab(self):
        """Create the spaces tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Spaces list
        self.spaces_list = QListWidget()
        layout.addWidget(self.spaces_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        new_space_btn = QPushButton("New Space")
        new_space_btn.clicked.connect(self.new_space)
        
        edit_space_btn = QPushButton("Edit Properties")
        edit_space_btn.clicked.connect(self.edit_space)
        
        duplicate_btn = QPushButton("Duplicate")
        duplicate_btn.clicked.connect(self.duplicate_space)
        
        button_layout.addWidget(new_space_btn)
        button_layout.addWidget(edit_space_btn)
        button_layout.addWidget(duplicate_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        widget.setLayout(layout)
        
        return widget
        
    def create_hvac_tab(self):
        """Create the HVAC paths tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # HVAC paths list
        self.hvac_list = QListWidget()
        layout.addWidget(self.hvac_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        new_path_btn = QPushButton("New Path")
        new_path_btn.clicked.connect(self.new_hvac_path)
        
        edit_path_btn = QPushButton("Edit Path")
        edit_path_btn.clicked.connect(self.edit_hvac_path)
        
        button_layout.addWidget(new_path_btn)
        button_layout.addWidget(edit_path_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        widget.setLayout(layout)
        
        return widget
        
    def create_right_panel(self):
        """Create the right panel with details and results"""
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Analysis status group
        status_group = QGroupBox("Analysis Status")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)
        
        # Component library group
        library_group = QGroupBox("Component Library")
        library_layout = QVBoxLayout()
        
        self.library_list = QListWidget()
        library_layout.addWidget(self.library_list)
        
        library_button_layout = QHBoxLayout()
        add_component_btn = QPushButton("Add Component")
        edit_library_btn = QPushButton("Edit Library")
        
        library_button_layout.addWidget(add_component_btn)
        library_button_layout.addWidget(edit_library_btn)
        
        library_layout.addLayout(library_button_layout)
        library_group.setLayout(library_layout)
        right_layout.addWidget(library_group)
        
        right_widget.setLayout(right_layout)
        
        return right_widget
        
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add status information
        self.update_status_bar()
        
    def refresh_all_data(self):
        """Refresh all data displays"""
        self.refresh_drawings()
        self.refresh_spaces()
        self.refresh_hvac_paths()
        self.refresh_component_library()
        self.update_analysis_status()
        self.update_status_bar()
        
    def refresh_drawings(self):
        """Refresh the drawings list"""
        try:
            session = get_session()
            drawings = session.query(Drawing).filter(Drawing.project_id == self.project_id).all()
            
            self.drawings_list.clear()
            for drawing in drawings:
                item_text = f"📄 {drawing.name}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, drawing.id)
                self.drawings_list.addItem(item)
                
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load drawings:\n{str(e)}")
            
    def refresh_spaces(self):
        """Refresh the spaces list"""
        try:
            session = get_session()
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            
            self.spaces_list.clear()
            for space in spaces:
                # Show analysis status with emoji
                status_icon = "✅" if space.calculated_rt60 else "❌"
                item_text = f"🏢 {space.name} {status_icon}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, space.id)
                self.spaces_list.addItem(item)
                
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load spaces:\n{str(e)}")
            
    def refresh_hvac_paths(self):
        """Refresh the HVAC paths list"""
        try:
            session = get_session()
            paths = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).all()
            
            self.hvac_list.clear()
            for path in paths:
                item_text = f"🔀 {path.name} ({path.path_type})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, path.id)
                self.hvac_list.addItem(item)
                
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load HVAC paths:\n{str(e)}")
            
    def refresh_component_library(self):
        """Refresh the component library display"""
        from data import STANDARD_COMPONENTS, STANDARD_MATERIALS
        
        self.library_list.clear()
        
        # Add HVAC components
        self.library_list.addItem("🔧 HVAC Components:")
        for key, component in STANDARD_COMPONENTS.items():
            item_text = f"  • {component['name']}"
            self.library_list.addItem(item_text)
            
        # Add acoustic materials
        self.library_list.addItem("🎵 Acoustic Materials:")
        material_count = len(STANDARD_MATERIALS)
        self.library_list.addItem(f"  • {material_count} standard materials")
        
    def update_analysis_status(self):
        """Update the analysis status display"""
        try:
            session = get_session()
            
            # Count spaces and their analysis status
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            total_spaces = len(spaces)
            analyzed_spaces = len([s for s in spaces if s.calculated_rt60])
            
            # Count HVAC paths
            paths = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).all()
            total_paths = len(paths)
            
            status_text = f"Analysis Status:\n\n"
            status_text += f"Spaces: {analyzed_spaces}/{total_spaces} analyzed\n"
            status_text += f"HVAC Paths: {total_paths} created\n\n"
            
            if analyzed_spaces < total_spaces:
                status_text += "⚠️ Some spaces need RT60 analysis\n"
            else:
                status_text += "✅ All spaces analyzed\n"
                
            self.status_text.setText(status_text)
            session.close()
            
        except Exception as e:
            self.status_text.setText(f"Error loading status: {str(e)}")
            
    def update_status_bar(self):
        """Update the status bar"""
        try:
            session = get_session()
            
            drawing_count = session.query(Drawing).filter(Drawing.project_id == self.project_id).count()
            space_count = session.query(Space).filter(Space.project_id == self.project_id).count()
            path_count = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).count()
            
            status_text = f"Ready | Project: {self.project.name} | {drawing_count} drawings, {space_count} spaces, {path_count} paths"
            self.status_bar.showMessage(status_text)
            
            session.close()
            
        except Exception as e:
            self.status_bar.showMessage(f"Error: {str(e)}")
            
    # Slot implementations (placeholder methods)
    def import_drawing(self):
        """Import a new drawing (PDF)"""
        QMessageBox.information(self, "Import Drawing", "Drawing import will be implemented next.")
        
    def open_drawing(self):
        """Open the selected drawing"""
        self.open_selected_drawing(self.drawings_list.currentItem())
        
    def open_selected_drawing(self, item):
        """Open the selected drawing in drawing interface"""
        if item:
            drawing_id = item.data(Qt.UserRole)
            try:
                self.drawing_interface = DrawingInterface(drawing_id, self.project_id)
                self.drawing_interface.show()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open drawing:\n{str(e)}")
        
    def remove_drawing(self):
        """Remove the selected drawing"""
        QMessageBox.information(self, "Remove Drawing", "Drawing removal will be implemented.")
        
    def new_space(self):
        """Create a new space"""
        QMessageBox.information(self, "New Space", "Space creation will be implemented.")
        
    def edit_space(self):
        """Edit space properties"""
        QMessageBox.information(self, "Edit Space", "Space editing will be implemented.")
        
    def duplicate_space(self):
        """Duplicate the selected space"""
        QMessageBox.information(self, "Duplicate Space", "Space duplication will be implemented.")
        
    def new_hvac_path(self):
        """Create a new HVAC path"""
        QMessageBox.information(self, "New HVAC Path", "HVAC path creation will be implemented.")
        
    def edit_hvac_path(self):
        """Edit HVAC path properties"""
        QMessageBox.information(self, "Edit HVAC Path", "HVAC path editing will be implemented.")
        
    def save_project(self):
        """Save the current project"""
        QMessageBox.information(self, "Save Project", "Project saved successfully.")
        
    def export_results(self):
        """Export analysis results"""
        QMessageBox.information(self, "Export Results", "Results export will be implemented.")
        
    def project_settings(self):
        """Open project settings"""
        QMessageBox.information(self, "Project Settings", "Project settings will be implemented.")
        
    def calculate_all_rt60(self):
        """Calculate RT60 for all spaces"""
        QMessageBox.information(self, "Calculate RT60", "RT60 calculation will be implemented.")
        
    def calculate_all_noise(self):
        """Calculate noise for all HVAC paths"""
        QMessageBox.information(self, "Calculate Noise", "Noise calculation will be implemented.")
        
    def show_project_summary(self):
        """Show project summary report"""
        QMessageBox.information(self, "Project Summary", "Project summary will be implemented.")
        
    def export_to_excel(self):
        """Export project data to Excel"""
        QMessageBox.information(self, "Export to Excel", "Excel export will be implemented.")
        
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", "Acoustic Analysis Tool v1.0\nfor LEED Acoustic Certification")
        
    def closeEvent(self, event):
        """Handle window close event"""
        self.finished.emit()
        event.accept()