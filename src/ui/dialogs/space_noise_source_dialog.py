"""
Space Noise Source Dialog - Add and edit in-space noise sources (no duct path)
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QDoubleSpinBox, QComboBox, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt

from models import get_session
from models.space import SpaceNoiseSource


class SpaceNoiseSourceDialog(QDialog):
    """Dialog for adding and editing space-internal noise sources."""

    def __init__(self, parent=None, space_id: int = None, source: SpaceNoiseSource = None):
        super().__init__(parent)
        self.space_id = space_id
        self.source = source
        self.is_editing = source is not None
        self.init_ui()
        if self.is_editing:
            self.load_source_data()

    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit In-Space Noise Source" if self.is_editing else "Add In-Space Noise Source"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(450, 280)

        layout = QVBoxLayout()

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Unit Heater-1, Inline Fan")
        form.addRow("Name:", self.name_edit)

        self.base_noise_spin = QDoubleSpinBox()
        self.base_noise_spin.setRange(0, 120)
        self.base_noise_spin.setSuffix(" dB(A)")
        self.base_noise_spin.setDecimals(1)
        self.base_noise_spin.setValue(40.0)
        form.addRow("Base Noise Level:", self.base_noise_spin)

        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(1.0, 100.0)
        self.distance_spin.setSuffix(" ft")
        self.distance_spin.setDecimals(1)
        self.distance_spin.setValue(10.0)
        form.addRow("Distance to Receiver:", self.distance_spin)

        self.outlet_combo = QComboBox()
        self.outlet_combo.addItems(["Single", "Array"])
        self.outlet_combo.currentTextChanged.connect(self.on_outlet_changed)
        form.addRow("Outlet Configuration:", self.outlet_combo)

        self.num_outlets_spin = QSpinBox()
        self.num_outlets_spin.setRange(1, 100)
        self.num_outlets_spin.setValue(4)
        self.num_outlets_spin.setEnabled(False)
        form.addRow("Number of Outlets:", self.num_outlets_spin)
        self.num_outlets_row = form.rowCount() - 1

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save" if self.is_editing else "Add")
        save_btn.clicked.connect(self.save_source)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.on_outlet_changed(self.outlet_combo.currentText())

    def on_outlet_changed(self, text: str):
        """Enable/disable num outlets based on configuration"""
        is_array = text == "Array"
        self.num_outlets_spin.setEnabled(is_array)

    def load_source_data(self):
        """Load existing source data for editing"""
        if not self.source:
            return
        self.name_edit.setText(self.source.name or "")
        self.base_noise_spin.setValue(float(self.source.base_noise_dba or 40.0))
        self.distance_spin.setValue(float(self.source.distance_to_receiver_ft or 10.0))
        cfg = (self.source.outlet_configuration or "").lower()
        if cfg == "array":
            self.outlet_combo.setCurrentIndex(1)
            self.num_outlets_spin.setValue(int(self.source.num_outlets or 4))
        else:
            self.outlet_combo.setCurrentIndex(0)
        self.on_outlet_changed(self.outlet_combo.currentText())

    def save_source(self):
        """Save the noise source"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Please enter a name.")
            return
        if not self.space_id:
            QMessageBox.warning(self, "Error", "No space selected.")
            return

        outlet_text = self.outlet_combo.currentText()
        outlet_config = "array" if outlet_text == "Array" else "single"
        num_outlets = self.num_outlets_spin.value() if outlet_config == "array" else None

        if outlet_config == "array" and (not num_outlets or num_outlets < 1):
            QMessageBox.warning(self, "Validation", "Please enter number of outlets for array configuration.")
            return

        try:
            session = get_session()
            try:
                if self.is_editing and self.source:
                    db_source = session.query(SpaceNoiseSource).filter(
                        SpaceNoiseSource.id == self.source.id
                    ).first()
                    if db_source:
                        db_source.name = name
                        db_source.base_noise_dba = self.base_noise_spin.value()
                        db_source.distance_to_receiver_ft = self.distance_spin.value()
                        db_source.outlet_configuration = outlet_config
                        db_source.num_outlets = num_outlets
                        session.commit()
                        self.source = db_source
                else:
                    new_source = SpaceNoiseSource(
                        space_id=self.space_id,
                        name=name,
                        base_noise_dba=self.base_noise_spin.value(),
                        distance_to_receiver_ft=self.distance_spin.value(),
                        outlet_configuration=outlet_config,
                        num_outlets=num_outlets,
                    )
                    session.add(new_source)
                    session.commit()
                    self.source = new_source
                self.accept()
            finally:
                session.close()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{str(e)}")
