"""
Project Settings Dialog - Edit project properties and manage drawing sets
"""

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QComboBox,
                             QFormLayout, QMessageBox, QTabWidget, QWidget,
                             QListWidget, QListWidgetItem, QGroupBox, QCheckBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from models import get_session, Project
from models.drawing_sets import DrawingSet
from models.drawing import Drawing
from sqlalchemy.orm import selectinload


class ProjectSettingsDialog(QDialog):
    """Dialog for editing project settings and managing drawing sets"""
    
    def __init__(self, parent, project_id: int):
        super().__init__(parent)
        self.project_id = project_id
        self.project = None
        
        self.load_project()
        self.init_ui()
        self.load_drawing_sets()
        
    def load_project(self):
        """Load project from database"""
        session = get_session()
        try:
            self.project = session.query(Project).filter(Project.id == self.project_id).first()
            if not self.project:
                raise Exception(f"Project with ID {self.project_id} not found")
        finally:
            session.close()
            
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Project Settings")
        self.setModal(True)
        self.resize(700, 600)

        # Apply consistent styling
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f7f7f7;
            }
            QLabel { color: #1f1f1f; }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #ffffff;
                color: #1a1a1a;
                border: 1px solid #c9c9c9;
                border-radius: 4px;
                padding: 4px;
            }
            QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {
                color: #6b6b6b;
                background-color: #ececec;
            }
            QPushButton {
                background-color: #0d8bd6;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #0b79ba; }
            QPushButton:disabled { background-color: #a9a9a9; color: #f0f0f0; }
            QListWidget {
                background-color: #ffffff;
                color: #1a1a1a;
                border: 1px solid #c9c9c9;
            }
            QListWidget::item:selected {
                background-color: #0d8bd6;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #ffffff;
                color: #1a1a1a;
                border: 1px solid #c9c9c9;
            }
            QTableWidget::item:selected {
                background-color: #0d8bd6;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #c9c9c9;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #1f1f1f;
                padding: 8px 16px;
                border: 1px solid #c9c9c9;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #0d8bd6;
            }
            QGroupBox {
                border: 1px solid #c9c9c9;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                color: #1f1f1f;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            """
        )
        
        # Main layout
        layout = QVBoxLayout()
        
        # Create tabs
        tabs = QTabWidget()
        
        # General Settings tab
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "General Settings")
        
        # Drawing Sets tab
        drawing_sets_tab = self.create_drawing_sets_tab()
        tabs.addTab(drawing_sets_tab, "Drawing Sets")
        
        layout.addWidget(tabs)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def create_general_tab(self):
        """Create the general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Form layout for project properties
        form_layout = QFormLayout()
        
        # Project name
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.project.name or "")
        self.name_edit.setPlaceholderText("Enter project name (required)")
        form_layout.addRow("Project Name:", self.name_edit)
        
        # Project description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlainText(self.project.description or "")
        self.description_edit.setPlaceholderText("Optional project description")
        form_layout.addRow("Description:", self.description_edit)
        
        # Project location (read-only)
        self.location_label = QLabel(self.project.location or "Not specified")
        self.location_label.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("Location:", self.location_label)
        
        # Default scale
        self.scale_combo = QComboBox()
        self.scale_combo.addItems([
            "1:50", "1:100", "1:200", "1:400", "1:500", "1:1000"
        ])
        current_scale = self.project.default_scale or "1:100"
        index = self.scale_combo.findText(current_scale)
        if index >= 0:
            self.scale_combo.setCurrentIndex(index)
        form_layout.addRow("Default Scale:", self.scale_combo)
        
        # Default units
        self.units_combo = QComboBox()
        self.units_combo.addItems(["feet", "meters"])
        current_units = self.project.default_units or "feet"
        index = self.units_combo.findText(current_units)
        if index >= 0:
            self.units_combo.setCurrentIndex(index)
        form_layout.addRow("Default Units:", self.units_combo)
        
        layout.addLayout(form_layout)
        
        # Project statistics
        stats_group = QGroupBox("Project Statistics")
        stats_layout = QVBoxLayout()
        
        # Get project statistics
        session = get_session()
        try:
            from models import Drawing, Space, HVACPath, HVACComponent
            
            drawing_count = session.query(Drawing).filter(Drawing.project_id == self.project_id).count()
            space_count = session.query(Space).filter(Space.project_id == self.project_id).count()
            path_count = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).count()
            component_count = session.query(HVACComponent).filter(HVACComponent.project_id == self.project_id).count()
            drawing_set_count = session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).count()
            
            stats_text = f"""
• {drawing_count} drawing(s)
• {space_count} space(s)
• {path_count} HVAC path(s)
• {component_count} HVAC component(s)
• {drawing_set_count} drawing set(s)
            """
            
            stats_label = QLabel(stats_text)
            stats_label.setStyleSheet("color: #1f1f1f; padding: 10px;")
            stats_layout.addWidget(stats_label)
            
        finally:
            session.close()
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def create_drawing_sets_tab(self):
        """Create the drawing sets management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Drawing sets help organize drawings by design phase (DD, SD, CD, Final).")
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Drawing sets list
        self.drawing_sets_list = QListWidget()
        layout.addWidget(self.drawing_sets_list)
        
        # Drawing set management buttons
        button_layout = QHBoxLayout()
        
        add_set_btn = QPushButton("Add Drawing Set")
        add_set_btn.clicked.connect(self.add_drawing_set)
        
        edit_set_btn = QPushButton("Edit Set")
        edit_set_btn.clicked.connect(self.edit_drawing_set)
        
        remove_set_btn = QPushButton("Remove Set")
        remove_set_btn.clicked.connect(self.remove_drawing_set)
        
        set_active_btn = QPushButton("Set as Active")
        set_active_btn.clicked.connect(self.set_active_drawing_set)
        
        button_layout.addWidget(add_set_btn)
        button_layout.addWidget(edit_set_btn)
        button_layout.addWidget(remove_set_btn)
        button_layout.addWidget(set_active_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Drawing assignments table
        assignments_group = QGroupBox("Drawings in Selected Set")
        assignments_layout = QVBoxLayout()
        
        self.drawings_table = QTableWidget(0, 3)
        self.drawings_table.setHorizontalHeaderLabels(["Drawing Name", "Scale", "File Path"])
        self.drawings_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.drawings_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        header = self.drawings_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        assignments_layout.addWidget(self.drawings_table)
        
        assignments_group.setLayout(assignments_layout)
        layout.addWidget(assignments_group)
        
        # Connect selection changed signal
        self.drawing_sets_list.currentItemChanged.connect(self.on_drawing_set_selected)
        
        widget.setLayout(layout)
        return widget
        
    def load_drawing_sets(self):
        """Load and display drawing sets"""
        session = get_session()
        try:
            drawing_sets = (
                session.query(DrawingSet)
                .options(selectinload(DrawingSet.drawings))
                .filter(DrawingSet.project_id == self.project_id)
                .order_by(DrawingSet.created_date)
                .all()
            )
            
            self.drawing_sets_list.clear()
            
            for drawing_set in drawing_sets:
                drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
                active_indicator = "🟢" if drawing_set.is_active else "⚪"
                phase_colors = {
                    'DD': '🟦',
                    'SD': '🟨',
                    'CD': '🟥',
                    'Final': '🟩',
                    'Legacy': '⚫',
                    'Other': '⚪'
                }
                phase_icon = phase_colors.get(drawing_set.phase_type, '⚪')
                
                item_text = f"{active_indicator} {phase_icon} {drawing_set.name} ({drawing_set.phase_type}) - {drawing_count} drawings"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, drawing_set.id)
                
                if drawing_set.is_active:
                    item.setForeground(QColor(13, 139, 214))  # Blue color for active
                
                self.drawing_sets_list.addItem(item)
                
        finally:
            session.close()
            
    def on_drawing_set_selected(self, current, previous):
        """Handle drawing set selection change"""
        if not current:
            self.drawings_table.setRowCount(0)
            return
            
        set_id = current.data(Qt.UserRole)
        
        session = get_session()
        try:
            drawings = (
                session.query(Drawing)
                .filter(Drawing.drawing_set_id == set_id)
                .all()
            )
            
            self.drawings_table.setRowCount(len(drawings))
            
            for row, drawing in enumerate(drawings):
                name_item = QTableWidgetItem(drawing.name or "")
                scale_item = QTableWidgetItem(drawing.scale_string or "")
                path_item = QTableWidgetItem(os.path.basename(drawing.file_path) if drawing.file_path else "")
                
                self.drawings_table.setItem(row, 0, name_item)
                self.drawings_table.setItem(row, 1, scale_item)
                self.drawings_table.setItem(row, 2, path_item)
                
        finally:
            session.close()
            
    def add_drawing_set(self):
        """Add a new drawing set"""
        try:
            from ui.dialogs.add_drawing_set_dialog import AddDrawingSetDialog
            
            dialog = AddDrawingSetDialog(self, self.project_id)
            if dialog.exec() == QDialog.Accepted:
                self.load_drawing_sets()
                
        except ImportError:
            # Create inline dialog if separate dialog doesn't exist
            self.create_inline_drawing_set_dialog()
            
    def create_inline_drawing_set_dialog(self):
        """Create a simple inline dialog for adding drawing sets"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QComboBox, QTextEdit, QCheckBox, QPushButton, QFormLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Drawing Set")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., 'Design Development - Rev 2'")
        form_layout.addRow("Set Name:", name_edit)
        
        phase_combo = QComboBox()
        phase_combo.addItems(["DD", "SD", "CD", "Final", "Legacy", "Other"])
        form_layout.addRow("Phase Type:", phase_combo)
        
        description_edit = QTextEdit()
        description_edit.setMaximumHeight(80)
        description_edit.setPlaceholderText("Optional description")
        form_layout.addRow("Description:", description_edit)
        
        active_checkbox = QCheckBox("Set as active drawing set")
        form_layout.addRow("", active_checkbox)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(create_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        def create_set():
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(dialog, "Validation Error", "Please enter a name for the drawing set.")
                return
                
            session = get_session()
            try:
                # If setting as active, deactivate all others
                if active_checkbox.isChecked():
                    session.query(DrawingSet).filter(
                        DrawingSet.project_id == self.project_id
                    ).update({DrawingSet.is_active: False})
                
                new_set = DrawingSet(
                    project_id=self.project_id,
                    name=name,
                    phase_type=phase_combo.currentText(),
                    description=description_edit.toPlainText().strip(),
                    is_active=active_checkbox.isChecked()
                )
                
                session.add(new_set)
                session.commit()
                
                QMessageBox.information(dialog, "Success", f"Drawing set '{name}' created successfully.")
                dialog.accept()
                self.load_drawing_sets()
                
            except Exception as e:
                session.rollback()
                QMessageBox.critical(dialog, "Error", f"Failed to create drawing set:\n{str(e)}")
            finally:
                session.close()
        
        create_btn.clicked.connect(create_set)
        dialog.exec()
        
    def edit_drawing_set(self):
        """Edit the selected drawing set"""
        current_item = self.drawing_sets_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Edit Drawing Set", "Please select a drawing set to edit.")
            return
            
        set_id = current_item.data(Qt.UserRole)
        
        session = get_session()
        try:
            drawing_set = session.query(DrawingSet).filter(DrawingSet.id == set_id).first()
            if not drawing_set:
                QMessageBox.warning(self, "Error", "Selected drawing set not found.")
                return
                
            # Create edit dialog (similar to add dialog but populated with existing data)
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QComboBox, QTextEdit, QCheckBox, QPushButton, QFormLayout
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Drawing Set")
            dialog.setModal(True)
            dialog.resize(400, 300)
            
            layout = QVBoxLayout()
            form_layout = QFormLayout()
            
            name_edit = QLineEdit()
            name_edit.setText(drawing_set.name)
            form_layout.addRow("Set Name:", name_edit)
            
            phase_combo = QComboBox()
            phase_combo.addItems(["DD", "SD", "CD", "Final", "Legacy", "Other"])
            index = phase_combo.findText(drawing_set.phase_type)
            if index >= 0:
                phase_combo.setCurrentIndex(index)
            form_layout.addRow("Phase Type:", phase_combo)
            
            description_edit = QTextEdit()
            description_edit.setMaximumHeight(80)
            description_edit.setPlainText(drawing_set.description or "")
            form_layout.addRow("Description:", description_edit)
            
            active_checkbox = QCheckBox("Set as active drawing set")
            active_checkbox.setChecked(drawing_set.is_active)
            form_layout.addRow("", active_checkbox)
            
            layout.addLayout(form_layout)
            
            # Buttons
            button_layout = QHBoxLayout()
            save_btn = QPushButton("Save")
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            
            button_layout.addStretch()
            button_layout.addWidget(save_btn)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            def save_changes():
                name = name_edit.text().strip()
                if not name:
                    QMessageBox.warning(dialog, "Validation Error", "Please enter a name for the drawing set.")
                    return
                    
                try:
                    # If setting as active, deactivate all others
                    if active_checkbox.isChecked() and not drawing_set.is_active:
                        session.query(DrawingSet).filter(
                            DrawingSet.project_id == self.project_id
                        ).update({DrawingSet.is_active: False})
                    
                    drawing_set.name = name
                    drawing_set.phase_type = phase_combo.currentText()
                    drawing_set.description = description_edit.toPlainText().strip()
                    drawing_set.is_active = active_checkbox.isChecked()
                    
                    session.commit()
                    
                    QMessageBox.information(dialog, "Success", f"Drawing set '{name}' updated successfully.")
                    dialog.accept()
                    self.load_drawing_sets()
                    
                except Exception as e:
                    session.rollback()
                    QMessageBox.critical(dialog, "Error", f"Failed to update drawing set:\n{str(e)}")
            
            save_btn.clicked.connect(save_changes)
            dialog.exec()
            
        finally:
            session.close()
            
    def remove_drawing_set(self):
        """Remove the selected drawing set"""
        current_item = self.drawing_sets_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Remove Drawing Set", "Please select a drawing set to remove.")
            return
            
        set_id = current_item.data(Qt.UserRole)
        
        session = get_session()
        try:
            drawing_set = session.query(DrawingSet).filter(DrawingSet.id == set_id).first()
            if not drawing_set:
                QMessageBox.warning(self, "Error", "Selected drawing set not found.")
                return
                
            # Count drawings in this set
            drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
            
            confirm_msg = f"Remove drawing set '{drawing_set.name}'?\n\n"
            if drawing_count > 0:
                confirm_msg += f"This set contains {drawing_count} drawing(s).\n"
                confirm_msg += "The drawings will NOT be deleted, only unassigned from this set."
            
            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                confirm_msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Unassign drawings from this set
                session.query(Drawing).filter(
                    Drawing.drawing_set_id == set_id
                ).update({Drawing.drawing_set_id: None})
                
                # Delete the drawing set
                session.delete(drawing_set)
                session.commit()
                
                QMessageBox.information(self, "Success", f"Drawing set '{drawing_set.name}' removed.")
                self.load_drawing_sets()
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to remove drawing set:\n{str(e)}")
        finally:
            session.close()
            
    def set_active_drawing_set(self):
        """Set the selected drawing set as active"""
        current_item = self.drawing_sets_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Set Active", "Please select a drawing set.")
            return
            
        set_id = current_item.data(Qt.UserRole)
        
        session = get_session()
        try:
            # Deactivate all drawing sets
            session.query(DrawingSet).filter(
                DrawingSet.project_id == self.project_id
            ).update({DrawingSet.is_active: False})
            
            # Activate the selected set
            drawing_set = session.query(DrawingSet).filter(DrawingSet.id == set_id).first()
            if drawing_set:
                drawing_set.is_active = True
                session.commit()
                
                QMessageBox.information(self, "Success", f"'{drawing_set.name}' is now the active drawing set.")
                self.load_drawing_sets()
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to set active drawing set:\n{str(e)}")
        finally:
            session.close()
            
    def save_changes(self):
        """Save all changes to the project"""
        name = self.name_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Project name is required.")
            self.name_edit.setFocus()
            return
            
        try:
            session = get_session()
            
            # Reload project to avoid detached instance issues
            project = session.query(Project).filter(Project.id == self.project_id).first()
            
            if not project:
                QMessageBox.critical(self, "Error", "Project not found.")
                session.close()
                return
            
            # Update project properties
            project.name = name
            project.description = self.description_edit.toPlainText().strip()
            project.default_scale = self.scale_combo.currentText()
            project.default_units = self.units_combo.currentText()
            
            session.commit()
            session.close()
            
            QMessageBox.information(self, "Success", "Project settings saved successfully.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project settings:\n{str(e)}")

