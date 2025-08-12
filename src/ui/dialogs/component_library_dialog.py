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
)
from PySide6.QtCore import Qt

from models import get_session
from models.mechanical import MechanicalUnit, NoiseSource


class ComponentLibraryDialog(QDialog):
    """Project-level component library management dialog."""

    def __init__(self, parent=None, project_id: int | None = None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("Component Library")
        self.resize(700, 500)
        self.setModal(True)

        self._build_ui()
        self.refresh_lists()

    # UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        tabs = QTabWidget()

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
        left_v.addWidget(self.mechanical_list)
        mech_split.addWidget(left_container)

        # Right preview
        right_container = QWidget()
        right_v = QVBoxLayout(right_container)
        freq_group = QGroupBox("Frequency Preview (Sound Power Levels)")
        freq_v = QVBoxLayout()
        self.freq_table = QTableWidget(8, 4)
        self.freq_table.setHorizontalHeaderLabels(["Band (Hz)", "Inlet", "Radiated", "Outlet"])
        bands_order = ["63","125","250","500","1000","2000","4000","8000"]
        for i, b in enumerate(bands_order):
            self.freq_table.setItem(i, 0, QTableWidgetItem(b))
            for j in range(1,4):
                self.freq_table.setItem(i, j, QTableWidgetItem(""))
        self.freq_table.horizontalHeader().setStretchLastSection(True)
        freq_v.addWidget(self.freq_table)
        freq_group.setLayout(freq_v)
        right_v.addWidget(freq_group)
        mech_split.addWidget(right_container)

        mech_layout.addWidget(mech_split)

        # Update preview/tooltip when selection changes
        self.mechanical_list.itemSelectionChanged.connect(self._on_mech_selection_changed)

        mech_btns = QHBoxLayout()
        self.import_btn = QPushButton("Import Mechanical Schedule from Image")
        self.import_btn.clicked.connect(self.import_mechanical_schedule_from_image)
        mech_btns.addWidget(self.import_btn)
        mech_btns.addStretch()
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

        layout.addWidget(tabs)

        # Close button
        close_btns = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btns.addStretch()
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
            bands_order = ["63","125","250","500","1000","2000","4000","8000"]
            def fill_column(json_str: str | None, col: int) -> None:
                if not json_str:
                    for r in range(len(bands_order)):
                        self.freq_table.item(r, col).setText("")
                    return
                try:
                    data = json.loads(json_str)
                except Exception:
                    data = {}
                for r, band in enumerate(bands_order):
                    val = data.get(band, "")
                    self.freq_table.item(r, col).setText(str(val) if val is not None else "")

            # Fill preview columns
            fill_column(getattr(unit, 'inlet_levels_json', None), 1)
            fill_column(getattr(unit, 'radiated_levels_json', None), 2)
            fill_column(getattr(unit, 'outlet_levels_json', None), 3)
        except Exception:
            self._clear_freq_preview()

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
            self._import_csv_into_mechanical_units(csv_path)
            QMessageBox.information(self, "Import Complete", "Mechanical schedule imported successfully.")
            self.refresh_lists()
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import CSV into database:\n{e}")

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
        idx_type = find_idx(["type", "unit type"]) 
        idx_cfm = find_idx(["cfm", "airflow", "supply cfm"]) 
        idx_esp = find_idx(["esp", "external static", "static pressure", "inwg", "in. w.g."])
        idx_mfr = find_idx(["manufacturer", "mfr"]) 
        idx_model = find_idx(["model", "model number"]) 

        # Sound performance style
        idx_mark = find_idx(["mark"]) 
        idx_number = find_idx(["number"]) 
        # Frequency columns (accept 1k/1K etc.)
        idx_63 = find_idx(["63"]) 
        idx_125 = find_idx(["125"]) 
        idx_250 = find_idx(["250"]) 
        idx_500 = find_idx(["500"]) 
        idx_1k = find_idx(["1k", "1000"]) 
        idx_2k = find_idx(["2k", "2000"]) 
        idx_4k = find_idx(["4k", "4000"]) 
        idx_8k = find_idx(["8k", "8000"]) 

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

                # Frequency preview as JSON strings (only "outlet" style here since schedule varies)
                # We'll store whichever bands are found under 'outlet_levels_json'
                def pick_val(i: int | None) -> str:
                    return row[i] if i is not None and i < len(row) else ""
                bands = {
                    "63": pick_val(idx_63),
                    "125": pick_val(idx_125),
                    "250": pick_val(idx_250),
                    "500": pick_val(idx_500),
                    "1000": pick_val(idx_1k),
                    "2000": pick_val(idx_2k),
                    "4000": pick_val(idx_4k),
                    "8000": pick_val(idx_8k),
                }
                # If at least one band has data, serialize
                if any(v for v in bands.values()):
                    try:
                        import json
                        unit.outlet_levels_json = json.dumps(bands)
                    except Exception:
                        unit.outlet_levels_json = None

                # Collect leftover text as notes for traceability
                leftover_pairs = []
                for i, cell in enumerate(row):
                    if i in {c for c in [idx_name, idx_type, idx_cfm, idx_esp, idx_mfr, idx_model, idx_mark, idx_number, idx_63, idx_125, idx_250, idx_500, idx_1k, idx_2k, idx_4k, idx_8k] if c is not None}:
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


