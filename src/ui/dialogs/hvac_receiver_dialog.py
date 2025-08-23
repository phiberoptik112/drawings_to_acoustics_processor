"""
HVAC Receiver Analysis Dialog - Per-space receiver configuration and background noise calculation
"""

from typing import List
import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox, QComboBox,
    QTextEdit, QGroupBox, QWidget, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt

from models import get_session
from models.space import Space
from models.hvac import HVACPath, HVACSegment, HVACReceiverResult
from sqlalchemy.orm import selectinload

from calculations.hvac_path_calculator import HVACPathCalculator
from calculations.receiver_room_sound_correction_calculations import (
    ReceiverRoomSoundCorrection,
)
from calculations.hvac_noise_engine import HVACNoiseEngine


class HVACReceiverDialog(QDialog):
    """Dialog to analyze receiver position for a space and combined HVAC noise."""

    def __init__(self, parent: QWidget, space_id: int):
        super().__init__(parent)
        self.space_id = space_id
        self.space = None
        self.paths: List[HVACPath] = []
        self.path_calculator = HVACPathCalculator()
        self.room_calc = ReceiverRoomSoundCorrection()
        self.engine = HVACNoiseEngine()
        self._latest_results = None  # Stored after successful calculation

        self._load_space()
        self._init_ui()

    # --- Data loading ---
    def _load_space(self) -> None:
        session = get_session()
        try:
            self.space = (
                session.query(Space)
                .options(selectinload(Space.hvac_paths).selectinload(HVACPath.segments))
                .filter(Space.id == self.space_id)
                .first()
            )
            self.paths = list(self.space.hvac_paths) if self.space else []
        finally:
            session.close()

    # --- UI ---
    def _init_ui(self) -> None:
        self.setWindowTitle("Edit Space HVAC Receiver")
        self.resize(900, 700)

        layout = QVBoxLayout()

        # Space summary
        info_group = QGroupBox("Space Summary")
        info_form = QFormLayout()
        info_form.addRow("Space:", QLabel(self.space.name if self.space else ""))
        volume_val = self.space.volume if (self.space and self.space.volume) else 0.0
        info_form.addRow("Volume (ft³):", QLabel(f"{volume_val:,.0f}"))
        self.target_nc_spin = QDoubleSpinBox()
        self.target_nc_spin.setRange(15, 65)
        self.target_nc_spin.setSingleStep(5.0)
        self.target_nc_spin.setValue(35.0)
        info_form.addRow("Target NC:", self.target_nc_spin)
        info_group.setLayout(info_form)
        layout.addWidget(info_group)

        # Paths table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Path Name", "Type", "Terminal dB(A)", "NC", "Distance (ft)", "Method"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self._populate_table()
        layout.addWidget(self.table)

        # Distributed array parameters (global defaults)
        da_group = QGroupBox("Distributed Array Parameters (when selected)")
        da_form = QFormLayout()
        self.ceiling_height_spin = QDoubleSpinBox()
        self.ceiling_height_spin.setRange(6.0, 30.0)
        self.ceiling_height_spin.setDecimals(1)
        self.ceiling_height_spin.setValue(float(self.space.ceiling_height or 10.0))
        da_form.addRow("Ceiling Height (ft):", self.ceiling_height_spin)
        self.floor_area_spin = QDoubleSpinBox()
        self.floor_area_spin.setRange(50.0, 1000.0)
        self.floor_area_spin.setDecimals(1)
        self.floor_area_spin.setValue(150.0)
        da_form.addRow("Floor Area per Diffuser (ft²):", self.floor_area_spin)
        da_group.setLayout(da_form)
        layout.addWidget(da_group)

        # Results + History (split view)
        splitter = QSplitter(Qt.Horizontal)

        # Left: current calculation results
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        splitter.addWidget(self.results_text)

        # Right: saved calculations history
        history_group = QGroupBox("Saved Calculations")
        history_vbox = QVBoxLayout()
        self.history_table = QTableWidget(0, 12)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "dB(A)", "NC", "Target", "Meets",
            "63", "125", "250", "500", "1000", "2000", "4000",
        ])
        h_header = self.history_table.horizontalHeader()
        h_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, 12):
            h_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        history_vbox.addWidget(self.history_table)
        history_group.setLayout(history_vbox)
        splitter.addWidget(history_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Buttons
        btn_row = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Combined Noise")
        self.calc_btn.clicked.connect(self.calculate_combined_noise)
        btn_row.addWidget(self.calc_btn)
        self.save_btn = QPushButton("Save Calculation Results")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_calculation_results)
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        # Populate saved history table initially
        self._refresh_history_table()

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.paths))
        for row, path in enumerate(self.paths):
            # Fetch latest noise numbers
            try:
                result = self.path_calculator.calculate_path_noise(path.id)
                term_dba = float(result.terminal_noise)
                nc = int(result.nc_rating)
            except Exception:
                term_dba = 0.0
                nc = 0

            name_item = QTableWidgetItem(path.name or "")
            name_item.setData(Qt.UserRole, path.id)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(path.path_type or ""))
            self.table.setItem(row, 2, QTableWidgetItem(f"{term_dba:.1f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"NC-{nc}"))

            # Distance input
            dist_spin = QDoubleSpinBox()
            dist_spin.setRange(1.0, 100.0)
            dist_spin.setDecimals(1)
            # Load persisted distance if available
            try:
                dist_val = float(getattr(path, 'receiver_distance_ft', 0) or 0)
                if dist_val <= 0:
                    dist_val = 10.0
            except Exception:
                dist_val = 10.0
            dist_spin.setValue(dist_val)
            dist_spin.setProperty("path_id", path.id)
            dist_spin.valueChanged.connect(self._on_distance_changed)
            self.table.setCellWidget(row, 4, dist_spin)

            # Method selection
            method_combo = QComboBox()
            method_combo.addItems(["Single Source (Eq27)", "Distributed Array (Eq29)"])
            # Load persisted method if available
            method = (getattr(path, 'receiver_method', '') or '').lower()
            if method.startswith('dist'):
                method_combo.setCurrentIndex(1)
            else:
                method_combo.setCurrentIndex(0)
            method_combo.setProperty("path_id", path.id)
            method_combo.currentIndexChanged.connect(self._on_method_changed)
            self.table.setCellWidget(row, 5, method_combo)

    # --- Handlers to persist per-path receiver settings ---
    def _on_distance_changed(self, value: float) -> None:
        try:
            widget = self.sender()
            path_id = int(widget.property("path_id")) if widget else None
            if not path_id:
                return
            session = get_session()
            try:
                db_path = session.query(HVACPath).filter(HVACPath.id == path_id).first()
                if db_path:
                    db_path.receiver_distance_ft = float(value)
                    session.commit()
            finally:
                session.close()
        except Exception:
            pass

    def _on_method_changed(self, idx: int) -> None:
        try:
            widget = self.sender()
            path_id = int(widget.property("path_id")) if widget else None
            if not path_id:
                return
            method_str = 'single' if idx == 0 else 'distributed'
            session = get_session()
            try:
                db_path = session.query(HVACPath).filter(HVACPath.id == path_id).first()
                if db_path:
                    db_path.receiver_method = method_str
                    session.commit()
            finally:
                session.close()
        except Exception:
            pass

    # --- Calculation ---
    def calculate_combined_noise(self) -> None:
        try:
            if not self.paths:
                self.results_text.setHtml("<i>No HVAC paths assigned to this space.</i>")
                return

            room_volume = float(self.space.volume or 0.0)
            if room_volume <= 0 and self.space.floor_area and self.space.ceiling_height:
                room_volume = float(self.space.floor_area * self.space.ceiling_height)

            # Energy sum per band (7 bands up to 4000 Hz)
            combined_energy = [0.0] * 7

            # Keep track of parameters used per-path for saving
            used_path_params = []

            for row, path in enumerate(self.paths):
                # Get latest spectrum at terminal for this path
                result = self.path_calculator.calculate_path_noise(path.id)
                spectrum = result.segment_results and []  # noqa: keep attribute for clarity
                try:
                    calc = self.path_calculator.noise_calculator.calculate_hvac_path_noise(
                        self.path_calculator.build_path_data_from_db(path)
                    )
                    term_spectrum = calc.get('octave_band_spectrum', [])
                except Exception:
                    term_spectrum = []

                if not term_spectrum:
                    continue

                # Convert to 7 bands (drop 8000 Hz if present)
                lw_spectrum_7 = [float(x) for x in term_spectrum[:7]] if len(term_spectrum) >= 7 else term_spectrum
                if len(lw_spectrum_7) < 7:
                    lw_spectrum_7 = (lw_spectrum_7 + [0.0] * 7)[:7]

                # Determine method/parameters
                dist_spin = self.table.cellWidget(row, 4)
                method_combo = self.table.cellWidget(row, 5)
                distance = float(dist_spin.value()) if isinstance(dist_spin, QDoubleSpinBox) else 10.0
                method_text = method_combo.currentText() if isinstance(method_combo, QComboBox) else "Single Source (Eq27)"

                # Persist current choices
                try:
                    session = get_session()
                    try:
                        db_path = session.query(HVACPath).filter(HVACPath.id == getattr(path, 'id', None)).first()
                        if db_path:
                            db_path.receiver_distance_ft = distance
                            db_path.receiver_method = 'single' if method_text.startswith("Single") else 'distributed'
                            session.commit()
                    finally:
                        session.close()
                except Exception:
                    pass

                if method_text.startswith("Single"):
                    # Use Equation 27 for small rooms by band
                    res = self.room_calc.calculate_octave_band_spectrum(
                        lw_spectrum=lw_spectrum_7,
                        distance=distance,
                        room_volume=max(room_volume, 1.0),
                        method='equation_27',
                    )
                    lp_bands = res.get('sound_pressure_levels', [])
                else:
                    # Distributed array parameters
                    lp_res = self.room_calc.calculate_distributed_array_spectrum(
                        lw_single_spectrum=lw_spectrum_7,
                        ceiling_height=float(self.ceiling_height_spin.value()),
                        floor_area_per_diffuser=float(self.floor_area_spin.value()),
                    )
                    lp_bands = lp_res.get('sound_pressure_levels', [])

                # Energy sum bands
                for i in range(min(7, len(lp_bands))):
                    combined_energy[i] += 10 ** (lp_bands[i] / 10.0)

                used_path_params.append({
                    'path_id': getattr(path, 'id', None),
                    'method': 'single' if method_text.startswith('Single') else 'distributed',
                    'distance_ft': distance,
                })

            # Convert back to dB spectrum
            combined_spectrum_7 = [0.0] * 7
            for i, energy in enumerate(combined_energy):
                combined_spectrum_7[i] = 10 * (0.0 if energy <= 0 else __import__('math').log10(energy))

            # Pad to 8 bands for engine utilities
            spectrum_8 = combined_spectrum_7 + [0.0]
            total_dba = self.engine._calculate_dba_from_spectrum(spectrum_8)
            nc_rating = self.engine._calculate_nc_rating(spectrum_8)

            target_nc = int(self.target_nc_spin.value())
            meets = nc_rating <= target_nc

            html = "<h3>Combined Receiver Background Noise</h3>"
            html += f"<p><b>Total A-weighted Level:</b> {total_dba:.1f} dB(A)<br>"
            html += f"<b>NC Rating:</b> NC-{nc_rating} (Target: NC-{target_nc})<br>"
            html += f"<b>Status:</b> {'✅ Meets target' if meets else '❌ Above target'}</p>"

            # Show band table
            freqs = [63, 125, 250, 500, 1000, 2000, 4000]
            html += "<table border='1' cellpadding='4'><tr><th>Hz</th>" + ''.join(
                f"<th>{f}</th>" for f in freqs
            ) + "</tr>"
            html += "<tr><td>LP (dB)</td>" + ''.join(
                f"<td>{v:.1f}</td>" for v in combined_spectrum_7
            ) + "</tr></table>"

            self.results_text.setHtml(html)

            # Store latest results for saving and enable button
            self._latest_results = {
                'target_nc': target_nc,
                'nc_rating': nc_rating,
                'total_dba': float(total_dba),
                'meets_target': bool(meets),
                'spectrum_7': combined_spectrum_7,
                'room_volume': room_volume,
                'distributed_ceiling_height': float(self.ceiling_height_spin.value()),
                'distributed_floor_area_per_diffuser': float(self.floor_area_spin.value()),
                'path_parameters': used_path_params,
            }
            self.save_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate combined noise:\n{str(e)}")


    def save_calculation_results(self) -> None:
        """Persist the latest calculation results to the database."""
        try:
            if not self._latest_results:
                QMessageBox.information(self, "Save Results", "Run a calculation first.")
                return

            data = self._latest_results
            spectrum = data.get('spectrum_7') or [0.0] * 7

            session = get_session()
            try:
                rec = HVACReceiverResult(
                    space_id=self.space_id,
                    target_nc=float(data.get('target_nc') or 0.0),
                    nc_rating=float(data.get('nc_rating') or 0.0),
                    total_dba=float(data.get('total_dba') or 0.0),
                    meets_target=bool(data.get('meets_target')),
                    lp_63=float(spectrum[0] if len(spectrum) > 0 else 0.0),
                    lp_125=float(spectrum[1] if len(spectrum) > 1 else 0.0),
                    lp_250=float(spectrum[2] if len(spectrum) > 2 else 0.0),
                    lp_500=float(spectrum[3] if len(spectrum) > 3 else 0.0),
                    lp_1000=float(spectrum[4] if len(spectrum) > 4 else 0.0),
                    lp_2000=float(spectrum[5] if len(spectrum) > 5 else 0.0),
                    lp_4000=float(spectrum[6] if len(spectrum) > 6 else 0.0),
                    room_volume=float(data.get('room_volume') or 0.0),
                    distributed_ceiling_height=float(data.get('distributed_ceiling_height') or 0.0),
                    distributed_floor_area_per_diffuser=float(data.get('distributed_floor_area_per_diffuser') or 0.0),
                    path_parameters_json=json.dumps(data.get('path_parameters') or []),
                )
                session.add(rec)

                # Optionally update space NC summary
                try:
                    space = session.query(Space).filter(Space.id == self.space_id).first()
                    if space:
                        space.calculated_nc = float(data.get('nc_rating') or 0.0)
                except Exception:
                    pass

                session.commit()
            finally:
                session.close()

            QMessageBox.information(self, "Save Results", "HVAC receiver results saved.")
            self._refresh_history_table()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save results:\n{str(e)}")

    # --- History table ---
    def _refresh_history_table(self) -> None:
        try:
            session = get_session()
            try:
                rows = (
                    session.query(HVACReceiverResult)
                    .filter(HVACReceiverResult.space_id == self.space_id)
                    .order_by(HVACReceiverResult.calculation_date.desc())
                    .all()
                )
            finally:
                session.close()

            self.history_table.setRowCount(len(rows))
            for r, rec in enumerate(rows):
                date_str = str(getattr(rec, 'calculation_date', '') or '')
                items = [
                    QTableWidgetItem(date_str),
                    QTableWidgetItem(f"{float(getattr(rec, 'total_dba', 0.0)):.1f}"),
                    QTableWidgetItem(f"NC-{int(getattr(rec, 'nc_rating', 0) or 0)}"),
                    QTableWidgetItem(f"NC-{int(getattr(rec, 'target_nc', 0) or 0)}"),
                    QTableWidgetItem("Yes" if getattr(rec, 'meets_target', False) else "No"),
                    QTableWidgetItem(f"{float(getattr(rec, 'lp_63', 0.0)):.1f}"),
                    QTableWidgetItem(f"{float(getattr(rec, 'lp_125', 0.0)):.1f}"),
                    QTableWidgetItem(f"{float(getattr(rec, 'lp_250', 0.0)):.1f}"),
                    QTableWidgetItem(f"{float(getattr(rec, 'lp_500', 0.0)):.1f}"),
                    QTableWidgetItem(f"{float(getattr(rec, 'lp_1000', 0.0)):.1f}"),
                    QTableWidgetItem(f"{float(getattr(rec, 'lp_2000', 0.0)):.1f}"),
                    QTableWidgetItem(f"{float(getattr(rec, 'lp_4000', 0.0)):.1f}"),
                ]
                for c, it in enumerate(items):
                    it.setFlags(it.flags() ^ Qt.ItemIsEditable)
                    self.history_table.setItem(r, c, it)
        except Exception:
            # Non-fatal UI helper
            pass

