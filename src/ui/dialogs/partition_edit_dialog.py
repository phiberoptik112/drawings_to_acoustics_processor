"""
Partition Edit Dialog - Add or edit a single partition assignment for a space.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QSpinBox, QTextEdit,
    QPushButton, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt

from models import get_session
from models.database import get_hvac_session
from models.partition import PartitionType, SpacePartition
from data.partition_stc_standards import (
    SPACE_TYPES, ASSEMBLY_LOCATIONS, get_minimum_stc
)


class PartitionEditDialog(QDialog):
    """Dialog for adding or editing a partition assignment"""
    
    def __init__(self, space_id, project_id, space_type=None, partition=None, parent=None):
        super().__init__(parent)
        self.space_id = space_id
        self.project_id = project_id
        self.space_type = space_type
        self.partition = partition  # Existing partition for editing, None for new
        
        self.partition_types_data = {}
        
        self.setWindowTitle("Edit Partition" if partition else "Add Partition")
        self.setModal(True)
        self.resize(500, 450)
        
        self.init_ui()
        self.load_partition_types()
        
        if partition:
            self.load_partition_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Partition type selection
        type_group = QGroupBox("Partition Type")
        type_layout = QFormLayout()
        
        self.partition_type_combo = QComboBox()
        self.partition_type_combo.addItem("-- Select from library --", None)
        self.partition_type_combo.currentIndexChanged.connect(self.on_partition_type_changed)
        type_layout.addRow("Assembly Type:", self.partition_type_combo)
        
        # Show selected type details
        self.type_details_label = QLabel("Select a partition type from the library")
        self.type_details_label.setWordWrap(True)
        self.type_details_label.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
        type_layout.addRow("", self.type_details_label)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Location and adjacency
        location_group = QGroupBox("Location & Adjacency")
        location_layout = QFormLayout()
        
        self.location_combo = QComboBox()
        self.location_combo.addItems(ASSEMBLY_LOCATIONS)
        location_layout.addRow("Assembly Location:", self.location_combo)
        
        self.adjacent_type_combo = QComboBox()
        self.adjacent_type_combo.setEditable(True)
        self.adjacent_type_combo.addItems([""] + SPACE_TYPES)
        self.adjacent_type_combo.currentTextChanged.connect(self.on_adjacent_type_changed)
        location_layout.addRow("Adjacent Space Type:", self.adjacent_type_combo)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        # STC Requirements
        stc_group = QGroupBox("STC Requirements")
        stc_layout = QFormLayout()
        
        # Minimum required STC
        min_stc_layout = QHBoxLayout()
        self.min_stc_spin = QSpinBox()
        self.min_stc_spin.setRange(0, 100)
        self.min_stc_spin.setValue(45)
        min_stc_layout.addWidget(self.min_stc_spin)
        
        self.auto_min_stc_btn = QPushButton("Auto")
        self.auto_min_stc_btn.setMaximumWidth(50)
        self.auto_min_stc_btn.setToolTip("Auto-calculate based on space types")
        self.auto_min_stc_btn.clicked.connect(self.auto_calculate_min_stc)
        min_stc_layout.addWidget(self.auto_min_stc_btn)
        min_stc_layout.addStretch()
        
        stc_layout.addRow("Minimum Required STC:", min_stc_layout)
        
        # Actual STC (from partition type or override)
        self.stc_rating_label = QLabel("--")
        self.stc_rating_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        stc_layout.addRow("Partition STC Rating:", self.stc_rating_label)
        
        # Override option
        self.override_check = QCheckBox("Override STC rating")
        self.override_check.stateChanged.connect(self.on_override_changed)
        stc_layout.addRow("", self.override_check)
        
        self.override_spin = QSpinBox()
        self.override_spin.setRange(0, 100)
        self.override_spin.setEnabled(False)
        self.override_spin.valueChanged.connect(self.update_compliance_preview)
        stc_layout.addRow("Override Value:", self.override_spin)
        
        stc_group.setLayout(stc_layout)
        layout.addWidget(stc_group)
        
        # Compliance preview
        self.compliance_label = QLabel("Select partition type to see compliance")
        self.compliance_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.compliance_label)
        
        # Notes
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        self.notes_edit.setPlaceholderText("Optional notes...")
        notes_layout.addWidget(self.notes_edit)
        
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_partition_types(self):
        """Load partition types from project"""
        try:
            session = get_session()
            partition_types = session.query(PartitionType).filter(
                PartitionType.project_id == self.project_id
            ).order_by(PartitionType.assembly_id).all()
            
            for pt in partition_types:
                self.partition_types_data[pt.id] = {
                    'id': pt.id,
                    'assembly_id': pt.assembly_id,
                    'description': pt.description,
                    'stc_rating': pt.stc_rating,
                    'source_document': pt.source_document
                }
                
                display_text = f"{pt.assembly_id} - STC {pt.stc_rating}"
                if pt.description:
                    display_text += f" ({pt.description[:30]}...)" if len(pt.description) > 30 else f" ({pt.description})"
                
                self.partition_type_combo.addItem(display_text, pt.id)
            
            session.close()
            
        except Exception as e:
            print(f"Error loading partition types: {e}")
    
    def load_partition_data(self):
        """Load existing partition data for editing"""
        if not self.partition:
            return
        
        # Set partition type
        if self.partition.partition_type_id:
            index = self.partition_type_combo.findData(self.partition.partition_type_id)
            if index >= 0:
                self.partition_type_combo.setCurrentIndex(index)
        
        # Set location
        if self.partition.assembly_location:
            index = self.location_combo.findText(self.partition.assembly_location)
            if index >= 0:
                self.location_combo.setCurrentIndex(index)
        
        # Set adjacent type
        if self.partition.adjacent_space_type:
            self.adjacent_type_combo.setCurrentText(self.partition.adjacent_space_type)
        
        # Set min STC
        if self.partition.minimum_stc_required:
            self.min_stc_spin.setValue(self.partition.minimum_stc_required)
        
        # Set override
        if self.partition.stc_rating_override is not None:
            self.override_check.setChecked(True)
            self.override_spin.setValue(self.partition.stc_rating_override)
        
        # Set notes
        if self.partition.notes:
            self.notes_edit.setPlainText(self.partition.notes)
    
    def on_partition_type_changed(self, index):
        """Handle partition type selection change"""
        partition_type_id = self.partition_type_combo.currentData()
        
        if partition_type_id and partition_type_id in self.partition_types_data:
            pt_data = self.partition_types_data[partition_type_id]
            
            # Update details label
            details = f"<b>{pt_data['assembly_id']}</b>"
            if pt_data['description']:
                details += f"<br>{pt_data['description']}"
            if pt_data['source_document']:
                details += f"<br><i>Source: {pt_data['source_document']}</i>"
            
            self.type_details_label.setText(details)
            self.type_details_label.setStyleSheet("color: #333; padding: 5px;")
            
            # Update STC rating display
            stc = pt_data['stc_rating']
            self.stc_rating_label.setText(f"STC {stc}" if stc else "--")
            
            if not self.override_check.isChecked():
                self.override_spin.setValue(stc or 45)
        else:
            self.type_details_label.setText("Select a partition type from the library")
            self.type_details_label.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
            self.stc_rating_label.setText("--")
        
        self.update_compliance_preview()
    
    def on_adjacent_type_changed(self, text):
        """Handle adjacent type change - suggest min STC"""
        self.update_compliance_preview()
    
    def on_override_changed(self, state):
        """Handle override checkbox change"""
        self.override_spin.setEnabled(state == Qt.CheckState.Checked.value)
        
        if not state:
            # Reset to partition type STC
            partition_type_id = self.partition_type_combo.currentData()
            if partition_type_id and partition_type_id in self.partition_types_data:
                stc = self.partition_types_data[partition_type_id]['stc_rating']
                self.override_spin.setValue(stc or 45)
        
        self.update_compliance_preview()
    
    def auto_calculate_min_stc(self):
        """Auto-calculate minimum STC based on space types"""
        adjacent_type = self.adjacent_type_combo.currentText()
        
        if not adjacent_type:
            QMessageBox.information(
                self, "Adjacent Type Required",
                "Please select an adjacent space type first."
            )
            return
        
        space_type = self.space_type or "default"
        suggested_stc = get_minimum_stc(space_type, adjacent_type)
        self.min_stc_spin.setValue(suggested_stc)
        self.update_compliance_preview()
    
    def update_compliance_preview(self):
        """Update the compliance preview label"""
        min_stc = self.min_stc_spin.value()
        
        # Get actual STC
        if self.override_check.isChecked():
            actual_stc = self.override_spin.value()
        else:
            partition_type_id = self.partition_type_combo.currentData()
            if partition_type_id and partition_type_id in self.partition_types_data:
                actual_stc = self.partition_types_data[partition_type_id]['stc_rating']
            else:
                actual_stc = None
        
        if actual_stc is None:
            self.compliance_label.setText("Select a partition type to see compliance")
            self.compliance_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 4px;
                    font-size: 12px;
                    color: #666;
                }
            """)
            self.stc_rating_label.setText("--")
            return
        
        # Update STC rating label
        if self.override_check.isChecked():
            self.stc_rating_label.setText(f"STC {actual_stc} (override)")
        else:
            self.stc_rating_label.setText(f"STC {actual_stc}")
        
        margin = actual_stc - min_stc
        
        if margin >= 0:
            if margin >= 5:
                text = f"✅ EXCEEDS: STC {actual_stc} exceeds minimum STC {min_stc} by {margin} points"
                bg_color = "#E8F5E9"
                text_color = "#2E7D32"
            else:
                text = f"✅ MEETS: STC {actual_stc} meets minimum STC {min_stc} (margin: {margin})"
                bg_color = "#E8F5E9"
                text_color = "#388E3C"
        else:
            text = f"❌ BELOW: STC {actual_stc} is {abs(margin)} points below minimum STC {min_stc}"
            bg_color = "#FFEBEE"
            text_color = "#C62828"
        
        self.compliance_label.setText(text)
        self.compliance_label.setStyleSheet(f"""
            QLabel {{
                padding: 10px;
                background-color: {bg_color};
                border-radius: 4px;
                font-size: 12px;
                color: {text_color};
                font-weight: bold;
            }}
        """)
    
    def validate(self):
        """Validate input"""
        partition_type_id = self.partition_type_combo.currentData()
        
        if not partition_type_id and not self.override_check.isChecked():
            QMessageBox.warning(
                self, "Validation Error",
                "Please select a partition type from the library, or check 'Override STC rating' to specify a custom value."
            )
            return False
        
        if not self.adjacent_type_combo.currentText().strip():
            QMessageBox.warning(
                self, "Validation Error",
                "Please specify the adjacent space type."
            )
            return False
        
        return True
    
    def save(self):
        """Save the partition"""
        if not self.validate():
            return
        
        try:
            with get_hvac_session() as session:
                if self.partition:
                    # Update existing
                    partition = session.query(SpacePartition).filter(
                        SpacePartition.id == self.partition.id
                    ).first()
                else:
                    # Create new
                    partition = SpacePartition(space_id=self.space_id)
                    session.add(partition)
                
                # Set values
                partition.partition_type_id = self.partition_type_combo.currentData()
                partition.assembly_location = self.location_combo.currentText()
                partition.adjacent_space_type = self.adjacent_type_combo.currentText().strip()
                partition.minimum_stc_required = self.min_stc_spin.value()
                
                if self.override_check.isChecked():
                    partition.stc_rating_override = self.override_spin.value()
                else:
                    partition.stc_rating_override = None
                
                partition.notes = self.notes_edit.toPlainText().strip() or None
            
            self.accept()
            
        except Exception as e:
            print(f"Error saving partition: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save partition:\n{e}")

