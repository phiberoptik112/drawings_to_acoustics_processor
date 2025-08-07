"""
Splash Screen - Initial application window for project selection/creation
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap

from models import initialize_database, get_session, Project
from ui.dialogs.project_dialog import ProjectDialog
from ui.project_dashboard import ProjectDashboard
from data.silencer_database import populate_silencer_database


class SplashScreen(QWidget):
    """Splash screen for project selection and creation"""
    
    def __init__(self):
        super().__init__()
        self.project_dashboard = None
        self.init_database()
        self.init_ui()
        self.load_recent_projects()
        
    def init_database(self):
        """Initialize the database connection"""
        try:
            self.db_path = initialize_database()
            
            # Populate silencer database if it's empty
            try:
                populate_silencer_database()
            except Exception as e:
                # Silencer database population is not critical, just log the error
                print(f"Warning: Failed to populate silencer database: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Database Error", 
                               f"Failed to initialize database:\n{str(e)}")
            
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Acoustic Analysis Tool")
        self.setGeometry(300, 300, 600, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
            QLabel#title {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin: 20px;
            }
            QLabel#subtitle {
                font-size: 14px;
                color: #7f8c8d;
                margin-bottom: 20px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QListWidget {
                background-color: black;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title section
        title_label = QLabel("Acoustic Analysis Tool")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("LEED Acoustic Certification Analysis")
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        
        # Recent projects section
        recent_label = QLabel("Recent Projects")
        recent_label.setFont(QFont("Arial", 14, QFont.Bold))
        recent_label.setStyleSheet("color: #2c3e50; margin-top: 10px;")
        
        self.recent_projects_list = QListWidget()
        self.recent_projects_list.setMaximumHeight(200)
        self.recent_projects_list.itemDoubleClicked.connect(self.open_selected_project)
        
        main_layout.addWidget(recent_label)
        main_layout.addWidget(self.recent_projects_list)
        
        # Buttons section
        button_layout = QHBoxLayout()
        
        self.new_project_btn = QPushButton("New Project")
        self.new_project_btn.clicked.connect(self.create_new_project)
        
        self.open_project_btn = QPushButton("Open Project")
        self.open_project_btn.clicked.connect(self.open_project)
        
        self.import_project_btn = QPushButton("Import Project")
        self.import_project_btn.clicked.connect(self.import_project)
        
        button_layout.addWidget(self.new_project_btn)
        button_layout.addWidget(self.open_project_btn)
        button_layout.addWidget(self.import_project_btn)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel(f"Database: {os.path.basename(self.db_path)}")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin-top: 10px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
        
    def load_recent_projects(self):
        """Load recent projects from database"""
        try:
            session = get_session()
            projects = session.query(Project).order_by(Project.modified_date.desc()).limit(10).all()
            
            self.recent_projects_list.clear()
            for project in projects:
                item_text = f"{project.name}\n{project.description or 'No description'}\nModified: {project.modified_date.strftime('%Y-%m-%d %H:%M')}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, project.id)
                self.recent_projects_list.addItem(item)
                
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load recent projects:\n{str(e)}")
            
    def create_new_project(self):
        """Create a new project"""
        dialog = ProjectDialog(self)
        if dialog.exec() == dialog.accepted:
            project_data = dialog.get_project_data()
            
            try:
                session = get_session()
                
                # Create new project
                project = Project(
                    name=project_data['name'],
                    description=project_data['description'],
                    location=project_data['location'],
                    default_scale=project_data['scale'],
                    default_units=project_data['units']
                )
                
                session.add(project)
                session.commit()
                
                # Open project dashboard
                self.open_project_dashboard(project.id)
                
                session.close()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project:\n{str(e)}")
                
    def open_project(self):
        """Open an existing project file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Project", 
            os.path.expanduser("~/Documents"), 
            "Database Files (*.db);;All Files (*)"
        )
        
        if file_path:
            try:
                # Initialize database with selected file
                initialize_database(file_path)
                self.load_recent_projects()
                self.status_label.setText(f"Database: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project:\n{str(e)}")
                
    def import_project(self):
        """Import project from another database"""
        QMessageBox.information(self, "Import Project", "Import functionality will be implemented in a future version.")
        
    def open_selected_project(self, item):
        """Open the selected project from the list"""
        project_id = item.data(Qt.UserRole)
        self.open_project_dashboard(project_id)
        
    def open_project_dashboard(self, project_id):
        """Open the project dashboard for the specified project"""
        try:
            self.project_dashboard = ProjectDashboard(project_id)
            self.project_dashboard.show()
            self.hide()
            
            # Connect signal to show splash when dashboard closes
            self.project_dashboard.finished.connect(self.show_splash)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open project dashboard:\n{str(e)}")
            
    def show_splash(self):
        """Show splash screen again when dashboard closes"""
        self.load_recent_projects()  # Refresh the project list
        self.show()
        
    def closeEvent(self, event):
        """Handle application close event"""
        from models import close_database
        close_database()
        event.accept()