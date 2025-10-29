"""
Material Schedule Comparison Dialog - Side-by-side comparison of material schedules from different drawing sets
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QSplitter, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt

from models import get_session, MaterialSchedule
from models.drawing_sets import DrawingSet
from drawing.pdf_viewer import PDFViewer


class MaterialScheduleComparisonDialog(QDialog):
    """Dialog for comparing material schedules from two drawing sets side by side"""
    
    def __init__(self, parent=None, project_id: Optional[int] = None):
        super().__init__(parent)
        self.project_id = project_id
        
        self.setWindowTitle("Compare Material Schedules")
        self.setModal(False)  # Allow interaction with other windows
        self.resize(1400, 900)
        
        self._build_ui()
        self._load_drawing_sets()
    
    def _build_ui(self):
        """Build the comparison dialog UI"""
        layout = QVBoxLayout()
        
        # Controls section
        controls = QHBoxLayout()
        
        # Left side controls
        left_controls = QHBoxLayout()
        left_controls.addWidget(QLabel("Base Drawing Set:"))
        self.left_set_combo = QComboBox()
        self.left_set_combo.setMinimumWidth(200)
        self.left_set_combo.currentIndexChanged.connect(self._on_left_set_changed)
        left_controls.addWidget(self.left_set_combo)
        
        left_controls.addWidget(QLabel("Schedule:"))
        self.left_schedule_combo = QComboBox()
        self.left_schedule_combo.setMinimumWidth(200)
        self.left_schedule_combo.currentIndexChanged.connect(self._load_left_schedule)
        left_controls.addWidget(self.left_schedule_combo)
        left_controls.addStretch()
        
        # Right side controls
        right_controls = QHBoxLayout()
        right_controls.addWidget(QLabel("Compare Drawing Set:"))
        self.right_set_combo = QComboBox()
        self.right_set_combo.setMinimumWidth(200)
        self.right_set_combo.currentIndexChanged.connect(self._on_right_set_changed)
        right_controls.addWidget(self.right_set_combo)
        
        right_controls.addWidget(QLabel("Schedule:"))
        self.right_schedule_combo = QComboBox()
        self.right_schedule_combo.setMinimumWidth(200)
        self.right_schedule_combo.currentIndexChanged.connect(self._load_right_schedule)
        right_controls.addWidget(self.right_schedule_combo)
        right_controls.addStretch()
        
        controls.addLayout(left_controls)
        controls.addWidget(QLabel(" | "))
        controls.addLayout(right_controls)
        
        layout.addLayout(controls)
        
        # Splitter for side-by-side PDF viewers
        splitter = QSplitter(Qt.Horizontal)
        
        # Left viewer
        left_group = QGroupBox("Base Schedule")
        left_layout = QVBoxLayout()
        self.left_viewer = PDFViewer()
        left_layout.addWidget(self.left_viewer)
        left_group.setLayout(left_layout)
        splitter.addWidget(left_group)
        
        # Right viewer
        right_group = QGroupBox("Compare Schedule")
        right_layout = QVBoxLayout()
        self.right_viewer = PDFViewer()
        right_layout.addWidget(self.right_viewer)
        right_group.setLayout(right_layout)
        splitter.addWidget(right_group)
        
        # Equal split
        splitter.setSizes([700, 700])
        
        layout.addWidget(splitter, 1)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        # Sync zoom button (optional enhancement)
        self.sync_zoom_btn = QPushButton("Sync Zoom")
        self.sync_zoom_btn.setCheckable(True)
        self.sync_zoom_btn.setToolTip("Synchronize zoom levels between viewers")
        self.sync_zoom_btn.clicked.connect(self._toggle_sync_zoom)
        button_layout.addWidget(self.sync_zoom_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _load_drawing_sets(self):
        """Load drawing sets for the project"""
        try:
            session = get_session()
            drawing_sets = (
                session.query(DrawingSet)
                .filter(DrawingSet.project_id == self.project_id)
                .order_by(DrawingSet.created_date)
                .all()
            )
            
            phase_icons = {'DD': '🟦', 'SD': '🟨', 'CD': '🟥', 'Final': '🟩', 'Legacy': '⚫'}
            
            for ds in drawing_sets:
                icon = phase_icons.get(ds.phase_type, '⚪')
                display_text = f"{icon} {ds.name} ({ds.phase_type})"
                
                self.left_set_combo.addItem(display_text, userData=ds.id)
                self.right_set_combo.addItem(display_text, userData=ds.id)
            
            session.close()
            
            # Set default selections (first two different sets if available)
            if self.left_set_combo.count() > 0:
                self.left_set_combo.setCurrentIndex(0)
            if self.right_set_combo.count() > 1:
                self.right_set_combo.setCurrentIndex(1)
            
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load drawing sets:\n{e}")
    
    def _on_left_set_changed(self, _index):
        """Handle left drawing set selection change"""
        self._populate_schedules_for_set(self.left_set_combo, self.left_schedule_combo)
    
    def _on_right_set_changed(self, _index):
        """Handle right drawing set selection change"""
        self._populate_schedules_for_set(self.right_set_combo, self.right_schedule_combo)
    
    def _populate_schedules_for_set(self, set_combo: QComboBox, schedule_combo: QComboBox):
        """Populate schedule combo for a given drawing set"""
        schedule_combo.clear()
        
        if set_combo.currentIndex() < 0:
            return
        
        drawing_set_id = set_combo.currentData()
        
        try:
            session = get_session()
            schedules = (
                session.query(MaterialSchedule)
                .filter(MaterialSchedule.drawing_set_id == drawing_set_id)
                .order_by(MaterialSchedule.name)
                .all()
            )
            
            if not schedules:
                schedule_combo.addItem("(No schedules available)", userData=None)
            else:
                for ms in schedules:
                    display_text = f"{ms.name} ({ms.schedule_type})"
                    schedule_combo.addItem(display_text, userData=ms.id)
            
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load schedules:\n{e}")
    
    def _load_left_schedule(self):
        """Load the selected schedule in the left viewer"""
        self._load_schedule_in_viewer(self.left_schedule_combo, self.left_viewer)
    
    def _load_right_schedule(self):
        """Load the selected schedule in the right viewer"""
        self._load_schedule_in_viewer(self.right_schedule_combo, self.right_viewer)
    
    def _load_schedule_in_viewer(self, schedule_combo: QComboBox, viewer: PDFViewer):
        """Load a material schedule PDF in the specified viewer"""
        if schedule_combo.currentIndex() < 0:
            return
        
        schedule_id = schedule_combo.currentData()
        if schedule_id is None:
            return
        
        try:
            session = get_session()
            schedule = session.query(MaterialSchedule).filter(
                MaterialSchedule.id == schedule_id
            ).first()
            session.close()
            
            if not schedule:
                QMessageBox.warning(self, "Load Error", "Selected schedule not found.")
                return
            
            # Get the file path (prefer managed, fall back to external)
            file_path = schedule.get_display_path()
            
            if not file_path:
                QMessageBox.warning(self, "Load Error", 
                                  f"No file path available for '{schedule.name}'.")
                return
            
            # Validate file exists
            import os
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", 
                                  f"PDF file not found:\n{file_path}\n\n"
                                  "The file may have been moved or deleted.")
                return
            
            # Load in viewer
            viewer.load_pdf(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", 
                               f"Failed to load schedule:\n{e}")
    
    def _toggle_sync_zoom(self, checked):
        """Toggle synchronized zoom between viewers (optional feature)"""
        if checked:
            # Connect zoom signals (if PDFViewer supports it)
            # This is a placeholder for future enhancement
            pass
        else:
            # Disconnect zoom signals
            pass

