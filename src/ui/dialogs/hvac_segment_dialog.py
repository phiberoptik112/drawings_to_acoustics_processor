"""
HVAC Segment Dialog - Configure duct segments with fittings and acoustic properties
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QListWidget,
                             QListWidgetItem, QSplitter, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import get_session
from models.hvac import HVACSegment, SegmentFitting
from data.components import STANDARD_FITTINGS


class FittingTableWidget(QTableWidget):
    """Table widget for managing segment fittings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the table UI"""
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Fitting Type", "Quantity", "Noise Adjustment", "Actions"])
        
        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.setMaximumHeight(200)
        
    def add_fitting(self, fitting_type, quantity=1, noise_adjustment=0.0):
        """Add a fitting to the table"""
        row = self.rowCount()
        self.insertRow(row)
        
        # Fitting type
        type_combo = QComboBox()
        type_combo.addItems(list(STANDARD_FITTINGS.keys()))
        type_combo.setCurrentText(fitting_type)
        self.setCellWidget(row, 0, type_combo)
        
        # Quantity
        qty_spin = QSpinBox()
        qty_spin.setRange(1, 10)
        qty_spin.setValue(quantity)
        self.setCellWidget(row, 1, qty_spin)
        
        # Noise adjustment
        noise_spin = QDoubleSpinBox()
        noise_spin.setRange(-20, 20)
        noise_spin.setSuffix(" dB")
        noise_spin.setDecimals(1)
        noise_spin.setValue(noise_adjustment)
        self.setCellWidget(row, 2, noise_spin)
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_fitting(row))
        self.setCellWidget(row, 3, remove_btn)
        
    def remove_fitting(self, row):
        """Remove a fitting from the table"""
        self.removeRow(row)
        
    def get_fittings_data(self):
        """Get fittings data from table"""
        fittings = []
        for row in range(self.rowCount()):
            fitting_type = self.cellWidget(row, 0).currentText()
            quantity = self.cellWidget(row, 1).value()
            noise_adjustment = self.cellWidget(row, 2).value()
            
            fittings.append({
                'fitting_type': fitting_type,
                'quantity': quantity,
                'noise_adjustment': noise_adjustment
            })
        return fittings
        
    def set_fittings_data(self, fittings_data):
        """Set fittings data in table"""
        self.setRowCount(0)
        for fitting in fittings_data:
            self.add_fitting(
                fitting.get('fitting_type', 'elbow'),
                fitting.get('quantity', 1),
                fitting.get('noise_adjustment', 0.0)
            )


class HVACSegmentDialog(QDialog):
    """Dialog for configuring HVAC segments with fittings"""
    
    segment_saved = Signal(HVACSegment)  # Emits saved segment
    
    def __init__(self, parent=None, hvac_path_id=None, from_component=None, 
                 to_component=None, segment=None):
        super().__init__(parent)
        self.hvac_path_id = hvac_path_id
        self.from_component = from_component
        self.to_component = to_component
        self.segment = segment  # Existing segment for editing
        self.is_editing = segment is not None
        
        self.init_ui()
        if self.is_editing:
            self.load_segment_data()
        
    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit HVAC Segment" if self.is_editing else "Configure HVAC Segment"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(700, 600)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel(title)
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Connection Information
        if self.from_component and self.to_component:
            connection_text = f"From: {self.from_component.name} → To: {self.to_component.name}"
            connection_label = QLabel(connection_text)
            connection_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px;")
            layout.addWidget(connection_label)
        
        # Main content in splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Left panel - Segment properties
        left_panel = self.create_segment_properties_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Fittings
        right_panel = self.create_fittings_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if self.is_editing:
            self.delete_btn = QPushButton("Delete Segment")
            self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            self.delete_btn.clicked.connect(self.delete_segment)
            button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        save_text = "Update Segment" if self.is_editing else "Create Segment"
        self.save_btn = QPushButton(save_text)
        self.save_btn.clicked.connect(self.save_segment)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_segment_properties_panel(self):
        """Create the segment properties panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Segment Information
        info_group = QGroupBox("Segment Information")
        info_layout = QFormLayout()
        
        # Length
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(0, 1000)
        self.length_spin.setSuffix(" ft")
        self.length_spin.setDecimals(1)
        info_layout.addRow("Length:", self.length_spin)
        
        # Segment order
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 100)
        info_layout.addRow("Segment Order:", self.order_spin)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Duct Properties
        duct_group = QGroupBox("Duct Properties")
        duct_layout = QFormLayout()
        
        # Duct shape
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["rectangular", "circular"])  # use 'circular' to match engine
        self.shape_combo.currentTextChanged.connect(self.on_duct_shape_changed)
        duct_layout.addRow("Duct Shape:", self.shape_combo)
        
        # Duct dimensions
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 100)
        self.width_spin.setSuffix(" in")
        self.width_spin.setDecimals(1)
        duct_layout.addRow("Width:", self.width_spin)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 100)
        self.height_spin.setSuffix(" in")
        self.height_spin.setDecimals(1)
        duct_layout.addRow("Height:", self.height_spin)

        # Diameter for circular ducts
        self.diameter_spin = QDoubleSpinBox()
        self.diameter_spin.setRange(1, 120)
        self.diameter_spin.setSuffix(" in")
        self.diameter_spin.setDecimals(1)
        duct_layout.addRow("Diameter:", self.diameter_spin)
        
        # Duct type
        self.duct_type_combo = QComboBox()
        self.duct_type_combo.addItems(["sheet_metal", "fiberglass", "flexible"])
        duct_layout.addRow("Duct Type:", self.duct_type_combo)
        
        # Lining material and thickness
        self.insulation_combo = QComboBox()
        self.insulation_combo.addItems(["none", "fiberglass", "foam", "mineral_wool"])
        duct_layout.addRow("Lining Material:", self.insulation_combo)

        self.lining_thickness_spin = QDoubleSpinBox()
        self.lining_thickness_spin.setRange(0, 6)
        self.lining_thickness_spin.setDecimals(1)
        self.lining_thickness_spin.setSuffix(" in")
        duct_layout.addRow("Lining Thickness:", self.lining_thickness_spin)
        
        duct_group.setLayout(duct_layout)
        layout.addWidget(duct_group)
        
        # Acoustic Properties
        acoustic_group = QGroupBox("Acoustic Properties")
        acoustic_layout = QFormLayout()
        
        # Distance loss
        self.distance_loss_spin = QDoubleSpinBox()
        self.distance_loss_spin.setRange(0, 50)
        self.distance_loss_spin.setSuffix(" dB")
        self.distance_loss_spin.setDecimals(2)
        acoustic_layout.addRow("Distance Loss:", self.distance_loss_spin)
        
        # Duct loss
        self.duct_loss_spin = QDoubleSpinBox()
        self.duct_loss_spin.setRange(0, 50)
        self.duct_loss_spin.setSuffix(" dB")
        self.duct_loss_spin.setDecimals(2)
        acoustic_layout.addRow("Duct Loss:", self.duct_loss_spin)
        
        # Fitting additions
        self.fitting_additions_spin = QDoubleSpinBox()
        self.fitting_additions_spin.setRange(0, 20)
        self.fitting_additions_spin.setSuffix(" dB")
        self.fitting_additions_spin.setDecimals(2)
        acoustic_layout.addRow("Fitting Additions:", self.fitting_additions_spin)
        
        acoustic_group.setLayout(acoustic_layout)
        layout.addWidget(acoustic_group)
        
        panel.setLayout(layout)
        return panel
        
    def create_fittings_panel(self):
        """Create the fittings management panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Fittings header
        fittings_label = QLabel("Duct Fittings")
        fittings_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(fittings_label)
        
        # Add fitting button
        add_fitting_btn = QPushButton("Add Fitting")
        add_fitting_btn.clicked.connect(self.add_fitting)
        layout.addWidget(add_fitting_btn)
        
        # Fittings table
        self.fittings_table = FittingTableWidget()
        layout.addWidget(self.fittings_table)
        
        # Fitting library
        library_group = QGroupBox("Fitting Library")
        library_layout = QVBoxLayout()
        
        self.library_list = QListWidget()
        self.library_list.setMaximumHeight(150)
        self.library_list.itemDoubleClicked.connect(self.add_fitting_from_library)
        
        # Populate library
        for fitting_type in STANDARD_FITTINGS.keys():
            item = QListWidgetItem(fitting_type)
            item.setData(Qt.UserRole, fitting_type)
            self.library_list.addItem(item)
        
        library_layout.addWidget(self.library_list)
        library_group.setLayout(library_layout)
        layout.addWidget(library_group)
        
        panel.setLayout(layout)
        return panel
        
    def on_duct_shape_changed(self, shape):
        """Handle duct shape change"""
        if shape == "circular":
            # Show diameter; hide rectangular dims
            self.diameter_spin.setEnabled(True)
            self.width_spin.setEnabled(False)
            self.height_spin.setEnabled(False)
        else:
            self.diameter_spin.setEnabled(False)
            self.width_spin.setEnabled(True)
            self.height_spin.setEnabled(True)
    
    def add_fitting(self):
        """Add a new fitting to the table"""
        self.fittings_table.add_fitting("elbow")
    
    def add_fitting_from_library(self, item):
        """Add fitting from library selection"""
        fitting_type = item.data(Qt.UserRole)
        self.fittings_table.add_fitting(fitting_type)
    
    def load_segment_data(self):
        """Load existing segment data for editing"""
        if not self.segment:
            return
            
        self.length_spin.setValue(self.segment.length or 0)
        self.order_spin.setValue(self.segment.segment_order or 1)
        
        # Duct properties
        if self.segment.duct_shape:
            index = self.shape_combo.findText(self.segment.duct_shape)
            if index >= 0:
                self.shape_combo.setCurrentIndex(index)
        
        self.width_spin.setValue(self.segment.duct_width or 12)
        self.height_spin.setValue(self.segment.duct_height or 8)
        self.diameter_spin.setValue(getattr(self.segment, 'diameter', 0) or 0)
        
        if self.segment.duct_type:
            index = self.duct_type_combo.findText(self.segment.duct_type)
            if index >= 0:
                self.duct_type_combo.setCurrentIndex(index)
        
        if self.segment.insulation:
            index = self.insulation_combo.findText(self.segment.insulation)
            if index >= 0:
                self.insulation_combo.setCurrentIndex(index)
        if getattr(self.segment, 'lining_thickness', None) is not None:
            self.lining_thickness_spin.setValue(self.segment.lining_thickness or 0)
        
        # Acoustic properties
        self.distance_loss_spin.setValue(self.segment.distance_loss or 0)
        self.duct_loss_spin.setValue(self.segment.duct_loss or 0)
        self.fitting_additions_spin.setValue(self.segment.fitting_additions or 0)
        
        # Load fittings
        fittings_data = []
        for fitting in self.segment.fittings:
            fittings_data.append({
                'fitting_type': fitting.fitting_type,
                'quantity': fitting.quantity or 1,
                'noise_adjustment': fitting.noise_adjustment or 0.0
            })
        self.fittings_table.set_fittings_data(fittings_data)
    
    def save_segment(self):
        """Save the HVAC segment"""
        # Validate inputs
        if self.length_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid segment length.")
            return
        
        try:
            session = get_session()
            
            if self.is_editing:
                # Update existing segment
                self.update_segment_properties(self.segment)
                self.update_segment_fittings(self.segment, session)
                session.commit()
                segment = self.segment
            else:
                # Create new segment
                segment = HVACSegment(
                    hvac_path_id=self.hvac_path_id,
                    from_component_id=self.from_component.id if self.from_component else None,
                    to_component_id=self.to_component.id if self.to_component else None,
                    length=self.length_spin.value(),
                    segment_order=self.order_spin.value(),
                    duct_width=self.width_spin.value(),
                    duct_height=self.height_spin.value(),
                    diameter=self.diameter_spin.value(),
                    duct_shape=self.shape_combo.currentText(),
                    duct_type=self.duct_type_combo.currentText(),
                    insulation=self.insulation_combo.currentText(),
                    lining_thickness=self.lining_thickness_spin.value(),
                    distance_loss=self.distance_loss_spin.value(),
                    duct_loss=self.duct_loss_spin.value(),
                    fitting_additions=self.fitting_additions_spin.value()
                )
                
                session.add(segment)
                session.flush()  # Get ID
                
                # Add fittings
                self.update_segment_fittings(segment, session)
                session.commit()
            
            session.close()
            
            self.segment_saved.emit(segment)
            self.accept()
            
        except Exception as e:
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Error", f"Failed to save segment:\n{str(e)}")
    
    def update_segment_properties(self, segment):
        """Update segment properties"""
        segment.length = self.length_spin.value()
        segment.segment_order = self.order_spin.value()
        segment.duct_width = self.width_spin.value()
        segment.duct_height = self.height_spin.value()
        segment.diameter = self.diameter_spin.value()
        segment.duct_shape = self.shape_combo.currentText()
        segment.duct_type = self.duct_type_combo.currentText()
        segment.insulation = self.insulation_combo.currentText()
        segment.lining_thickness = self.lining_thickness_spin.value()
        segment.distance_loss = self.distance_loss_spin.value()
        segment.duct_loss = self.duct_loss_spin.value()
        segment.fitting_additions = self.fitting_additions_spin.value()
    
    def update_segment_fittings(self, segment, session):
        """Update segment fittings"""
        # Remove existing fittings
        for fitting in segment.fittings:
            session.delete(fitting)
        
        # Add new fittings
        fittings_data = self.fittings_table.get_fittings_data()
        for fitting_data in fittings_data:
            fitting = SegmentFitting(
                segment_id=segment.id,
                fitting_type=fitting_data['fitting_type'],
                quantity=fitting_data['quantity'],
                noise_adjustment=fitting_data['noise_adjustment']
            )
            session.add(fitting)
    
    def delete_segment(self):
        """Delete the HVAC segment"""
        if not self.is_editing or not self.segment:
            return
            
        reply = QMessageBox.question(
            self, "Delete Segment",
            f"Are you sure you want to delete this segment?\n\n"
            "This will also remove all fittings associated with this segment.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                session.delete(self.segment)
                session.commit()
                session.close()
                
                self.accept()
                
            except Exception as e:
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Error", f"Failed to delete segment:\n{str(e)}")


# Convenience function to show dialog
def show_hvac_segment_dialog(parent=None, hvac_path_id=None, from_component=None, 
                           to_component=None, segment=None):
    """Show HVAC segment dialog"""
    dialog = HVACSegmentDialog(parent, hvac_path_id, from_component, to_component, segment)
    return dialog.exec() 