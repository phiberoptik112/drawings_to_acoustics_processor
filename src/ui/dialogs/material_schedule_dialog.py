"""
Material Schedule Dialog - Add/Edit material schedule PDFs associated with drawing sets
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QCheckBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

from models import get_session, MaterialSchedule
from models.drawing_sets import DrawingSet
from data.material_file_manager import (
    copy_material_schedule_to_project,
    validate_material_schedule_pdf
)


class MaterialScheduleDialog(QDialog):
    """Dialog for adding or editing a material schedule"""
    
    def __init__(self, parent=None, project_id: Optional[int] = None, 
                 project_location: Optional[str] = None, 
                 material_schedule: Optional[MaterialSchedule] = None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_location = project_location
        self.material_schedule = material_schedule
        self.is_edit_mode = material_schedule is not None
        
        self.setWindowTitle("Edit Material Schedule" if self.is_edit_mode else "Add Material Schedule")
        self.setModal(True)
        self.resize(600, 400)
        
        self._build_ui()
        
        if self.is_edit_mode:
            self._load_schedule_data()
    
    def _build_ui(self):
        """Build the dialog UI"""
        layout = QVBoxLayout()
        
        # Form for schedule properties
        form = QFormLayout()
        
        # Drawing Set selection
        self.drawing_set_combo = QComboBox()
        self.drawing_set_combo.setToolTip("Select the drawing set this material schedule belongs to")
        self._populate_drawing_sets()
        form.addRow("Drawing Set:", self.drawing_set_combo)
        
        # Schedule name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Interior Finishes Schedule")
        form.addRow("Schedule Name:", self.name_edit)
        
        # Schedule type
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "finishes",
            "materials",
            "acoustic_treatments",
            "ceiling_systems",
            "flooring",
            "wall_systems",
            "other"
        ])
        self.type_combo.setToolTip("Category of this material schedule")
        form.addRow("Schedule Type:", self.type_combo)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Optional description or notes")
        self.description_edit.setMaximumHeight(80)
        form.addRow("Description:", self.description_edit)
        
        layout.addLayout(form)
        
        # File selection section
        file_group = QVBoxLayout()
        file_label = QLabel("PDF File:")
        file_label.setStyleSheet("font-weight: bold;")
        file_group.addWidget(file_label)
        
        # File path display and browse button
        file_row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a PDF file...")
        self.file_path_edit.setReadOnly(True)
        file_row.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        
        file_group.addLayout(file_row)
        
        # Copy to project folder checkbox
        self.copy_to_project_cb = QCheckBox("Copy PDF to project materials folder")
        self.copy_to_project_cb.setChecked(True)
        self.copy_to_project_cb.setToolTip(
            "When checked, a copy of the PDF will be stored in the project folder.\n"
            "Unchecked: Only the external path will be stored (PDF must remain at original location)."
        )
        file_group.addWidget(self.copy_to_project_cb)
        
        layout.addLayout(file_group)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        save_btn.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _populate_drawing_sets(self):
        """Load drawing sets for the current project"""
        try:
            session = get_session()
            drawing_sets = (
                session.query(DrawingSet)
                .filter(DrawingSet.project_id == self.project_id)
                .order_by(DrawingSet.created_date)
                .all()
            )
            
            for ds in drawing_sets:
                phase_icons = {'DD': '🟦', 'SD': '🟨', 'CD': '🟥', 'Final': '🟩', 'Legacy': '⚫'}
                icon = phase_icons.get(ds.phase_type, '⚪')
                display_text = f"{icon} {ds.name} ({ds.phase_type})"
                self.drawing_set_combo.addItem(display_text, userData=ds.id)
            
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load drawing sets:\n{e}")
    
    def _load_schedule_data(self):
        """Load existing schedule data for editing"""
        if not self.material_schedule:
            return
        
        ms = self.material_schedule
        
        # Set drawing set
        for i in range(self.drawing_set_combo.count()):
            if self.drawing_set_combo.itemData(i) == ms.drawing_set_id:
                self.drawing_set_combo.setCurrentIndex(i)
                break
        
        # Set other fields
        self.name_edit.setText(ms.name or "")
        self.description_edit.setPlainText(ms.description or "")
        
        # Set schedule type
        idx = self.type_combo.findText(ms.schedule_type or "finishes")
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        
        # Set file path (prefer managed path)
        display_path = ms.get_display_path()
        if display_path:
            self.file_path_edit.setText(display_path)
        
        # Default to not copying if already has managed path
        if ms.managed_file_path:
            self.copy_to_project_cb.setChecked(False)
    
    def _browse_file(self):
        """Browse for PDF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Material Schedule PDF",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            # Validate the PDF
            is_valid, message = validate_material_schedule_pdf(file_path)
            if not is_valid:
                QMessageBox.warning(self, "Invalid PDF", f"Cannot use this file:\n{message}")
                return
            
            self.file_path_edit.setText(file_path)
    
    def _save(self):
        """Save the material schedule"""
        # Validate inputs
        if self.drawing_set_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validation", "Please select a drawing set.")
            return
        
        schedule_name = self.name_edit.text().strip()
        if not schedule_name:
            QMessageBox.warning(self, "Validation", "Please enter a schedule name.")
            return
        
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Validation", "Please select a PDF file.")
            return
        
        # Validate file still exists
        is_valid, message = validate_material_schedule_pdf(file_path)
        if not is_valid:
            QMessageBox.warning(self, "Invalid File", f"Selected file is not valid:\n{message}")
            return
        
        drawing_set_id = self.drawing_set_combo.currentData()
        schedule_type = self.type_combo.currentText()
        description = self.description_edit.toPlainText().strip()
        
        try:
            session = get_session()
            
            # Get drawing set for folder name
            drawing_set = session.query(DrawingSet).filter(DrawingSet.id == drawing_set_id).first()
            if not drawing_set:
                QMessageBox.critical(self, "Error", "Selected drawing set not found.")
                session.close()
                return
            
            # Handle file copying if requested
            managed_path = None
            if self.copy_to_project_cb.isChecked() and self.project_location:
                success, result = copy_material_schedule_to_project(
                    file_path,
                    self.project_location,
                    drawing_set.name,
                    target_filename=f"{schedule_name}.pdf"
                )
                
                if success:
                    managed_path = result
                else:
                    reply = QMessageBox.question(
                        self,
                        "Copy Failed",
                        f"Failed to copy file to project folder:\n{result}\n\n"
                        "Do you want to save with external path only?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        session.close()
                        return
            
            # Create or update schedule
            if self.is_edit_mode:
                ms = session.query(MaterialSchedule).filter(
                    MaterialSchedule.id == self.material_schedule.id
                ).first()
                if not ms:
                    QMessageBox.critical(self, "Error", "Material schedule not found.")
                    session.close()
                    return
            else:
                ms = MaterialSchedule()
                session.add(ms)
            
            # Set properties
            ms.drawing_set_id = drawing_set_id
            ms.name = schedule_name
            ms.description = description if description else None
            ms.schedule_type = schedule_type
            ms.file_path = file_path
            if managed_path:
                ms.managed_file_path = managed_path
            
            session.commit()
            session.close()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save material schedule:\n{e}")

