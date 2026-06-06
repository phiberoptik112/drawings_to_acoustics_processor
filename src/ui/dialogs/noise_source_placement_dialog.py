"""
Noise Source Placement Dialog - Select or create a noise source for drawing placement.
Supports octave-band Lw entry and spectrum estimation from overall dB(A).
"""

import json
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QDialogButtonBox, QListWidget,
    QListWidgetItem, QWidget, QStackedWidget)
from PySide6.QtCore import Qt, Signal

from models import get_session
from models.mechanical import NoiseSource


OCTAVE_FREQUENCIES = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
A_WEIGHTING = [-26.2, -16.1, -8.6, -3.2, 0.0, 1.2, 1.0, -1.1]


class NoiseSourcePlacementDialog(QDialog):
    """Dialog for selecting an existing noise source or creating a new one for placement."""

    source_selected = Signal(int)  # Emits noise_source_id on confirmation

    def __init__(self, parent=None, project_id: int = None, noise_source: NoiseSource = None):
        super().__init__(parent)
        self.project_id = project_id
        self.noise_source = noise_source
        self.is_editing = noise_source is not None
        self._selected_source_id = noise_source.id if noise_source else None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Noise Source Placement" if not self.is_editing else "Edit Noise Source")
        self.setModal(True)
        self.resize(550, 500)

        layout = QVBoxLayout()

        if not self.is_editing:
            # Selection mode: pick existing or create new
            self.stack = QStackedWidget()

            # Page 0: select existing
            select_page = QWidget()
            select_lay = QVBoxLayout()
            select_lay.addWidget(QLabel("Select an existing noise source or create a new one:"))
            self.source_list = QListWidget()
            self._populate_source_list()
            self.source_list.itemDoubleClicked.connect(self._on_select_existing)
            select_lay.addWidget(self.source_list)

            btn_row = QHBoxLayout()
            self.select_btn = QPushButton("Use Selected")
            self.select_btn.clicked.connect(self._on_select_existing)
            btn_row.addWidget(self.select_btn)
            self.new_btn = QPushButton("Create New...")
            self.new_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
            btn_row.addWidget(self.new_btn)
            btn_row.addStretch()
            select_lay.addLayout(btn_row)
            select_page.setLayout(select_lay)
            self.stack.addWidget(select_page)

            # Page 1: create new
            create_page = self._build_edit_form()
            self.stack.addWidget(create_page)
            layout.addWidget(self.stack)
        else:
            # Edit mode: go straight to form
            edit_form = self._build_edit_form()
            layout.addWidget(edit_form)

        self.setLayout(layout)

    def _populate_source_list(self):
        session = get_session()
        sources = session.query(NoiseSource).filter_by(project_id=self.project_id).all()
        for s in sources:
            item = QListWidgetItem(f"{s.name} ({s.source_type or 'general'}) - {s.base_noise_dba or '?'} dB(A)")
            item.setData(Qt.UserRole, s.id)
            self.source_list.addItem(item)
        session.close()

    def _on_select_existing(self):
        item = self.source_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Selection", "Please select a noise source.")
            return
        self._selected_source_id = item.data(Qt.UserRole)
        self.source_selected.emit(self._selected_source_id)
        self.accept()

    def _build_edit_form(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Chiller Plant, Generator Room")
        form.addRow("Name:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["equipment", "environmental", "other"])
        form.addRow("Source Type:", self.type_combo)

        layout.addLayout(form)

        # Octave-band Lw table
        octave_group = QGroupBox("Octave-Band Sound Power Levels (Lw, dB re 10⁻¹² W)")
        octave_lay = QVBoxLayout()

        self.octave_table = QTableWidget(1, 8)
        self.octave_table.setHorizontalHeaderLabels([str(f) for f in OCTAVE_FREQUENCIES])
        self.octave_table.setVerticalHeaderLabels(["Lw"])
        self.octave_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.octave_table.setMaximumHeight(60)
        for col in range(8):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            self.octave_table.setItem(0, col, item)
        octave_lay.addWidget(self.octave_table)

        # Overall dB(A) display and estimate button
        dba_row = QHBoxLayout()
        self.dba_spin = QDoubleSpinBox()
        self.dba_spin.setRange(0, 130)
        self.dba_spin.setDecimals(1)
        self.dba_spin.setSuffix(" dB(A)")
        self.dba_spin.setToolTip("Overall A-weighted level (computed from octave bands or enter manually)")
        dba_row.addWidget(QLabel("Overall:"))
        dba_row.addWidget(self.dba_spin)

        self.estimate_btn = QPushButton("Estimate Spectrum")
        self.estimate_btn.setToolTip("Generate a typical HVAC spectrum from the overall dB(A) level")
        self.estimate_btn.clicked.connect(self._estimate_spectrum)
        dba_row.addWidget(self.estimate_btn)

        self.compute_dba_btn = QPushButton("Compute dB(A)")
        self.compute_dba_btn.setToolTip("Compute overall dB(A) from octave bands")
        self.compute_dba_btn.clicked.connect(self._compute_dba_from_bands)
        dba_row.addWidget(self.compute_dba_btn)
        dba_row.addStretch()
        octave_lay.addLayout(dba_row)

        octave_group.setLayout(octave_lay)
        layout.addWidget(octave_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_new_source)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        widget.setLayout(layout)

        # If editing, populate fields
        if self.is_editing and self.noise_source:
            self.name_edit.setText(self.noise_source.name or "")
            idx = self.type_combo.findText(self.noise_source.source_type or "equipment")
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.dba_spin.setValue(self.noise_source.base_noise_dba or 0)
            bands = self.noise_source.get_octave_bands()
            if bands:
                for col, freq in enumerate(OCTAVE_FREQUENCIES):
                    val = bands.get(freq)
                    if val is not None:
                        self.octave_table.item(0, col).setText(f"{val:.1f}")

        return widget

    def _get_octave_values(self) -> Optional[dict]:
        """Read octave band values from the table. Returns None if any cell is empty."""
        bands = {}
        for col, freq in enumerate(OCTAVE_FREQUENCIES):
            text = self.octave_table.item(0, col).text().strip()
            if not text:
                return None
            try:
                bands[freq] = float(text)
            except ValueError:
                return None
        return bands

    def _compute_dba_from_bands(self):
        bands = self._get_octave_values()
        if not bands:
            QMessageBox.information(self, "Info", "Fill in all 8 octave-band values first.")
            return
        import math
        total = 0.0
        for i, freq in enumerate(OCTAVE_FREQUENCIES):
            lw = bands[freq] + A_WEIGHTING[i]
            total += 10 ** (lw / 10.0)
        overall = 10 * math.log10(total) if total > 0 else 0
        self.dba_spin.setValue(round(overall, 1))

    def _estimate_spectrum(self):
        dba = self.dba_spin.value()
        if dba <= 0:
            QMessageBox.information(self, "Info", "Enter an overall dB(A) level first.")
            return
        try:
            from calculations.nc_rating_analyzer import NCRatingAnalyzer
            analyzer = NCRatingAnalyzer()
            octave_data = analyzer.estimate_octave_bands_from_dba(dba, "typical_hvac")
            values = octave_data.to_list()
            for col in range(min(8, len(values))):
                self.octave_table.item(0, col).setText(f"{values[col]:.1f}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not estimate spectrum: {e}")

    def _save_new_source(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name is required.")
            return

        session = get_session()
        try:
            if self.is_editing:
                source = session.query(NoiseSource).get(self.noise_source.id)
            else:
                source = NoiseSource(project_id=self.project_id)
                session.add(source)

            source.name = name
            source.source_type = self.type_combo.currentText()
            source.base_noise_dba = self.dba_spin.value() if self.dba_spin.value() > 0 else None

            bands = self._get_octave_values()
            source.set_octave_bands(bands)

            session.flush()
            self._selected_source_id = source.id
            session.commit()
            self.source_selected.emit(source.id)
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save noise source: {e}")
        finally:
            session.close()

    def get_selected_source_id(self) -> Optional[int]:
        return self._selected_source_id
