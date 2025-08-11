"""
HVAC Component Dialog - Add and edit HVAC components with noise properties
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import get_session
from models.hvac import HVACComponent
from data.components import STANDARD_COMPONENTS


class HVACComponentDialog(QDialog):
    """Dialog for adding and editing HVAC components"""
    
    component_saved = Signal(HVACComponent)  # Emits saved component
    
    def __init__(self, parent=None, project_id=None, drawing_id=None, component=None):
        super().__init__(parent)
        self.project_id = project_id
        self.drawing_id = drawing_id
        self.component = component  # Existing component for editing
        self.is_editing = component is not None
        
        self.init_ui()
        if self.is_editing:
            self.load_component_data()
        
    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit HVAC Component" if self.is_editing else "Add HVAC Component"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel(title)
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Component Information
        info_group = QGroupBox("Component Information")
        info_layout = QFormLayout()
        
        # Component name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., AHU-1, VAV-Box-A, Diffuser-101")
        info_layout.addRow("Component Name:", self.name_edit)
        
        # Component type
        self.type_combo = QComboBox()
        component_types = list(STANDARD_COMPONENTS.keys())
        self.type_combo.addItems(component_types)
        self.type_combo.currentTextChanged.connect(self.on_component_type_changed)
        info_layout.addRow("Component Type:", self.type_combo)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Position Information
        position_group = QGroupBox("Position on Drawing")
        position_layout = QFormLayout()
        
        # X position
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 10000)
        self.x_spin.setSuffix(" px")
        position_layout.addRow("X Position:", self.x_spin)
        
        # Y position
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 10000)
        self.y_spin.setSuffix(" px")
        position_layout.addRow("Y Position:", self.y_spin)
        
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        # Acoustic Properties
        acoustic_group = QGroupBox("Acoustic Properties")
        acoustic_layout = QFormLayout()
        
        # Noise level
        self.noise_spin = QDoubleSpinBox()
        self.noise_spin.setRange(0, 120)
        self.noise_spin.setSuffix(" dB(A)")
        self.noise_spin.setDecimals(1)
        acoustic_layout.addRow("Base Noise Level:", self.noise_spin)
        
        # Use standard checkbox
        self.use_standard_cb = QCheckBox("Use standard noise level for component type")
        self.use_standard_cb.setChecked(True)
        self.use_standard_cb.toggled.connect(self.on_use_standard_toggled)
        acoustic_layout.addRow("", self.use_standard_cb)
        
        acoustic_group.setLayout(acoustic_layout)
        layout.addWidget(acoustic_group)
        
        # Component Details
        details_group = QGroupBox("Component Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setPlaceholderText("Additional details about this component...")
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if self.is_editing:
            self.delete_btn = QPushButton("Delete Component")
            self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            self.delete_btn.clicked.connect(self.delete_component)
            button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        save_text = "Update Component" if self.is_editing else "Add Component"
        self.save_btn = QPushButton(save_text)
        self.save_btn.clicked.connect(self.save_component)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Initialize with first component type
        self.on_component_type_changed(self.type_combo.currentText())
        
    def on_component_type_changed(self, component_type):
        """Handle component type change"""
        if component_type in STANDARD_COMPONENTS:
            standard_noise = STANDARD_COMPONENTS[component_type].get('noise_level', 50.0)
            self.noise_spin.setValue(standard_noise)
            
            # Update name suggestion
            if not self.name_edit.text():
                self.name_edit.setText(f"{component_type.upper()}-1")
    
    def on_use_standard_toggled(self, checked):
        """Handle use standard checkbox toggle"""
        if checked:
            component_type = self.type_combo.currentText()
            if component_type in STANDARD_COMPONENTS:
                standard_noise = STANDARD_COMPONENTS[component_type].get('noise_level', 50.0)
                self.noise_spin.setValue(standard_noise)
            self.noise_spin.setEnabled(False)
        else:
            self.noise_spin.setEnabled(True)
    
    def load_component_data(self):
        """Load existing component data for editing"""
        if not self.component:
            return
            
        self.name_edit.setText(self.component.name)
        
        # Set component type
        index = self.type_combo.findText(self.component.component_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # Set position
        self.x_spin.setValue(int(self.component.x_position))
        self.y_spin.setValue(int(self.component.y_position))
        
        # Set noise level
        if self.component.noise_level is not None:
            self.noise_spin.setValue(self.component.noise_level)
            self.use_standard_cb.setChecked(False)
            self.noise_spin.setEnabled(True)
    
    def save_component(self):
        """Save the HVAC component"""
        # Validate inputs
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a component name.")
            return
        
        try:
            session = get_session()
            
            if self.is_editing:
                # Update existing component
                self.component.name = name
                self.component.component_type = self.type_combo.currentText()
                self.component.x_position = self.x_spin.value()
                self.component.y_position = self.y_spin.value()
                self.component.noise_level = self.noise_spin.value()
                
                session.commit()
                component = self.component
            else:
                # Create new component
                component = HVACComponent(
                    project_id=self.project_id,
                    drawing_id=self.drawing_id,
                    name=name,
                    component_type=self.type_combo.currentText(),
                    x_position=self.x_spin.value(),
                    y_position=self.y_spin.value(),
                    noise_level=self.noise_spin.value()
                )
                
                session.add(component)
                session.commit()
            
            session.close()
            
            self.component_saved.emit(component)
            self.accept()
            
        except Exception as e:
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Error", f"Failed to save component:\n{str(e)}")
    
    def delete_component(self):
        """Delete the HVAC component"""
        if not self.is_editing or not self.component:
            return
            
        reply = QMessageBox.question(
            self, "Delete Component",
            f"Are you sure you want to delete '{self.component.name}'?\n\n"
            "This will also remove any segments connected to this component.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                session.delete(self.component)
                session.commit()
                session.close()
                
                self.accept()
                
            except Exception as e:
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Error", f"Failed to delete component:\n{str(e)}")


# Convenience function to show dialog
def show_hvac_component_dialog(parent=None, project_id=None, drawing_id=None, component=None):
    """Show HVAC component dialog"""
    dialog = HVACComponentDialog(parent, project_id, drawing_id, component)
    return dialog.exec() 