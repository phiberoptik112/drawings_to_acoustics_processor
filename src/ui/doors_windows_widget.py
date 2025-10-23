"""
Doors & Windows Widget - Dedicated widget for managing door and window elements
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QGroupBox, QPushButton,
                             QDialog, QFormLayout, QComboBox, QLineEdit, 
                             QDoubleSpinBox, QSpinBox, QDialogButtonBox,
                             QMessageBox, QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from typing import Dict, List, Optional
import uuid

try:
    from ..data.enhanced_materials import ENHANCED_MATERIALS
    from ..data.materials import STANDARD_MATERIALS
except ImportError:
    try:
        from data.enhanced_materials import ENHANCED_MATERIALS
        from data.materials import STANDARD_MATERIALS
    except ImportError:
        import sys
        import os
        # Add src directory to path for testing
        current_dir = os.path.dirname(__file__)
        src_dir = os.path.dirname(current_dir)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from data.enhanced_materials import ENHANCED_MATERIALS
        from data.materials import STANDARD_MATERIALS


class DoorWindowEditDialog(QDialog):
    """Dialog for adding/editing door and window elements"""
    
    def __init__(self, parent=None, element_type='door', element_data=None):
        super().__init__(parent)
        self.element_type = element_type
        self.element_data = element_data or {}
        self.is_editing = element_data is not None
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """Initialize the dialog UI"""
        title = f"{'Edit' if self.is_editing else 'Add'} {self.element_type.title()}"
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 350)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Type selection
        self.type_combo = QComboBox()
        self.populate_type_combo()
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form_layout.addRow("Type:", self.type_combo)
        
        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText(f"Enter {self.element_type} description")
        form_layout.addRow("Description:", self.description_edit)
        
        # Dimensions
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.1, 50.0)
        self.width_spin.setValue(3.0 if self.element_type == 'door' else 4.0)
        self.width_spin.setSuffix(" ft")
        self.width_spin.setDecimals(1)
        self.width_spin.valueChanged.connect(self.calculate_area)
        form_layout.addRow("Width:", self.width_spin)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.1, 20.0)
        self.height_spin.setValue(8.0 if self.element_type == 'door' else 3.0)
        self.height_spin.setSuffix(" ft")
        self.height_spin.setDecimals(1)
        self.height_spin.valueChanged.connect(self.calculate_area)
        form_layout.addRow("Height:", self.height_spin)
        
        # Quantity
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 99)
        self.quantity_spin.setValue(1)
        self.quantity_spin.valueChanged.connect(self.calculate_area)
        form_layout.addRow("Quantity:", self.quantity_spin)
        
        # Calculated area (read-only)
        self.area_label = QLabel("0.0 sf")
        self.area_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        form_layout.addRow("Total Area:", self.area_label)
        
        layout.addLayout(form_layout)
        
        # Material properties display
        self.properties_group = QGroupBox("Material Properties")
        self.properties_layout = QVBoxLayout()
        
        self.nrc_label = QLabel("NRC: Not selected")
        self.properties_layout.addWidget(self.nrc_label)
        
        self.coefficients_label = QLabel("Absorption Coefficients: Not selected")
        self.coefficients_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        self.properties_layout.addWidget(self.coefficients_label)
        
        self.properties_group.setLayout(self.properties_layout)
        layout.addWidget(self.properties_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Initial calculations
        self.calculate_area()
        self.on_type_changed()
        
    def populate_type_combo(self):
        """Populate the type combo box with appropriate materials"""
        self.type_combo.clear()
        
        if self.element_type == 'door':
            # Add door materials from enhanced_materials
            door_materials = {
                'solid_wood_doors': 'Solid Wood Door',
                'hollow_wood_doors': 'Hollow Wood Door', 
                'metal_doors': 'Metal Door'
            }
            
            for key, name in door_materials.items():
                if key in ENHANCED_MATERIALS:
                    self.type_combo.addItem(name, key)
                    
        elif self.element_type == 'window':
            # Add window materials from enhanced_materials
            window_materials = {
                'glass_window': 'Standard Glass Window',
                'heavy_glass': 'Heavy Glass Window'
            }
            
            for key, name in window_materials.items():
                if key in ENHANCED_MATERIALS:
                    self.type_combo.addItem(name, key)
                    
    def on_type_changed(self):
        """Handle material type selection change"""
        material_key = self.type_combo.currentData()
        if material_key and material_key in ENHANCED_MATERIALS:
            material = ENHANCED_MATERIALS[material_key]
            
            # Update NRC display
            nrc = self.calculate_nrc(material['absorption_coefficients'])
            self.nrc_label.setText(f"NRC: {nrc:.2f}")
            
            # Update coefficients display
            coeffs = material['absorption_coefficients']
            coeff_text = "Absorption Coefficients:\n"
            frequencies = [125, 250, 500, 1000, 2000, 4000]
            for freq in frequencies:
                coeff_text += f"{freq}Hz: {coeffs.get(freq, 0):.2f}  "
                if freq == 1000:
                    coeff_text += "\n"
            
            self.coefficients_label.setText(coeff_text.strip())
        else:
            self.nrc_label.setText("NRC: Not available")
            self.coefficients_label.setText("Absorption Coefficients: Not available")
            
    def calculate_nrc(self, coefficients: Dict[int, float]) -> float:
        """Calculate NRC from absorption coefficients"""
        nrc_frequencies = [250, 500, 1000, 2000]
        total = sum(coefficients.get(freq, 0) for freq in nrc_frequencies)
        return total / 4.0
        
    def calculate_area(self):
        """Calculate and display total area"""
        width = self.width_spin.value()
        height = self.height_spin.value()
        quantity = self.quantity_spin.value()
        
        total_area = width * height * quantity
        self.area_label.setText(f"{total_area:.1f} sf")
        
    def load_data(self):
        """Load existing element data for editing"""
        if not self.is_editing or not self.element_data:
            return
            
        # Set material type
        material_key = self.element_data.get('material_key')
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == material_key:
                self.type_combo.setCurrentIndex(i)
                break
                
        # Set other fields
        self.description_edit.setText(self.element_data.get('description', ''))
        self.width_spin.setValue(self.element_data.get('width', 1.0))
        self.height_spin.setValue(self.element_data.get('height', 1.0))
        self.quantity_spin.setValue(self.element_data.get('quantity', 1))
        
    def get_element_data(self) -> Dict:
        """Get the element data from the form"""
        material_key = self.type_combo.currentData()
        material = ENHANCED_MATERIALS.get(material_key, {})
        
        width = self.width_spin.value()
        height = self.height_spin.value()
        quantity = self.quantity_spin.value()
        total_area = width * height * quantity
        
        coefficients = material.get('absorption_coefficients', {})
        nrc = self.calculate_nrc(coefficients) if coefficients else 0.0
        
        return {
            'id': self.element_data.get('id', str(uuid.uuid4())),
            'type': self.element_type,
            'material_key': material_key,
            'material_name': material.get('name', 'Unknown'),
            'description': self.description_edit.text().strip(),
            'width': width,
            'height': height,
            'quantity': quantity,
            'total_area': total_area,
            'absorption_coefficients': coefficients,
            'nrc': nrc
        }


class DoorsWindowsWidget(QWidget):
    """Widget for managing door and window elements"""
    
    # Signals
    elements_changed = Signal()  # Emitted when doors/windows are modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.elements = []  # List of door/window elements
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Title and controls
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Doors & Windows")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #e0e0e0;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Add buttons
        self.add_door_btn = QPushButton("Add Door")
        self.add_door_btn.clicked.connect(lambda: self.add_element('door'))
        header_layout.addWidget(self.add_door_btn)
        
        self.add_window_btn = QPushButton("Add Window")
        self.add_window_btn.clicked.connect(lambda: self.add_element('window'))
        header_layout.addWidget(self.add_window_btn)
        
        layout.addLayout(header_layout)
        
        # Elements table
        self.elements_table = QTableWidget()
        self.elements_table.setColumnCount(9)
        
        headers = ["Type", "Description", "Material", "W×H", "Qty", "Area (sf)", "NRC", "Edit", "Remove"]
        self.elements_table.setHorizontalHeaderLabels(headers)
        
        # Configure table
        self.elements_table.setAlternatingRowColors(True)
        self.elements_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.elements_table.setMaximumHeight(200)
        
        # Set column widths
        header = self.elements_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Description
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Material
        
        for i in [0, 3, 4, 5, 6, 7, 8]:  # Fixed width columns
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            
        self.elements_table.setColumnWidth(0, 60)   # Type
        self.elements_table.setColumnWidth(3, 80)   # W×H
        self.elements_table.setColumnWidth(4, 40)   # Qty
        self.elements_table.setColumnWidth(5, 70)   # Area
        self.elements_table.setColumnWidth(6, 50)   # NRC
        self.elements_table.setColumnWidth(7, 50)   # Edit
        self.elements_table.setColumnWidth(8, 60)   # Remove
        
        layout.addWidget(self.elements_table)
        
        # Status
        self.status_label = QLabel("No doors or windows added")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 10px; margin: 5px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def add_element(self, element_type: str):
        """Add a new door or window element"""
        dialog = DoorWindowEditDialog(self, element_type)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            element_data = dialog.get_element_data()
            self.elements.append(element_data)
            self.refresh_table()
            self.elements_changed.emit()
            
    def edit_element(self, element_index: int):
        """Edit an existing element"""
        if 0 <= element_index < len(self.elements):
            element = self.elements[element_index]
            dialog = DoorWindowEditDialog(self, element['type'], element)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_data = dialog.get_element_data()
                self.elements[element_index] = updated_data
                self.refresh_table()
                self.elements_changed.emit()
                
    def remove_element(self, element_index: int):
        """Remove an element"""
        if 0 <= element_index < len(self.elements):
            element = self.elements[element_index]
            reply = QMessageBox.question(
                self, 
                "Confirm Removal",
                f"Remove {element['type']} '{element['description']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.elements.pop(element_index)
                self.refresh_table()
                self.elements_changed.emit()
                
    def refresh_table(self):
        """Refresh the elements table display"""
        self.elements_table.setRowCount(len(self.elements))
        
        for i, element in enumerate(self.elements):
            # Type
            type_item = QTableWidgetItem(element['type'].title())
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.elements_table.setItem(i, 0, type_item)
            
            # Description
            desc_item = QTableWidgetItem(element.get('description', ''))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.elements_table.setItem(i, 1, desc_item)
            
            # Material
            material_item = QTableWidgetItem(element.get('material_name', 'Unknown'))
            material_item.setFlags(material_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.elements_table.setItem(i, 2, material_item)
            
            # Dimensions (W×H)
            dimensions = f"{element.get('width', 0):.1f} × {element.get('height', 0):.1f}"
            dim_item = QTableWidgetItem(dimensions)
            dim_item.setFlags(dim_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.elements_table.setItem(i, 3, dim_item)
            
            # Quantity
            qty_item = QTableWidgetItem(str(element.get('quantity', 1)))
            qty_item.setFlags(qty_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.elements_table.setItem(i, 4, qty_item)
            
            # Total area
            area_item = QTableWidgetItem(f"{element.get('total_area', 0):.1f}")
            area_item.setFlags(area_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.elements_table.setItem(i, 5, area_item)
            
            # NRC
            nrc_item = QTableWidgetItem(f"{element.get('nrc', 0):.2f}")
            nrc_item.setFlags(nrc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.elements_table.setItem(i, 6, nrc_item)
            
            # Edit button
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, idx=i: self.edit_element(idx))
            self.elements_table.setCellWidget(i, 7, edit_btn)
            
            # Remove button
            remove_btn = QPushButton("Remove")
            remove_btn.setStyleSheet("color: #e74c3c;")
            remove_btn.clicked.connect(lambda checked, idx=i: self.remove_element(idx))
            self.elements_table.setCellWidget(i, 8, remove_btn)
            
        # Update status
        self.update_status()
        
    def update_status(self):
        """Update the status label"""
        if not self.elements:
            self.status_label.setText("No doors or windows added")
            return
            
        doors = sum(1 for e in self.elements if e['type'] == 'door')
        windows = sum(1 for e in self.elements if e['type'] == 'window')
        total_area = sum(e.get('total_area', 0) for e in self.elements)
        
        status_parts = []
        if doors > 0:
            status_parts.append(f"{doors} door{'s' if doors != 1 else ''}")
        if windows > 0:
            status_parts.append(f"{windows} window{'s' if windows != 1 else ''}")
            
        status = ", ".join(status_parts)
        status += f" | Total: {total_area:.1f} sf"
        
        self.status_label.setText(status)
        
    def get_elements_data(self) -> List[Dict]:
        """Get all elements data for external use"""
        return self.elements.copy()
        
    def set_elements_data(self, elements: List[Dict]):
        """Set elements data from external source"""
        self.elements = elements.copy() if elements else []
        self.refresh_table()
        
    def clear_all_elements(self):
        """Clear all elements"""
        if self.elements:
            reply = QMessageBox.question(
                self,
                "Confirm Clear All",
                "Remove all doors and windows?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.elements.clear()
                self.refresh_table()
                self.elements_changed.emit()