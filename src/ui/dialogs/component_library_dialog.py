"""
Component Library Dialog
 - Displays Mechanical Units and Noise Sources stored in the project database
 - Provides an "Import Mechanical Schedule from Image" workflow that leverages
   the image->CSV utility and ingests the resulting CSV into the Mechanical
   Units table for the active project.
"""

from __future__ import annotations

import os
import subprocess
import sys
import csv
from typing import List

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QWidget,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QTextEdit,
)
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy

from models import get_session
from models.mechanical import MechanicalUnit, NoiseSource


class ComponentLibraryDialog(QDialog):
    """Project-level component library management dialog."""

    def __init__(self, parent=None, project_id: int | None = None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("Component Library")
        self.resize(900, 600)
        self.setMinimumSize(800, 500)
        self.setModal(True)

        self._build_ui()
        self.refresh_lists()
        self.freq_dirty = False

    # UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        tabs = QTabWidget()
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Mechanical Units tab
        mech_tab = QWidget()
        mech_layout = QVBoxLayout()
        mech_layout.addWidget(QLabel("Mechanical Units"))

        # Splitter: left list, right frequency preview
        mech_split = QSplitter()
        mech_split.setOrientation(Qt.Horizontal)

        # Left list
        left_container = QWidget()
        left_v = QVBoxLayout(left_container)
        self.mechanical_list = QListWidget()
        self.mechanical_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_v.addWidget(self.mechanical_list)
        mech_split.addWidget(left_container)

        # Right preview area: frequency table and PDF preview side-by-side
        right_container = QWidget()
        right_v = QVBoxLayout(right_container)
        right_split = QSplitter()
        right_split.setOrientation(Qt.Horizontal)

        # Frequency group (left in right panel)
        freq_group = QGroupBox("Frequency Preview (Sound Power Levels)")
        freq_v = QVBoxLayout()
        self.band_order = ["63","125","250","500","1000","2000","4000","8000"]
        self.freq_table = QTableWidget(8, 4)
        self.freq_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.freq_table.setHorizontalHeaderLabels(["Band (Hz)", "Inlet", "Radiated", "Outlet"])
        for i, b in enumerate(self.band_order):
            self.freq_table.setItem(i, 0, QTableWidgetItem(b))
            for j in range(1,4):
                self.freq_table.setItem(i, j, QTableWidgetItem(""))
        self.freq_table.horizontalHeader().setStretchLastSection(True)
        # Enable editing on double click
        self.freq_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.freq_table.cellChanged.connect(self._on_freq_cell_changed)
        freq_v.addWidget(self.freq_table)
        freq_group.setLayout(freq_v)
        freq_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # PDF preview group (right in right panel)
        preview_group = QGroupBox("File Preview (PDF)")
        preview_v = QVBoxLayout()
        from drawing.pdf_viewer import PDFViewer
        self.preview_viewer = PDFViewer()
        preview_v.addWidget(self.preview_viewer)
        preview_btns = QHBoxLayout()
        self.load_pdf_btn = QPushButton("Load PDF…")
        self.load_pdf_btn.clicked.connect(self.load_preview_pdf)
        preview_btns.addStretch(); preview_btns.addWidget(self.load_pdf_btn)
        preview_v.addLayout(preview_btns)
        preview_group.setLayout(preview_v)

        right_split.addWidget(freq_group)
        right_split.addWidget(preview_group)
        right_split.setStretchFactor(0, 1)
        right_split.setStretchFactor(1, 1)
        right_v.addWidget(right_split)

        mech_split.addWidget(right_container)

        # Favor preview panel width a bit more
        mech_split.setStretchFactor(0, 1)
        mech_split.setStretchFactor(1, 2)

        mech_layout.addWidget(mech_split, 1)

        # Update preview/tooltip when selection changes
        self.mechanical_list.itemSelectionChanged.connect(self._on_mech_selection_changed)
        # Also control edit/delete state
        self.mechanical_list.itemSelectionChanged.connect(self._toggle_edit_delete_buttons)

        mech_btns = QHBoxLayout()
        self.import_btn = QPushButton("Import Mechanical Schedule from Image")
        self.import_btn.clicked.connect(self.import_mechanical_schedule_from_image)
        self.import_pdf_btn = QPushButton("Import Mechanical Schedule from PDF")
        self.import_pdf_btn.clicked.connect(self.import_mechanical_schedule_from_pdf)
        self.edit_btn = QPushButton("Edit Entry")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_selected_mechanical_unit)
        self.delete_btn = QPushButton("Delete Entry")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_mechanical_unit)
        mech_btns.addWidget(self.import_btn)
        mech_btns.addWidget(self.import_pdf_btn)
        mech_btns.addStretch()
        mech_btns.addWidget(self.edit_btn)
        mech_btns.addWidget(self.delete_btn)
        mech_layout.addLayout(mech_btns)
        mech_tab.setLayout(mech_layout)

        # Noise Sources tab
        noise_tab = QWidget()
        noise_layout = QVBoxLayout()
        self.noise_list = QListWidget()
        noise_layout.addWidget(QLabel("Noise Sources"))
        noise_layout.addWidget(self.noise_list)
        noise_tab.setLayout(noise_layout)

        tabs.addTab(mech_tab, "Mechanical Units")
        tabs.addTab(noise_tab, "Noise Sources")

        layout.addWidget(tabs, 1)

        # Close/Save buttons
        close_btns = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_frequency_changes)
        close_btns.addStretch()
        close_btns.addWidget(self.save_btn)
        close_btns.addWidget(close_btn)
        layout.addLayout(close_btns)

        self.setLayout(layout)

    # Data
    def refresh_lists(self) -> None:
        try:
            session = get_session()
            units: List[MechanicalUnit] = (
                session.query(MechanicalUnit)
                .filter(MechanicalUnit.project_id == self.project_id)
                .order_by(MechanicalUnit.name)
                .all()
            )
            sources: List[NoiseSource] = (
                session.query(NoiseSource)
                .filter(NoiseSource.project_id == self.project_id)
                .order_by(NoiseSource.name)
                .all()
            )
            self.mechanical_list.clear()
            for u in units:
                text = f"{u.name} — {u.unit_type or ''}  {u.airflow_cfm or ''} CFM"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, u.id)
                self.mechanical_list.addItem(item)
            # Clear preview
            self._clear_freq_preview()
            self.noise_list.clear()
            for s in sources:
                text = f"{s.name} — {s.source_type or ''}  {s.base_noise_dba or ''} dBA"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, s.id)
                self.noise_list.addItem(item)
            session.close()
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load component library:\n{e}")

    def _update_mech_tooltip(self) -> None:
        # Show frequency preview in item tooltip when available
        try:
            current = self.mechanical_list.currentItem()
            if not current:
                return
            item_id = current.data(Qt.UserRole)
            session = get_session()
            from models.mechanical import MechanicalUnit
            unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == item_id).first()
            session.close()
            if not unit:
                return
            import json
            preview = None
            if getattr(unit, 'outlet_levels_json', None):
                try:
                    bands = json.loads(unit.outlet_levels_json)
                    ordered_keys = ["63", "125", "250", "500", "1000", "2000", "4000", "8000"]
                    parts = [f"{k}:{bands.get(k, '')}" for k in ordered_keys if k in bands]
                    preview = "Outlet " + ", ".join(parts)
                except Exception:
                    pass
            if preview:
                current.setToolTip(preview)
            else:
                current.setToolTip("")
        except Exception:
            pass

    def _clear_freq_preview(self) -> None:
        if hasattr(self, 'freq_table') and self.freq_table is not None:
            for i in range(self.freq_table.rowCount()):
                for j in range(1, 4):
                    item = self.freq_table.item(i, j)
                    if item:
                        item.setText("")
        # reset dirty state
        self.freq_dirty = False
        if hasattr(self, 'save_btn'):
            self.save_btn.setEnabled(False)

    def _on_mech_selection_changed(self) -> None:
        # Update both tooltip and right-hand preview
        self._update_mech_tooltip()
        try:
            current = self.mechanical_list.currentItem()
            if not current:
                self._clear_freq_preview()
                return
            item_id = current.data(Qt.UserRole)
            session = get_session()
            unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == item_id).first()
            session.close()
            if not unit:
                self._clear_freq_preview()
                return
            import json
            def fill_column(json_str: str | None, col: int) -> None:
                if not json_str:
                    for r in range(len(self.band_order)):
                        self.freq_table.item(r, col).setText("")
                    return
                try:
                    data = json.loads(json_str)
                except Exception:
                    data = {}
                for r, band in enumerate(self.band_order):
                    val = data.get(band, "")
                    self.freq_table.item(r, col).setText(str(val) if val is not None else "")

            # Fill preview columns
            fill_column(getattr(unit, 'inlet_levels_json', None), 1)
            fill_column(getattr(unit, 'radiated_levels_json', None), 2)
            fill_column(getattr(unit, 'outlet_levels_json', None), 3)
            # reset dirty state after load
            self.freq_dirty = False
            if hasattr(self, 'save_btn'):
                self.save_btn.setEnabled(False)
        except Exception:
            self._clear_freq_preview()

    def _toggle_edit_delete_buttons(self) -> None:
        has_sel = self.mechanical_list.currentItem() is not None
        self.edit_btn.setEnabled(has_sel)
        self.delete_btn.setEnabled(has_sel)

    # Import workflow
    def import_mechanical_schedule_from_image(self) -> None:
        """Run OCR pipeline on an image and import resulting CSV into MechanicalUnit."""
        # Pick image
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Mechanical Schedule Image",
            "",
            "Images (*.png *.jpg *.jpeg *.tif *.tiff);;All Files (*)",
        )
        if not image_path:
            return

        # Choose output CSV path (temporary beside image by default)
        default_csv = os.path.splitext(image_path)[0] + "_table.csv"
        csv_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extracted CSV",
            default_csv,
            "CSV Files (*.csv)",
        )
        if not csv_path:
            return

        # Run the script as a module so it works in venv and packaged contexts
        try:
            script_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", "calculations", "image_table_to_csv.py"
            ))
            python_exec = sys.executable
            cmd = [python_exec, script_path, "--image", image_path, "--output", csv_path]
            # Non-interactive run
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "Image to CSV extraction failed")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to extract table:\n{e}")
            return

        # Ingest CSV rows
        try:
            # Method exists below in this class; ensure correct name
            self._import_csv_into_mechanical_units(csv_path)
            QMessageBox.information(self, "Import Complete", "Mechanical schedule imported successfully.")
            self.refresh_lists()
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import CSV into database:\n{e}")

    def import_mechanical_schedule_from_pdf(self) -> None:
        """Extract a mechanical schedule directly from a PDF using PyMuPDF and ingest it."""
        pdf_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Mechanical Schedule PDF",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not pdf_path:
            return

        # Extract to temporary JSON next to PDF
        try:
            script_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", "calculations", "pdf_table_to_mechanical_units.py"
            ))
            python_exec = sys.executable
            output_json = os.path.splitext(pdf_path)[0] + "_units.json"
            # Enable verbose debug to help diagnose empty results
            cmd = [python_exec, script_path, "--pdf", pdf_path, "--output", output_json, "--debug"]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "PDF extraction failed")
            # If no units parsed, surface debug output
            if os.path.exists(output_json):
                try:
                    import json
                    with open(output_json, "r", encoding="utf-8") as f:
                        parsed = json.load(f)
                    if not parsed:
                        dbg = (result.stdout or "")
                        QMessageBox.information(self, "PDF Import Debug", f"No rows parsed. Debug output:\n\n{dbg[:2000]}")
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to extract from PDF:\n{e}")
            return

        # Load JSON and ingest
        try:
            import json
            with open(output_json, "r", encoding="utf-8") as f:
                units = json.load(f)

            session = get_session()
            for rec in units:
                unit = MechanicalUnit(
                    project_id=self.project_id,
                    name=rec.get("name"),
                    unit_type=rec.get("unit_type"),
                    outlet_levels_json=rec.get("outlet_levels_json"),
                    extra_json=rec.get("extra_json"),
                )
                session.add(unit)
            session.commit()
            session.close()
            self.refresh_lists()
            QMessageBox.information(self, "Import Complete", f"Imported {len(units)} mechanical units from PDF.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import PDF results into database:\n{e}")

    def load_preview_pdf(self):
        pdf_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF to Preview",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not pdf_path:
            return
        try:
            self.preview_viewer.load_pdf(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Preview Error", f"Failed to load PDF:\n{e}")

    def _on_freq_cell_changed(self, _row: int, _col: int) -> None:
        # Mark table dirty when user edits a cell
        self.freq_dirty = True
        if hasattr(self, 'save_btn'):
            self.save_btn.setEnabled(True)

    def save_frequency_changes(self) -> None:
        if not self.freq_dirty:
            return
        current = self.mechanical_list.currentItem()
        if not current:
            QMessageBox.information(self, "Save", "Select a Mechanical Unit first.")
            return
        unit_id = current.data(Qt.UserRole)
        try:
            # Collect values from table
            def collect_col(col: int) -> dict:
                data = {}
                for r, band in enumerate(self.band_order):
                    item = self.freq_table.item(r, col)
                    if item:
                        val = item.text().strip()
                        if val:
                            data[band] = val
                return data
            inlet_data = collect_col(1)
            radiated_data = collect_col(2)
            outlet_data = collect_col(3)
            import json as _json
            session = get_session()
            unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == unit_id).first()
            if not unit:
                session.close()
                QMessageBox.warning(self, "Save", "Selected unit not found in database.")
                return
            unit.inlet_levels_json = _json.dumps(inlet_data) if inlet_data else None
            unit.radiated_levels_json = _json.dumps(radiated_data) if radiated_data else None
            unit.outlet_levels_json = _json.dumps(outlet_data) if outlet_data else None
            session.commit()
            session.close()
            self.freq_dirty = False
            self.save_btn.setEnabled(False)
            QMessageBox.information(self, "Saved", "Frequency values saved to database.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes:\n{e}")

    # --- Edit/Delete operations ---
    def edit_selected_mechanical_unit(self) -> None:
        item = self.mechanical_list.currentItem()
        if not item:
            return
        unit_id = item.data(Qt.UserRole)
        session = get_session()
        unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == unit_id).first()
        session.close()
        if not unit:
            return
        dlg = MechanicalUnitEditDialog(self, unit)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_lists()

    def delete_selected_mechanical_unit(self) -> None:
        item = self.mechanical_list.currentItem()
        if not item:
            return
        unit_id = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            "Delete Entry",
            "Are you sure you want to delete the selected Mechanical Unit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            session = get_session()
            unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == unit_id).first()
            if unit:
                session.delete(unit)
                session.commit()
            session.close()
            self.refresh_lists()
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete entry:\n{e}")


class MechanicalUnitEditDialog(QDialog):
    """Simple editor for MechanicalUnit properties, including extras JSON."""

    def __init__(self, parent: QWidget | None, unit: MechanicalUnit):
        super().__init__(parent)
        self.unit = unit
        self.setWindowTitle(f"Edit Mechanical Unit: {unit.name}")
        self.resize(500, 500)
        self.setModal(True)

        v = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(unit.name or "")
        form.addRow("Name:", self.name_edit)

        self.type_edit = QLineEdit(unit.unit_type or "")
        form.addRow("Unit Type:", self.type_edit)

        self.mfr_edit = QLineEdit(getattr(unit, 'manufacturer', '') or "")
        form.addRow("Manufacturer:", self.mfr_edit)

        self.model_edit = QLineEdit(getattr(unit, 'model_number', '') or "")
        form.addRow("Model:", self.model_edit)

        self.cfm_spin = QDoubleSpinBox()
        self.cfm_spin.setRange(0, 1_000_000)
        self.cfm_spin.setDecimals(1)
        if unit.airflow_cfm is not None:
            self.cfm_spin.setValue(float(unit.airflow_cfm))
        form.addRow("Airflow (CFM):", self.cfm_spin)

        self.esp_spin = QDoubleSpinBox()
        self.esp_spin.setRange(0, 1000)
        self.esp_spin.setDecimals(2)
        if unit.external_static_inwg is not None:
            self.esp_spin.setValue(float(unit.external_static_inwg))
        form.addRow("External Static (in.w.g):", self.esp_spin)

        v.addLayout(form)

        # Extra properties JSON
        self.extra_text = QTextEdit()
        self.extra_text.setPlaceholderText("Additional properties (JSON)")
        try:
            import json
            if unit.extra_json:
                parsed = json.loads(unit.extra_json)
                self.extra_text.setPlainText(json.dumps(parsed, indent=2))
        except Exception:
            self.extra_text.setPlainText(unit.extra_json or "")
        v.addWidget(QLabel("Additional Properties (JSON):"))
        v.addWidget(self.extra_text, 1)

        # Buttons
        btns = QHBoxLayout()
        cancel = QPushButton("Cancel")
        save = QPushButton("Save")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        btns.addStretch(); btns.addWidget(cancel); btns.addWidget(save)
        v.addLayout(btns)

    def _save(self) -> None:
        try:
            session = get_session()
            db_unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == self.unit.id).first()
            if not db_unit:
                session.close()
                QMessageBox.critical(self, "Save Error", "Unit not found")
                return
            db_unit.name = self.name_edit.text().strip() or db_unit.name
            db_unit.unit_type = self.type_edit.text().strip() or None
            db_unit.manufacturer = self.mfr_edit.text().strip() or None
            db_unit.model_number = self.model_edit.text().strip() or None
            db_unit.airflow_cfm = float(self.cfm_spin.value()) if self.cfm_spin.value() > 0 else None
            db_unit.external_static_inwg = float(self.esp_spin.value()) if self.esp_spin.value() > 0 else None
            txt = self.extra_text.toPlainText().strip()
            if txt:
                # Validate JSON
                import json
                try:
                    json.loads(txt)
                    db_unit.extra_json = txt
                except Exception:
                    db_unit.extra_json = txt
            else:
                db_unit.extra_json = None
            session.commit()
            session.close()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes:\n{e}")

    def _import_csv_into_mechanical_units(self, csv_path: str) -> None:
        """Import Mechanical Units from a CSV produced by the OCR tool.

        Handles two common formats:
        1) Conventional schedules with headers like: name/tag, type, cfm, esp, manufacturer, model
        2) Sound performance schedules where headers include MARK, NUMBER, and frequency bands
           (63, 125, 250, 500, 1K, 2K, 4K, 8K). In this case we synthesize unit name
           as "MARK-NUMBER" and store MARK as unit_type.
        """

        # Read CSV
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = [ [c.strip() for c in row] for row in reader if any(cell.strip() for cell in row) ]
        if not rows:
            return

        # Detect the header row robustly
        header_row_idx = 0
        detected = False
        for idx, row in enumerate(rows[:20]):  # scan first 20 lines for a real header
            lower = [c.lower() for c in row]
            if ("mark" in lower and "number" in lower) or (
                any(x in lower for x in ["name", "tag"]) and any(x in lower for x in ["type", "unit type"])  # type schedule
            ):
                header_row_idx = idx
                detected = True
                break
        if not detected:
            # Fallback to first row
            header_row_idx = 0

        header = rows[header_row_idx]
        data_rows = rows[header_row_idx + 1 :]
        header_lower = [h.lower() for h in header]

        def find_idx(keys: List[str]) -> int | None:
            for key in keys:
                if key in header_lower:
                    return header_lower.index(key)
            return None

        # Try conventional mapping first
        idx_name = find_idx(["name", "tag", "id"])  # typical naming column
        idx_type = find_idx(["type", "unit type", "unit"]) 
        idx_cfm = find_idx(["cfm", "airflow", "supply cfm"]) 
        idx_esp = find_idx(["esp", "external static", "static pressure", "inwg", "in. w.g."])
        idx_mfr = find_idx(["manufacturer", "mfr"]) 
        idx_model = find_idx(["model", "model number"]) 

        # Sound performance style
        idx_mark = find_idx(["mark"]) 
        idx_number = find_idx(["number"]) 

        # Build frequency blocks (Inlet, Radiated, Outlet) by scanning header for repeated 63..8k sequences
        def norm_band(tok: str) -> str | None:
            t = tok.lower().strip()
            if t in {"63", "125", "250", "500"}:
                return t
            if t in {"1k", "1000"}:
                return "1000"
            if t in {"2k", "2000"}:
                return "2000"
            if t in {"4k", "4000"}:
                return "4000"
            if t in {"8k", "8000"}:
                return "8000"
            return None

        band_order = ["63", "125", "250", "500", "1000", "2000", "4000", "8000"]
        band_tokens: list[tuple[int, str]] = []
        for i, h in enumerate(header_lower):
            nb = norm_band(h)
            if nb:
                band_tokens.append((i, nb))
        # Group into blocks starting at '63'
        blocks: list[list[tuple[int, str]]] = []
        current: list[tuple[int, str]] = []
        for idx, b in band_tokens:
            if b == "63" and current:
                # Start of next block
                blocks.append(current)
                current = [(idx, b)]
            else:
                current.append((idx, b))
        if current:
            blocks.append(current)
        # Filter blocks to band sequences of at least 5 and map to indices by band
        band_blocks: list[dict[str, int]] = []
        for block in blocks:
            mapping: dict[str, int] = {}
            for idx, b in block:
                if b not in mapping:  # keep first occurrence
                    mapping[b] = idx
            # Ensure order includes at least half of bands; accept
            if len([k for k in mapping if k in band_order]) >= 5:
                band_blocks.append(mapping)
        # Cap to three blocks total (many schedules have exactly three sections)
        if len(band_blocks) > 3:
            band_blocks = band_blocks[:3]

        # Try to label blocks using keywords seen in surrounding header context rows
        labeled_blocks: dict[str, dict[str, int]] = {}
        if band_blocks:
            try:
                # Use up to 3 rows above the header for context keywords
                context_start = max(0, header_row_idx - 3)
                context_rows = rows[context_start : header_row_idx + 1]
                # Precompute centers for each block
                block_centers = []
                for blk in band_blocks:
                    idxs = [v for v in blk.values()]
                    center = sum(idxs) / max(1, len(idxs))
                    block_centers.append(center)
                # Scan for keywords and assign closest block
                keyword_map = {
                    'inlet': 'inlet',
                    'radiated': 'radiated',
                    'outlet': 'outlet',
                }
                best_for_label: dict[str, tuple[int, dict[str, int]]] = {}
                for ctx in context_rows:
                    ctx_lower = [str(t).strip().lower() for t in ctx]
                    for j, tok in enumerate(ctx_lower):
                        if tok in keyword_map:
                            # Find nearest block by index distance to center
                            distances = [abs(j - c) for c in block_centers]
                            nearest = int(min(range(len(distances)), key=lambda k: distances[k]))
                            label = keyword_map[tok]
                            # Keep the closest occurrence per label
                            if (label not in best_for_label) or (distances[nearest] < abs(best_for_label[label][0] - block_centers[nearest])):
                                best_for_label[label] = (j, band_blocks[nearest])
                for lab, (_pos, blk) in best_for_label.items():
                    labeled_blocks[lab] = blk
            except Exception:
                pass

        imported_count = 0
        session = get_session()
        try:
            for row in data_rows:
                # Prefer conventional schedule
                name = row[idx_name].strip() if idx_name is not None and idx_name < len(row) else ""
                unit_type = row[idx_type].strip() if idx_type is not None and idx_type < len(row) else ""

                # If not available, synthesize from MARK/NUMBER
                if not name and (idx_mark is not None or idx_number is not None):
                    mark = row[idx_mark].strip() if idx_mark is not None and idx_mark < len(row) else ""
                    number = row[idx_number].strip() if idx_number is not None and idx_number < len(row) else ""
                    # Clean mark to alpha tokens like AHU, RF, EF, DOAS, TF, CHILLER
                    mark_clean = "".join(ch for ch in mark if ch.isalnum() or ch in ("-", "_"))
                    number_clean = "".join(ch for ch in number if ch.isalnum() or ch in ("-", "_"))
                    if mark_clean and number_clean:
                        name = f"{mark_clean}-{number_clean}"
                        unit_type = mark_clean
                    elif mark_clean:
                        name = mark_clean
                        unit_type = mark_clean

                if not name:
                    # Skip rows without an identifiable name
                    continue

                unit = MechanicalUnit(
                    project_id=self.project_id,
                    name=name,
                    unit_type=unit_type or None,
                    manufacturer=(row[idx_mfr].strip() if idx_mfr is not None and idx_mfr < len(row) else None) or None,
                    model_number=(row[idx_model].strip() if idx_model is not None and idx_model < len(row) else None) or None,
                )

                # Parse numeric fields with tolerance
                def as_float(val: str) -> float | None:
                    try:
                        cleaned = (
                            val.replace(",", "")
                            .replace("CFM", "")
                            .replace("cfm", "")
                            .replace("inwg", "")
                            .replace("in. w.g.", "")
                            .strip()
                        )
                        return float(cleaned)
                    except Exception:
                        return None

                unit.airflow_cfm = as_float(row[idx_cfm]) if idx_cfm is not None and idx_cfm < len(row) else None
                unit.external_static_inwg = as_float(row[idx_esp]) if idx_esp is not None and idx_esp < len(row) else None

                # Frequency preview: if we detected blocks, assign them to inlet/radiated/outlet
                def pick_val(i: int | None) -> str:
                    return row[i] if i is not None and i < len(row) else ""
                if band_blocks:
                    try:
                        import json
                        def build_json(mapping: dict[str, int]) -> str:
                            data = {b: pick_val(mapping.get(b)) for b in band_order}
                            # remove empties
                            data = {k: v for k, v in data.items() if v}
                            return json.dumps(data) if data else None
                        if labeled_blocks:
                            if 'inlet' in labeled_blocks:
                                unit.inlet_levels_json = build_json(labeled_blocks['inlet'])
                            if 'radiated' in labeled_blocks:
                                unit.radiated_levels_json = build_json(labeled_blocks['radiated'])
                            if 'outlet' in labeled_blocks:
                                unit.outlet_levels_json = build_json(labeled_blocks['outlet'])
                        else:
                            # Fallback: left-to-right
                            if len(band_blocks) >= 1:
                                unit.inlet_levels_json = build_json(band_blocks[0])
                            if len(band_blocks) >= 2:
                                unit.radiated_levels_json = build_json(band_blocks[1])
                            if len(band_blocks) >= 3:
                                unit.outlet_levels_json = build_json(band_blocks[2])
                            # If only one block detected, assume outlet
                            if len(band_blocks) == 1 and unit.outlet_levels_json is None:
                                unit.outlet_levels_json = unit.inlet_levels_json
                                unit.inlet_levels_json = None
                    except Exception:
                        pass
                else:
                    # Single set detected; store as outlet for backward compatibility
                    bands = {b: pick_val(find_idx([b])) for b in band_order}
                    if any(v for v in bands.values()):
                        try:
                            import json
                            unit.outlet_levels_json = json.dumps({k: v for k, v in bands.items() if v})
                        except Exception:
                            unit.outlet_levels_json = None

                # Collect leftover text as notes for traceability
                leftover_pairs = []
                for i, cell in enumerate(row):
                    freq_indices = set()
                    for blk in band_blocks:
                        for v in blk.values():
                            freq_indices.add(v)
                    if i in {c for c in [idx_name, idx_type, idx_cfm, idx_esp, idx_mfr, idx_model, idx_mark, idx_number] if c is not None} or i in freq_indices:
                        continue
                    if i < len(header) and cell:
                        leftover_pairs.append(f"{header[i]}: {cell}")
                unit.notes = " | ".join(leftover_pairs) if leftover_pairs else None

                session.add(unit)
                imported_count += 1

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        # Provide quick feedback in UI
        QMessageBox.information(self, "Import", f"Imported {imported_count} mechanical units from CSV.")


