"""
HVAC Component Dialog - Add and edit HVAC components with noise properties
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox, QFrame,
                             QSplitter, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import json

from models import get_session
from models.hvac import HVACComponent, SilencerProduct
from data.components import STANDARD_COMPONENTS
from .silencer_filter_dialog import SilencerFilterDialog


class HVACComponentDialog(QDialog):
    """Dialog for adding and editing HVAC components"""
    
    component_saved = Signal(HVACComponent)  # Emits saved component
    
    def __init__(self, parent=None, project_id=None, drawing_id=None, component=None):
        super().__init__(parent)
        self.project_id = project_id
        self.drawing_id = drawing_id
        self.component = component  # Existing component for editing
        self.is_editing = component is not None
        self.selected_silencer_product = None
        
        self.init_ui()
        if self.is_editing:
            self.load_component_data()
        
    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit HVAC Component" if self.is_editing else "Add HVAC Component"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(600, 500)
        
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
        
        # Silencer Properties (only show for silencer type)
        self.silencer_group = QGroupBox("Silencer Properties")
        silencer_layout = QFormLayout()
        
        # Is Silencer checkbox
        self.is_silencer_cb = QCheckBox("This is a silencer component")
        self.is_silencer_cb.toggled.connect(self.on_silencer_toggled)
        silencer_layout.addRow("", self.is_silencer_cb)
        
        # Silencer type
        self.silencer_type_combo = QComboBox()
        self.silencer_type_combo.addItems(["dissipative", "reactive", "hybrid"])
        silencer_layout.addRow("Silencer Type:", self.silencer_type_combo)
        
        # Target noise reduction
        self.target_reduction_spin = QDoubleSpinBox()
        self.target_reduction_spin.setRange(0, 50)
        self.target_reduction_spin.setSuffix(" dB")
        self.target_reduction_spin.setDecimals(1)
        silencer_layout.addRow("Target Noise Reduction:", self.target_reduction_spin)
        
        # Flow rate for product selection
        self.flow_rate_spin = QDoubleSpinBox()
        self.flow_rate_spin.setRange(0, 10000)
        self.flow_rate_spin.setSuffix(" CFM")
        silencer_layout.addRow("Design Flow Rate:", self.flow_rate_spin)
        
        # Selected product display
        self.selected_product_label = QLabel("No product selected")
        self.selected_product_label.setStyleSheet("color: gray; font-style: italic;")
        silencer_layout.addRow("Selected Product:", self.selected_product_label)
        
        # Product selection buttons
        product_button_layout = QHBoxLayout()
        
        self.select_product_btn = QPushButton("Select from Database")
        self.select_product_btn.clicked.connect(self.show_silencer_selection)
        product_button_layout.addWidget(self.select_product_btn)
        
        self.clear_product_btn = QPushButton("Clear Selection")
        self.clear_product_btn.clicked.connect(self.clear_product_selection)
        self.clear_product_btn.setEnabled(False)
        product_button_layout.addWidget(self.clear_product_btn)
        
        silencer_layout.addRow("", product_button_layout)
        
        # Space constraints
        constraints_layout = QHBoxLayout()
        
        self.max_length_spin = QDoubleSpinBox()
        self.max_length_spin.setRange(0, 200)
        self.max_length_spin.setSuffix(" in")
        self.max_length_spin.setSpecialValueText("No limit")
        constraints_layout.addWidget(QLabel("Max L:"))
        constraints_layout.addWidget(self.max_length_spin)
        
        self.max_width_spin = QDoubleSpinBox()
        self.max_width_spin.setRange(0, 100)
        self.max_width_spin.setSuffix(" in")
        self.max_width_spin.setSpecialValueText("No limit")
        constraints_layout.addWidget(QLabel("W:"))
        constraints_layout.addWidget(self.max_width_spin)
        
        self.max_height_spin = QDoubleSpinBox()
        self.max_height_spin.setRange(0, 100)
        self.max_height_spin.setSuffix(" in")
        self.max_height_spin.setSpecialValueText("No limit")
        constraints_layout.addWidget(QLabel("H:"))
        constraints_layout.addWidget(self.max_height_spin)
        
        silencer_layout.addRow("Space Constraints:", constraints_layout)
        
        self.silencer_group.setLayout(silencer_layout)
        layout.addWidget(self.silencer_group)
        
        # Initially hide silencer properties
        self.silencer_group.setVisible(False)
        
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
        
        # Auto-enable silencer properties if component is a silencer
        if component_type == 'silencer':
            self.is_silencer_cb.setChecked(True)
        else:
            self.is_silencer_cb.setChecked(False)
    
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
        
        # Load silencer properties
        if hasattr(self.component, 'is_silencer') and self.component.is_silencer:
            self.is_silencer_cb.setChecked(True)
            
            if self.component.silencer_type:
                index = self.silencer_type_combo.findText(self.component.silencer_type)
                if index >= 0:
                    self.silencer_type_combo.setCurrentIndex(index)
            
            if self.component.target_noise_reduction:
                self.target_reduction_spin.setValue(self.component.target_noise_reduction)
            
            # Load space constraints from JSON
            if self.component.space_constraints:
                try:
                    constraints = json.loads(self.component.space_constraints)
                    if 'max_length' in constraints:
                        self.max_length_spin.setValue(constraints['max_length'])
                    if 'max_width' in constraints:
                        self.max_width_spin.setValue(constraints['max_width'])
                    if 'max_height' in constraints:
                        self.max_height_spin.setValue(constraints['max_height'])
                except json.JSONDecodeError:
                    pass
            
            # Load frequency requirements and show flow rate
            if self.component.frequency_requirements:
                try:
                    freq_req = json.loads(self.component.frequency_requirements)
                    if 'flow_rate' in freq_req:
                        self.flow_rate_spin.setValue(freq_req['flow_rate'])
                except json.JSONDecodeError:
                    pass
            
            # Load selected product
            if self.component.selected_product_id:
                session = get_session()
                try:
                    product = session.query(SilencerProduct).filter_by(
                        id=self.component.selected_product_id
                    ).first()
                    if product:
                        self.selected_silencer_product = product
                        self.update_selected_product_display()
                finally:
                    session.close()
    
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
                
                # Update silencer properties
                self.component.is_silencer = self.is_silencer_cb.isChecked()
                if self.component.is_silencer:
                    self.component.silencer_type = self.silencer_type_combo.currentText()
                    self.component.target_noise_reduction = self.target_reduction_spin.value()
                    
                    # Save space constraints as JSON
                    constraints = {}
                    if self.max_length_spin.value() > 0:
                        constraints['max_length'] = self.max_length_spin.value()
                    if self.max_width_spin.value() > 0:
                        constraints['max_width'] = self.max_width_spin.value()
                    if self.max_height_spin.value() > 0:
                        constraints['max_height'] = self.max_height_spin.value()
                    self.component.space_constraints = json.dumps(constraints) if constraints else None
                    
                    # Save frequency requirements (including flow rate)
                    freq_req = {}
                    if self.flow_rate_spin.value() > 0:
                        freq_req['flow_rate'] = self.flow_rate_spin.value()
                    self.component.frequency_requirements = json.dumps(freq_req) if freq_req else None
                    
                    # Save selected product
                    self.component.selected_product_id = (
                        self.selected_silencer_product.id if self.selected_silencer_product else None
                    )
                else:
                    # Clear silencer properties if not a silencer
                    self.component.silencer_type = None
                    self.component.target_noise_reduction = None
                    self.component.space_constraints = None
                    self.component.frequency_requirements = None
                    self.component.selected_product_id = None
                
                session.commit()
                component = self.component
            else:
                # Create new component
                # Prepare silencer properties
                is_silencer = self.is_silencer_cb.isChecked()
                silencer_type = self.silencer_type_combo.currentText() if is_silencer else None
                target_reduction = self.target_reduction_spin.value() if is_silencer else None
                
                # Prepare space constraints
                constraints = None
                if is_silencer:
                    constraint_dict = {}
                    if self.max_length_spin.value() > 0:
                        constraint_dict['max_length'] = self.max_length_spin.value()
                    if self.max_width_spin.value() > 0:
                        constraint_dict['max_width'] = self.max_width_spin.value()
                    if self.max_height_spin.value() > 0:
                        constraint_dict['max_height'] = self.max_height_spin.value()
                    constraints = json.dumps(constraint_dict) if constraint_dict else None
                
                # Prepare frequency requirements
                freq_req = None
                if is_silencer:
                    freq_dict = {}
                    if self.flow_rate_spin.value() > 0:
                        freq_dict['flow_rate'] = self.flow_rate_spin.value()
                    freq_req = json.dumps(freq_dict) if freq_dict else None
                
                component = HVACComponent(
                    project_id=self.project_id,
                    drawing_id=self.drawing_id,
                    name=name,
                    component_type=self.type_combo.currentText(),
                    x_position=self.x_spin.value(),
                    y_position=self.y_spin.value(),
                    noise_level=self.noise_spin.value(),
                    is_silencer=is_silencer,
                    silencer_type=silencer_type,
                    target_noise_reduction=target_reduction,
                    space_constraints=constraints,
                    frequency_requirements=freq_req,
                    selected_product_id=self.selected_silencer_product.id if self.selected_silencer_product else None
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
    
    def on_silencer_toggled(self, checked):
        """Handle silencer checkbox toggle"""
        self.silencer_group.setVisible(checked)
        
        if checked:
            # Set component type to silencer if not already
            if self.type_combo.currentText() != 'silencer':
                silencer_index = self.type_combo.findText('silencer')
                if silencer_index >= 0:
                    self.type_combo.setCurrentIndex(silencer_index)
        else:
            # Clear product selection when disabling silencer mode
            self.selected_silencer_product = None
            self.update_selected_product_display()
    
    def show_silencer_selection(self):
        """Show silencer product selection dialog"""
        # Prepare noise requirements
        noise_requirements = {
            'flow_rate': self.flow_rate_spin.value() if self.flow_rate_spin.value() > 0 else None
        }
        
        if self.target_reduction_spin.value() > 0:
            # Assume target reduction applies primarily to mid-frequency range
            noise_requirements['insertion_loss_500'] = self.target_reduction_spin.value()
            noise_requirements['insertion_loss_1000'] = self.target_reduction_spin.value()
        
        # Prepare space constraints
        space_constraints = {}
        if self.max_length_spin.value() > 0:
            space_constraints['max_length'] = self.max_length_spin.value()
        if self.max_width_spin.value() > 0:
            space_constraints['max_width'] = self.max_width_spin.value()
        if self.max_height_spin.value() > 0:
            space_constraints['max_height'] = self.max_height_spin.value()
        
        # Show filter dialog
        dialog = SilencerFilterDialog(
            noise_requirements=noise_requirements,
            space_constraints=space_constraints,
            parent=self
        )
        
        # Connect the product selection signal
        dialog.product_selected.connect(self.on_product_selected)
        
        dialog.exec()
    
    def on_product_selected(self, product):
        """Handle product selection from filter dialog"""
        self.selected_silencer_product = product
        self.configure_silencer_from_product(product)
        self.update_selected_product_display()
    
    def configure_silencer_from_product(self, product):
        """Configure silencer component from selected product"""
        if not product:
            return
        
        # Update component name if not manually set
        suggested_name = f"{product.manufacturer} {product.model_number}"
        if not self.name_edit.text() or self.name_edit.text().endswith('-1'):
            self.name_edit.setText(suggested_name)
        
        # Set silencer type
        type_index = self.silencer_type_combo.findText(product.silencer_type)
        if type_index >= 0:
            self.silencer_type_combo.setCurrentIndex(type_index)
        
        # Update space constraints if product dimensions are available
        if product.length:
            self.max_length_spin.setValue(product.length)
        if product.width:
            self.max_width_spin.setValue(product.width)
        if product.height:
            self.max_height_spin.setValue(product.height)
        
        # Set a reasonable target based on product performance (500Hz as representative)
        if product.insertion_loss_500:
            self.target_reduction_spin.setValue(product.insertion_loss_500)
        
        # Set flow rate to middle of product range
        if product.flow_rate_min and product.flow_rate_max:
            mid_flow = (product.flow_rate_min + product.flow_rate_max) / 2
            self.flow_rate_spin.setValue(mid_flow)
    
    def update_selected_product_display(self):
        """Update the selected product display"""
        if self.selected_silencer_product:
            product = self.selected_silencer_product
            display_text = f"{product.manufacturer} {product.model_number}"
            self.selected_product_label.setText(display_text)
            self.selected_product_label.setStyleSheet("color: black; font-weight: bold;")
            self.clear_product_btn.setEnabled(True)
        else:
            self.selected_product_label.setText("No product selected")
            self.selected_product_label.setStyleSheet("color: gray; font-style: italic;")
            self.clear_product_btn.setEnabled(False)
    
    def clear_product_selection(self):
        """Clear the selected product"""
        self.selected_silencer_product = None
        self.update_selected_product_display()
    
    def get_noise_requirements(self):
        """Get noise requirements for silencer selection"""
        requirements = {}
        
        if self.target_reduction_spin.value() > 0:
            target = self.target_reduction_spin.value()
            # Apply target to key frequency bands
            requirements['insertion_loss_250'] = target * 0.8
            requirements['insertion_loss_500'] = target
            requirements['insertion_loss_1000'] = target
            requirements['insertion_loss_2000'] = target * 0.9
        
        if self.flow_rate_spin.value() > 0:
            requirements['flow_rate'] = self.flow_rate_spin.value()
        
        return requirements
    
    def get_space_constraints(self):
        """Get space constraints for silencer selection"""
        constraints = {}
        
        if self.max_length_spin.value() > 0:
            constraints['max_length'] = self.max_length_spin.value()
        if self.max_width_spin.value() > 0:
            constraints['max_width'] = self.max_width_spin.value()
        if self.max_height_spin.value() > 0:
            constraints['max_height'] = self.max_height_spin.value()
        
        return constraints


# Convenience function to show dialog
def show_hvac_component_dialog(parent=None, project_id=None, drawing_id=None, component=None):
    """Show HVAC component dialog"""
    dialog = HVACComponentDialog(parent, project_id, drawing_id, component)
    return dialog.exec() 