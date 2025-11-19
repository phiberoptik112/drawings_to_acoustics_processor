"""
Component Library Dialog
 - Displays Mechanical Units and Noise Sources stored in the project database
 - Provides an "Import Mechanical Schedule from Image" workflow that leverages
   the image->CSV utility and ingests the resulting CSV into the Mechanical
   Units table for the active project.

Still needed:
- Silencer component import - need to differentiate between component type

"""

from __future__ import annotations

import os
import subprocess
import sys
import csv
from typing import List, Union, Optional

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
    QComboBox,
    QGridLayout,
    QCheckBox,
)
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtGui import QColor

from models import get_session
from models.mechanical import MechanicalUnit, NoiseSource
from models.hvac import SilencerProduct
from models.rt60_models import AcousticMaterial, SurfaceCategory, RoomSurfaceInstance
from calculations.hvac_constants import is_valid_cfm_value


class ComponentLibraryDialog(QDialog):
    """Project-level component library management dialog."""
    
    # Signal emitted when library data changes (so parent can refresh if needed)
    library_updated = Signal()

    def __init__(self, parent=None, project_id: Optional[int] = None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("Component Library")
        # Make this a non-modal window so users can reference it while working
        self.setModal(False)
        # Set window flags to make it an independent window that can be arranged freely
        self.setWindowFlags(Qt.Window)
        self.resize(900, 600)
        self.setMinimumSize(1200, 900)

        # Initialize state variables BEFORE building UI and refreshing
        self.freq_dirty = False
        self.acoustic_material_dirty = False
        self.show_only_project_materials = False

        self._build_ui()
        self.refresh_lists()

    # UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        tabs = QTabWidget()
        tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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
        self.mechanical_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        # New orientation: rows = [Inlet, Radiated, Outlet], columns = bands
        self.freq_table = QTableWidget(3, len(self.band_order))
        self.freq_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.freq_table.setHorizontalHeaderLabels(self.band_order)
        self.freq_table.setVerticalHeaderLabels(["Inlet", "Radiated", "Outlet"])
        for r in range(3):
            for c in range(len(self.band_order)):
                self.freq_table.setItem(r, c, QTableWidgetItem(""))
        self.freq_table.horizontalHeader().setStretchLastSection(True)
        # Enable editing on double click
        self.freq_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.freq_table.cellChanged.connect(self._on_freq_cell_changed)
        freq_v.addWidget(self.freq_table)
        freq_group.setLayout(freq_v)
        freq_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # PDF preview group (right in right panel)
        preview_group = QGroupBox("File Preview (PDF)")
        preview_v = QVBoxLayout()
        from drawing.pdf_viewer import PDFViewer
        self.preview_viewer = PDFViewer()
        preview_v.addWidget(self.preview_viewer)
        preview_btns = QHBoxLayout()
        self.load_pdf_btn = QPushButton("Load PDF…")
        self.load_pdf_btn.clicked.connect(self.load_preview_pdf)
        # Selection mode toggles
        self.sel_free_btn = QPushButton("Free Select")
        self.sel_free_btn.setCheckable(True)
        self.sel_free_btn.setChecked(True)
        self.sel_free_btn.clicked.connect(lambda: self.set_preview_selection_mode('free'))
        self.sel_col_btn = QPushButton("Select Column")
        self.sel_col_btn.setCheckable(True)
        self.sel_col_btn.clicked.connect(lambda: self.set_preview_selection_mode('column'))
        self.sel_row_btn = QPushButton("Select Row")
        self.sel_row_btn.setCheckable(True)
        self.sel_row_btn.clicked.connect(lambda: self.set_preview_selection_mode('row'))
        preview_btns.addWidget(self.sel_free_btn)
        preview_btns.addWidget(self.sel_col_btn)
        preview_btns.addWidget(self.sel_row_btn)
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
        self.manual_add_btn = QPushButton("Manual Component Add")
        self.manual_add_btn.setToolTip("Manually add a mechanical component with octave-band data")
        self.manual_add_btn.clicked.connect(self.manual_add_component)
        self.edit_btn = QPushButton("Edit Entry")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_selected_mechanical_unit)
        self.delete_btn = QPushButton("Delete Entry")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_mechanical_unit)
        mech_btns.addWidget(self.import_btn)
        mech_btns.addWidget(self.import_pdf_btn)
        mech_btns.addWidget(self.manual_add_btn)
        mech_btns.addStretch()
        mech_btns.addWidget(self.edit_btn)
        mech_btns.addWidget(self.delete_btn)
        mech_layout.addLayout(mech_btns)
        mech_tab.setLayout(mech_layout)

        # Silencers tab
        silencer_tab = QWidget()
        silencer_layout = QVBoxLayout()
        silencer_split = QSplitter(); silencer_split.setOrientation(Qt.Horizontal)
        # Left: list
        sil_left = QWidget(); sil_left_v = QVBoxLayout(sil_left)
        self.silencer_list = QListWidget()
        sil_left_v.addWidget(self.silencer_list)
        silencer_split.addWidget(sil_left)
        # Right: IL preview table
        sil_right = QWidget(); sil_right_v = QVBoxLayout(sil_right)
        sil_group = QGroupBox("Insertion Loss (dB)")
        sil_group_v = QVBoxLayout()
        self.sil_band_order = ["63","125","250","500","1000","2000","4000","8000"]
        self.sil_table = QTableWidget(1, len(self.sil_band_order))
        self.sil_table.setHorizontalHeaderLabels(self.sil_band_order)
        self.sil_table.setVerticalHeaderLabels(["IL (dB)"])
        for c in range(len(self.sil_band_order)):
            self.sil_table.setItem(0, c, QTableWidgetItem(""))
        self.sil_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.sil_table.cellChanged.connect(lambda _r,_c: self._toggle_silencer_save(True))
        # Allow column selection to target band when importing a single value
        self.sil_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectColumns)
        sil_group_v.addWidget(self.sil_table)
        sil_group.setLayout(sil_group_v)
        sil_right_v.addWidget(sil_group)

        # --- Silencer PDF preview & selection controls ---
        sil_prev_group = QGroupBox("File Preview (PDF)")
        sil_prev_v = QVBoxLayout()
        from drawing.pdf_viewer import PDFViewer
        self.sil_preview_viewer = PDFViewer()
        sil_prev_v.addWidget(self.sil_preview_viewer)
        sil_prev_btns = QHBoxLayout()
        self.sil_sel_free_btn = QPushButton("Free Select"); self.sil_sel_free_btn.setCheckable(True); self.sil_sel_free_btn.setChecked(True)
        self.sil_sel_free_btn.clicked.connect(lambda: self.set_sil_preview_selection_mode('free'))
        self.sil_sel_col_btn = QPushButton("Select Column"); self.sil_sel_col_btn.setCheckable(True)
        self.sil_sel_col_btn.clicked.connect(lambda: self.set_sil_preview_selection_mode('column'))
        self.sil_sel_row_btn = QPushButton("Select Row"); self.sil_sel_row_btn.setCheckable(True)
        self.sil_sel_row_btn.clicked.connect(lambda: self.set_sil_preview_selection_mode('row'))
        self.sil_load_pdf_btn = QPushButton("Load PDF…")
        self.sil_load_pdf_btn.clicked.connect(self.load_silencer_preview_pdf)
        sil_prev_btns.addWidget(self.sil_sel_free_btn)
        sil_prev_btns.addWidget(self.sil_sel_col_btn)
        sil_prev_btns.addWidget(self.sil_sel_row_btn)
        sil_prev_btns.addStretch(); sil_prev_btns.addWidget(self.sil_load_pdf_btn)
        sil_prev_v.addLayout(sil_prev_btns)
        sil_prev_group.setLayout(sil_prev_v)
        sil_right_v.addWidget(sil_prev_group)
        # Buttons
        sil_btns = QHBoxLayout()
        self.add_sil_btn = QPushButton("Add Silencer")
        self.add_sil_btn.clicked.connect(self.add_silencer)
        self.edit_sil_btn = QPushButton("Edit")
        self.edit_sil_btn.setEnabled(False)
        self.edit_sil_btn.clicked.connect(self.edit_selected_silencer)
        self.del_sil_btn = QPushButton("Delete")
        self.del_sil_btn.setEnabled(False)
        self.del_sil_btn.clicked.connect(self.delete_selected_silencer)
        self.save_sil_btn = QPushButton("Save IL Changes")
        self.save_sil_btn.setEnabled(False)
        self.save_sil_btn.clicked.connect(self.save_silencer_il_changes)
        # Import controls for silencer
        self.sil_import_row_btn = QPushButton("Import Selected Row")
        self.sil_import_row_btn.setToolTip("Select a row region across 8 bands; imports IL values")
        self.sil_import_row_btn.clicked.connect(self.import_silencer_selected_row)
        self.sil_import_col_btn = QPushButton("Import Selected Column")
        self.sil_import_col_btn.setToolTip("Select a single cell/column region; imports value into the selected band column")
        self.sil_import_col_btn.clicked.connect(self.import_silencer_selected_column)
        sil_btns.addWidget(self.add_sil_btn)
        sil_btns.addWidget(self.edit_sil_btn)
        sil_btns.addWidget(self.del_sil_btn)
        sil_btns.addStretch()
        sil_btns.addWidget(self.sil_import_row_btn)
        sil_btns.addWidget(self.sil_import_col_btn)
        sil_btns.addWidget(self.save_sil_btn)
        sil_right_v.addLayout(sil_btns)
        silencer_split.addWidget(sil_right)
        silencer_layout.addWidget(silencer_split)
        silencer_tab.setLayout(silencer_layout)

        # Acoustic Treatment tab
        acoustic_tab = self.create_acoustic_treatment_tab()
        
        tabs.addTab(mech_tab, "Mechanical Units")
        tabs.addTab(silencer_tab, "Silencers")
        tabs.addTab(acoustic_tab, "Acoustic Treatment")

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

        # Column import controls under right panel
        column_tools = QHBoxLayout()
        column_tools.addWidget(QLabel("PDF Region Import:"))
        self.column_label_edit = QLineEdit()
        self.column_label_edit.setPlaceholderText("Column label (e.g., Inlet 500, Outlet 1K)")
        self.import_col_btn = QPushButton("Import Selected Column")
        self.import_col_btn.setToolTip("Draw a rectangle in File Preview over a single column, then click to OCR just that area")
        self.import_col_btn.clicked.connect(self.import_selected_pdf_column)
        self.import_row_btn = QPushButton("Import Selected Row")
        self.import_row_btn.setToolTip("Draw a rectangle over a single unit row across 8 bands; label must include Inlet, Radiated, or Outlet")
        self.import_row_btn.clicked.connect(self.import_selected_pdf_row)
        column_tools.addWidget(self.column_label_edit)
        column_tools.addWidget(self.import_col_btn)
        column_tools.addWidget(self.import_row_btn)
        right_v.addLayout(column_tools)

    def create_acoustic_treatment_tab(self) -> QWidget:
        """Create the Acoustic Treatment tab with materials and schedules side-by-side"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Main horizontal splitter: Materials (left) | Schedules (right)
        main_splitter = QSplitter()
        main_splitter.setOrientation(Qt.Horizontal)
        
        # ===== LEFT SECTION: Acoustic Materials =====
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        
        # Filter checkbox
        filter_layout = QHBoxLayout()
        self.materials_filter_checkbox = QCheckBox("Show only project materials")
        self.materials_filter_checkbox.setChecked(False)
        self.materials_filter_checkbox.stateChanged.connect(self._on_acoustic_material_filter_changed)
        filter_layout.addWidget(self.materials_filter_checkbox)
        filter_layout.addStretch()
        left_layout.addLayout(filter_layout)
        
        # Materials list
        left_layout.addWidget(QLabel("Acoustic Materials"))
        self.acoustic_materials_list = QListWidget()
        self.acoustic_materials_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.acoustic_materials_list.itemSelectionChanged.connect(self._on_acoustic_material_selected)
        self.acoustic_materials_list.itemSelectionChanged.connect(self._toggle_acoustic_material_buttons)
        left_layout.addWidget(self.acoustic_materials_list)
        
        # Absorption coefficients table
        abs_group = QGroupBox("Absorption Coefficients (Sabine)")
        abs_layout = QVBoxLayout()
        self.acoustic_band_order = ["125", "250", "500", "1000", "2000", "4000"]
        self.acoustic_absorption_table = QTableWidget(1, 7)  # 6 bands + NRC
        headers = self.acoustic_band_order + ["NRC"]
        self.acoustic_absorption_table.setHorizontalHeaderLabels(headers)
        self.acoustic_absorption_table.setVerticalHeaderLabels(["Absorption"])
        self.acoustic_absorption_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.acoustic_absorption_table.setMaximumHeight(100)
        # Initialize cells
        for c in range(7):
            item = QTableWidgetItem("")
            self.acoustic_absorption_table.setItem(0, c, item)
            # Make NRC column (last) read-only with grey background
            if c == 6:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setBackground(QColor(240, 240, 240))
        self.acoustic_absorption_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.acoustic_absorption_table.cellChanged.connect(self._on_acoustic_material_cell_changed)
        abs_layout.addWidget(self.acoustic_absorption_table)
        abs_group.setLayout(abs_layout)
        left_layout.addWidget(abs_group)
        
        # Material buttons
        material_btns = QHBoxLayout()
        self.manual_add_material_btn = QPushButton("Manual Treatment Add")
        self.manual_add_material_btn.clicked.connect(self.manual_add_acoustic_material)
        self.edit_material_btn = QPushButton("Edit")
        self.edit_material_btn.setEnabled(False)
        self.edit_material_btn.clicked.connect(self.edit_selected_acoustic_material)
        self.delete_material_btn = QPushButton("Delete")
        self.delete_material_btn.setEnabled(False)
        self.delete_material_btn.clicked.connect(self.delete_selected_acoustic_material)
        self.save_material_btn = QPushButton("Save Changes")
        self.save_material_btn.setEnabled(False)
        self.save_material_btn.clicked.connect(self.save_acoustic_material_changes)
        material_btns.addWidget(self.manual_add_material_btn)
        material_btns.addWidget(self.edit_material_btn)
        material_btns.addWidget(self.delete_material_btn)
        material_btns.addStretch()
        # Add database setup button
        self.db_setup_btn = QPushButton("Database Setup...")
        self.db_setup_btn.setToolTip("View and configure materials database sources")
        self.db_setup_btn.clicked.connect(self.open_materials_database_setup)
        material_btns.addWidget(self.db_setup_btn)
        material_btns.addWidget(self.save_material_btn)
        left_layout.addLayout(material_btns)
        
        main_splitter.addWidget(left_container)
        
        # ===== RIGHT SECTION: Material Schedules =====
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        # Create vertical splitter for resizable list and preview sections
        right_splitter = QSplitter()
        right_splitter.setOrientation(Qt.Vertical)
        
        # Top section: Material schedules list
        schedules_list_container = QWidget()
        schedules_list_layout = QVBoxLayout(schedules_list_container)
        schedules_list_layout.setContentsMargins(0, 0, 0, 0)
        schedules_list_layout.addWidget(QLabel("Material Schedules by Drawing Set"))
        self.material_schedules_list = QListWidget()
        self.material_schedules_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.material_schedules_list.itemSelectionChanged.connect(self.on_material_schedule_selected)
        schedules_list_layout.addWidget(self.material_schedules_list)
        right_splitter.addWidget(schedules_list_container)
        
        # Bottom section: PDF Preview
        preview_group = QGroupBox("Material Schedule Preview")
        preview_layout = QVBoxLayout()
        
        from drawing.pdf_viewer import PDFViewer
        self.material_schedule_viewer = PDFViewer()
        preview_layout.addWidget(self.material_schedule_viewer)
        
        # Load PDF button
        load_pdf_row = QHBoxLayout()
        load_pdf_row.addStretch()
        self.load_material_pdf_btn = QPushButton("Load PDF…")
        self.load_material_pdf_btn.clicked.connect(self.load_material_schedule_pdf)
        load_pdf_row.addWidget(self.load_material_pdf_btn)
        preview_layout.addLayout(load_pdf_row)
        
        preview_group.setLayout(preview_layout)
        right_splitter.addWidget(preview_group)
        
        # Set initial splitter proportions (40% list, 60% preview)
        right_splitter.setStretchFactor(0, 2)
        right_splitter.setStretchFactor(1, 3)
        
        # Add splitter to main layout
        right_layout.addWidget(right_splitter)
        
        # Schedule management buttons
        schedule_btns = QHBoxLayout()
        add_schedule_btn = QPushButton("Add Schedule")
        add_schedule_btn.clicked.connect(self.add_material_schedule)
        edit_schedule_btn = QPushButton("Edit")
        edit_schedule_btn.clicked.connect(self.edit_material_schedule)
        self.edit_material_schedule_btn = edit_schedule_btn
        self.edit_material_schedule_btn.setEnabled(False)
        delete_schedule_btn = QPushButton("Delete")
        delete_schedule_btn.clicked.connect(self.delete_material_schedule)
        self.delete_material_schedule_btn = delete_schedule_btn
        self.delete_material_schedule_btn.setEnabled(False)
        compare_btn = QPushButton("Compare Schedules")
        compare_btn.setToolTip("Compare material schedules from different drawing sets side-by-side")
        compare_btn.clicked.connect(self.compare_material_schedules)
        schedule_btns.addWidget(add_schedule_btn)
        schedule_btns.addWidget(edit_schedule_btn)
        schedule_btns.addWidget(delete_schedule_btn)
        schedule_btns.addStretch()
        schedule_btns.addWidget(compare_btn)
        right_layout.addLayout(schedule_btns)
        
        main_splitter.addWidget(right_container)
        
        # Set splitter proportions - equal split
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(main_splitter)
        widget.setLayout(layout)
        
        return widget
    
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
            silencers: List[SilencerProduct] = (
                session.query(SilencerProduct).order_by(SilencerProduct.manufacturer, SilencerProduct.model_number).all()
            )
            self.mechanical_list.clear()
            for u in units:
                cfm_text = f"{u.airflow_cfm:.0f}" if u.airflow_cfm else "—"
                text = f"{u.name} ({u.unit_type or 'unit'}) — {cfm_text} CFM"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, u.id)
                self.mechanical_list.addItem(item)
            # Clear preview
            self._clear_freq_preview()
            if hasattr(self, 'silencer_list'):
                self.silencer_list.clear()
                for s in silencers:
                    text = f"{s.manufacturer} {s.model_number} ({s.silencer_type or ''})"
                    item = QListWidgetItem(text)
                    item.setData(Qt.UserRole, s.id)
                    self.silencer_list.addItem(item)
                # wire selection change
                try:
                    self.silencer_list.itemSelectionChanged.disconnect()
                except Exception:
                    pass
                self.silencer_list.itemSelectionChanged.connect(self._on_silencer_selected)
            session.close()
            
            # Refresh acoustic materials
            self.refresh_acoustic_materials()
            
            # Refresh material schedules
            self.refresh_material_schedules()
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load component library:\n{e}")

    def _toggle_silencer_save(self, on: bool) -> None:
        if hasattr(self, 'save_sil_btn'):
            self.save_sil_btn.setEnabled(bool(on))

    def _on_silencer_selected(self) -> None:
        item = self.silencer_list.currentItem() if hasattr(self, 'silencer_list') else None
        if not item:
            self._toggle_silencer_save(False)
            return
        sid = item.data(Qt.UserRole)
        try:
            session = get_session()
            s = session.query(SilencerProduct).filter(SilencerProduct.id == sid).first()
            session.close()
            if not s:
                return
            # Fill IL table
            il_values = [
                s.insertion_loss_63, s.insertion_loss_125, s.insertion_loss_250, s.insertion_loss_500,
                s.insertion_loss_1000, s.insertion_loss_2000, s.insertion_loss_4000, s.insertion_loss_8000
            ]
            for c, val in enumerate(il_values):
                self.sil_table.item(0, c).setText("" if val is None else str(val))
            self._toggle_silencer_save(False)
            # Toggle buttons
            self.edit_sil_btn.setEnabled(True)
            self.del_sil_btn.setEnabled(True)
        except Exception:
            pass

    def add_silencer(self) -> None:
        dlg = SilencerEditDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_lists()
            self.library_updated.emit()

    def edit_selected_silencer(self) -> None:
        item = self.silencer_list.currentItem()
        if not item:
            return
        sid = item.data(Qt.UserRole)
        session = get_session()
        s = session.query(SilencerProduct).filter(SilencerProduct.id == sid).first()
        session.close()
        if not s:
            return
        dlg = SilencerEditDialog(self, s)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_lists()
            self.library_updated.emit()

    def delete_selected_silencer(self) -> None:
        item = self.silencer_list.currentItem()
        if not item:
            return
        sid = item.data(Qt.UserRole)
        if QMessageBox.question(self, "Delete Silencer", "Delete selected silencer?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            session = get_session()
            s = session.query(SilencerProduct).filter(SilencerProduct.id == sid).first()
            if s:
                session.delete(s)
                session.commit()
            session.close()
            self.refresh_lists()
            self.library_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete silencer:\n{e}")

    def save_silencer_il_changes(self) -> None:
        item = self.silencer_list.currentItem()
        if not item:
            return
        sid = item.data(Qt.UserRole)
        try:
            session = get_session()
            s = session.query(SilencerProduct).filter(SilencerProduct.id == sid).first()
            if not s:
                session.close(); return
            # Read table values
            def as_float(txt):
                try:
                    return float(txt)
                except Exception:
                    return None
            vals = [as_float(self.sil_table.item(0, c).text().strip()) for c in range(len(self.sil_band_order))]
            s.insertion_loss_63 = vals[0]
            s.insertion_loss_125 = vals[1]
            s.insertion_loss_250 = vals[2]
            s.insertion_loss_500 = vals[3]
            s.insertion_loss_1000 = vals[4]
            s.insertion_loss_2000 = vals[5]
            s.insertion_loss_4000 = vals[6]
            s.insertion_loss_8000 = vals[7]
            session.commit(); session.close()
            self._toggle_silencer_save(False)
            self.library_updated.emit()
            QMessageBox.information(self, "Silencer", "Insertion loss values saved.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save insertion loss:\n{e}")

    def load_silencer_preview_pdf(self):
        pdf_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Preview", "", "PDF Files (*.pdf);;All Files (*)")
        if not pdf_path:
            return
        try:
            self.sil_preview_viewer.load_pdf(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Preview Error", f"Failed to load PDF:\n{e}")

    def set_sil_preview_selection_mode(self, mode: str):
        if mode == 'free':
            self.sil_sel_free_btn.setChecked(True); self.sil_sel_col_btn.setChecked(False); self.sil_sel_row_btn.setChecked(False)
        elif mode == 'column':
            self.sil_sel_free_btn.setChecked(False); self.sil_sel_col_btn.setChecked(True); self.sil_sel_row_btn.setChecked(False)
        elif mode == 'row':
            self.sil_sel_free_btn.setChecked(False); self.sil_sel_col_btn.setChecked(False); self.sil_sel_row_btn.setChecked(True)
        try:
            self.sil_preview_viewer.set_selection_mode(mode)
        except Exception:
            pass

    def import_silencer_selected_row(self):
        item = self.silencer_list.currentItem()
        if not item:
            QMessageBox.information(self, "Silencer Row Import", "Select a silencer first.")
            return
        if not getattr(self.sil_preview_viewer, 'pdf_document', None):
            QMessageBox.information(self, "Silencer Row Import", "Load a PDF in the silencer preview.")
            return
        sel = getattr(self.sil_preview_viewer, 'selection_rect_pdf', None)
        if not sel:
            QMessageBox.information(self, "Silencer Row Import", "Drag to select a row region across 8 bands.")
            return
        try:
            import tempfile, os, sys, re, csv as csvmod
            import fitz
            page = self.sil_preview_viewer.pdf_document[self.sil_preview_viewer.current_page]
            x0,y0,x1,y1 = sel
            rect = fitz.Rect(x0,y0,x1,y1)
            zoom = 300.0/72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom,zoom), clip=rect)
            with tempfile.TemporaryDirectory() as td:
                img_path = os.path.join(td,'row.png'); csv_path = os.path.join(td,'row.csv'); pix.save(img_path)
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..','calculations','image_table_to_csv.py'))
                res = subprocess.run([sys.executable, script_path, '--image', img_path, '--output', csv_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    raise RuntimeError(res.stderr or 'OCR failed')
                tokens = []
                with open(csv_path, newline='', encoding='utf-8') as f:
                    reader = csvmod.reader(f)
                    for r in reader:
                        tokens.extend([c.strip() for c in r if c and c.strip()])
                nums = [t for t in tokens if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", t)]
                vals8 = nums[:8]
                if not vals8:
                    QMessageBox.information(self, 'Silencer Row Import', 'No numeric values detected.')
                    return
                for c, v in enumerate(vals8):
                    if c < len(self.sil_band_order):
                        self.sil_table.item(0, c).setText(v)
                self._toggle_silencer_save(True)
        except Exception as e:
            QMessageBox.critical(self, "Silencer Row Import", f"Failed: {e}")

    def import_silencer_selected_column(self):
        item = self.silencer_list.currentItem()
        if not item:
            QMessageBox.information(self, "Silencer Column Import", "Select a silencer first.")
            return
        if not getattr(self.sil_preview_viewer, 'pdf_document', None):
            QMessageBox.information(self, "Silencer Column Import", "Load a PDF in the silencer preview.")
            return
        sel = getattr(self.sil_preview_viewer, 'selection_rect_pdf', None)
        if not sel:
            QMessageBox.information(self, "Silencer Column Import", "Drag to select a single cell/column region.")
            return
        selected_cols = set([rng.leftColumn() for rng in self.sil_table.selectedRanges()])
        if not selected_cols:
            QMessageBox.information(self, "Silencer Column Import", "Select a target band column in the IL table first.")
            return
        target_col = list(sorted(selected_cols))[0]
        try:
            import tempfile, os, sys, re, csv as csvmod
            import fitz
            page = self.sil_preview_viewer.pdf_document[self.sil_preview_viewer.current_page]
            x0,y0,x1,y1 = sel
            rect = fitz.Rect(x0,y0,x1,y1)
            zoom = 300.0/72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom,zoom), clip=rect)
            with tempfile.TemporaryDirectory() as td:
                img_path = os.path.join(td,'col.png'); csv_path = os.path.join(td,'col.csv'); pix.save(img_path)
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..','calculations','image_table_to_csv.py'))
                res = subprocess.run([sys.executable, script_path, '--image', img_path, '--output', csv_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    raise RuntimeError(res.stderr or 'OCR failed')
                value = None
                with open(csv_path, newline='', encoding='utf-8') as f:
                    reader = csvmod.reader(f)
                    for r in reader:
                        for c in r:
                            s = c.strip()
                            if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", s):
                                value = s; break
                        if value is not None:
                            break
                if value is None:
                    QMessageBox.information(self, 'Silencer Column Import', 'No numeric value found in selection.')
                    return
                self.sil_table.item(0, target_col).setText(value)
                self._toggle_silencer_save(True)
        except Exception as e:
            QMessageBox.critical(self, "Silencer Column Import", f"Failed: {e}")

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
            for r in range(self.freq_table.rowCount()):
                for c in range(self.freq_table.columnCount()):
                    item = self.freq_table.item(r, c)
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
            def fill_row(json_str: Optional[str], row_index: int) -> None:
                # row_index: 0 Inlet, 1 Radiated, 2 Outlet
                for c in range(self.freq_table.columnCount()):
                    self.freq_table.item(row_index, c).setText("")
                if not json_str:
                    return
                try:
                    data = json.loads(json_str)
                except Exception:
                    data = {}
                for c, band in enumerate(self.band_order):
                    val = data.get(band, "")
                    self.freq_table.item(row_index, c).setText(str(val) if val is not None else "")

            # Fill preview rows
            fill_row(getattr(unit, 'inlet_levels_json', None), 0)
            fill_row(getattr(unit, 'radiated_levels_json', None), 1)
            fill_row(getattr(unit, 'outlet_levels_json', None), 2)
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
            self.library_updated.emit()
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
            self.library_updated.emit()
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

    def set_preview_selection_mode(self, mode: str) -> None:
        # Update toggle states
        if mode == 'free':
            self.sel_free_btn.setChecked(True)
            self.sel_col_btn.setChecked(False)
            self.sel_row_btn.setChecked(False)
        elif mode == 'column':
            self.sel_free_btn.setChecked(False)
            self.sel_col_btn.setChecked(True)
            self.sel_row_btn.setChecked(False)
        elif mode == 'row':
            self.sel_free_btn.setChecked(False)
            self.sel_col_btn.setChecked(False)
            self.sel_row_btn.setChecked(True)
        try:
            self.preview_viewer.set_selection_mode(mode)
        except Exception:
            pass

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
            def collect_row(row: int) -> dict:
                data = {}
                for c, band in enumerate(self.band_order):
                    item = self.freq_table.item(row, c)
                    if item:
                        val = item.text().strip()
                        if val:
                            data[band] = val
                return data
            inlet_data = collect_row(0)
            radiated_data = collect_row(1)
            outlet_data = collect_row(2)
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
            self.library_updated.emit()
            QMessageBox.information(self, "Saved", "Frequency values saved to database.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes:\n{e}")

    def import_selected_pdf_column(self) -> None:
        # Validate selection and input
        if not hasattr(self, 'preview_viewer') or not getattr(self.preview_viewer, 'pdf_document', None):
            QMessageBox.information(self, "Column Import", "Load a PDF in File Preview first.")
            return
        sel = getattr(self.preview_viewer, 'selection_rect_pdf', None)
        if not sel:
            QMessageBox.information(self, "Column Import", "Drag to select a column region in the PDF preview.")
            return
        label_text = self.column_label_edit.text().strip()
        if not label_text:
            QMessageBox.information(self, "Column Import", "Enter a column label (e.g., 'Inlet 500').")
            return
        try:
            import tempfile, os, sys, json as _json
            import fitz
            # Render just the selected rectangle region to a temp image
            page = self.preview_viewer.pdf_document[self.preview_viewer.current_page]
            x0, y0, x1, y1 = sel
            rect = fitz.Rect(x0, y0, x1, y1)
            zoom = 300.0 / 72.0
            mat = fitz.Matrix(zoom, zoom)
            clip_pix = page.get_pixmap(matrix=mat, clip=rect)
            with tempfile.TemporaryDirectory() as td:
                img_path = os.path.join(td, 'col.png')
                csv_path = os.path.join(td, 'col.csv')
                clip_pix.save(img_path)
                # Run the image table extractor on the cropped column
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'calculations', 'image_table_to_csv.py'))
                cmd = [sys.executable, script_path, '--image', img_path, '--output', csv_path]
                import subprocess
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    raise RuntimeError(res.stderr or 'OCR failed')
                # Read rows and map into a single band column
                import csv
                with open(csv_path, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = [r for r in reader if any(c.strip() for c in r)]
                if not rows:
                    QMessageBox.information(self, 'Column Import', 'No text detected in selection.')
                    return
                # Apply to selected MechanicalUnit if any; else prompt to pick
                current = self.mechanical_list.currentItem()
                if not current:
                    QMessageBox.information(self, 'Column Import', 'Select a Mechanical Unit to apply values to.')
                    return
                unit_id = current.data(Qt.UserRole)
                session = get_session()
                unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == unit_id).first()
                if not unit:
                    session.close(); QMessageBox.information(self, 'Column Import', 'Unit not found.'); return
                # Decide which column to fill based on label
                lt = label_text.lower()
                import re
                band_keys = self.band_order
                # Extract band name if present (63, 125, 250, 500, 1k/1000, 2k/2000, 4k/4000, 8k/8000)
                def norm_band(s):
                    s = s.lower().replace('hz','').strip()
                    if s in {'63','125','250','500'}: return s
                    if s in {'1k','1000'}: return '1000'
                    if s in {'2k','2000'}: return '2000'
                    if s in {'4k','4000'}: return '4000'
                    if s in {'8k','8000'}: return '8000'
                    return None
                # Build map from rows sequentially
                values = {}
                for idx, r in enumerate(rows):
                    # Use first non-empty cell per row as the value
                    val = next((c for c in r if c.strip()), '')
                    if not val:
                        continue
                    # Map rows to bands in order if explicit band not provided
                    if idx < len(band_keys):
                        values[band_keys[idx]] = val
                # Assign to inlet/radiated/outlet based on label
                target = None
                if 'inlet' in lt:
                    target = 'inlet_levels_json'
                elif 'radiated' in lt:
                    target = 'radiated_levels_json'
                elif 'outlet' in lt:
                    target = 'outlet_levels_json'
                if not target:
                    session.close(); QMessageBox.information(self, 'Column Import', 'Label must include Inlet, Radiated, or Outlet.'); return
                setattr(unit, target, _json.dumps(values) if values else None)
                session.commit(); session.close()
                # Refresh display
                self._on_mech_selection_changed()
                QMessageBox.information(self, 'Column Import', f'Applied {len(values)} values to {label_text}.')
        except Exception as e:
            QMessageBox.critical(self, 'Column Import', f'Failed: {e}')

    def import_selected_pdf_row(self) -> None:
        # Require a selected unit
        current = self.mechanical_list.currentItem()
        if not current:
            QMessageBox.information(self, 'Row Import', 'Select a Mechanical Unit in the list first.')
            return
        if not hasattr(self, 'preview_viewer') or not getattr(self.preview_viewer, 'pdf_document', None):
            QMessageBox.information(self, 'Row Import', 'Load a PDF in File Preview, then drag-select a single row region.')
            return
        sel = getattr(self.preview_viewer, 'selection_rect_pdf', None)
        if not sel:
            QMessageBox.information(self, 'Row Import', 'Drag to select a single unit row region in the PDF preview.')
            return
        # Determine target row from label
        label_text = self.column_label_edit.text().strip().lower()
        target = None
        if 'inlet' in label_text:
            target = 'inlet_levels_json'
        elif 'radiated' in label_text:
            target = 'radiated_levels_json'
        elif 'outlet' in label_text:
            target = 'outlet_levels_json'
        if not target:
            QMessageBox.information(self, 'Row Import', 'Enter a label that includes Inlet, Radiated, or Outlet to specify the target row.')
            return
        try:
            import tempfile, os, sys, json as _json, re, csv
            import fitz
            page = self.preview_viewer.pdf_document[self.preview_viewer.current_page]
            x0, y0, x1, y1 = sel
            rect = fitz.Rect(x0, y0, x1, y1)
            zoom = 300.0 / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            with tempfile.TemporaryDirectory() as td:
                img_path = os.path.join(td, 'row.png')
                csv_path = os.path.join(td, 'row.csv')
                pix.save(img_path)
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'calculations', 'image_table_to_csv.py'))
                cmd = [sys.executable, script_path, '--image', img_path, '--output', csv_path]
                import subprocess
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    raise RuntimeError(res.stderr or 'OCR failed')
                tokens = []
                with open(csv_path, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for r in reader:
                        tokens.extend([c.strip() for c in r if c and c.strip()])
                if not tokens:
                    QMessageBox.information(self, 'Row Import', 'No text detected in the selected row.')
                    return
                # Extract numeric tokens only
                nums = [t for t in tokens if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", t)]
                if not nums:
                    QMessageBox.information(self, 'Row Import', 'No numeric values detected in the selection.')
                    return
                # Expect exactly the first 8 bands for a single row
                band_keys = self.band_order
                vals8 = nums[:8]
                if len(vals8) < 1:
                    QMessageBox.information(self, 'Row Import', 'Could not detect the 8 band values in the selection.')
                    return
                values_map = {k: v for k, v in zip(band_keys, vals8)}
                unit_id = current.data(Qt.UserRole)
                session = get_session()
                unit = session.query(MechanicalUnit).filter(MechanicalUnit.id == unit_id).first()
                if not unit:
                    session.close(); QMessageBox.information(self, 'Row Import', 'Selected unit not found.'); return
                setattr(unit, target, _json.dumps(values_map))
                session.commit(); session.close()
                self._on_mech_selection_changed()
                QMessageBox.information(self, 'Row Import', f'Imported {len(values_map)} band values into the {target.replace("_levels_json"," ")} row.')
        except Exception as e:
            QMessageBox.critical(self, 'Row Import', f'Failed: {e}')

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
            self.library_updated.emit()

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
            self.library_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete entry:\n{e}")


    def manual_add_component(self) -> None:
        dlg = ManualMechanicalUnitAddDialog(self, project_id=self.project_id)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_lists()
            self.library_updated.emit()
    
    # Acoustic Materials Management Methods
    def refresh_acoustic_materials(self) -> None:
        """Refresh the acoustic materials list with optional project filtering"""
        if not hasattr(self, 'acoustic_materials_list'):
            return
        
        try:
            session = get_session()
            
            # Base query
            query = session.query(AcousticMaterial)
            
            # Apply project filter if enabled
            if self.show_only_project_materials and self.project_id:
                # Get materials used in this project's spaces (check both systems)
                from models.space import Space, SpaceSurfaceMaterial
                from data.materials import STANDARD_MATERIALS
                
                project_space_ids = [s.id for s in session.query(Space).filter(Space.project_id == self.project_id).all()]
                
                if project_space_ids:
                    material_ids_set = set()
                    
                    # Check NEW RT60 system: RoomSurfaceInstance with material_id FK
                    room_surface_material_ids = session.query(RoomSurfaceInstance.material_id).filter(
                        RoomSurfaceInstance.space_id.in_(project_space_ids),
                        RoomSurfaceInstance.material_id.isnot(None)
                    ).distinct().all()
                    material_ids_set.update([mid[0] for mid in room_surface_material_ids])
                    
                    # Check LEGACY system: SpaceSurfaceMaterial with material_key strings
                    space_material_keys = session.query(SpaceSurfaceMaterial.material_key).filter(
                        SpaceSurfaceMaterial.space_id.in_(project_space_ids)
                    ).distinct().all()
                    
                    # Match material keys to AcousticMaterial names
                    for (mat_key,) in space_material_keys:
                        # Get material name from STANDARD_MATERIALS
                        if mat_key in STANDARD_MATERIALS:
                            mat_name = STANDARD_MATERIALS[mat_key].get('name', mat_key)
                        else:
                            # Material key might BE the name already
                            mat_name = mat_key
                        
                        # Find matching AcousticMaterial by name (case-insensitive partial match)
                        matching_materials = session.query(AcousticMaterial).filter(
                            AcousticMaterial.name.ilike(f'%{mat_name}%')
                        ).all()
                        material_ids_set.update([m.id for m in matching_materials])
                    
                    if material_ids_set:
                        query = query.filter(AcousticMaterial.id.in_(material_ids_set))
                    else:
                        # No materials in project yet
                        query = query.filter(AcousticMaterial.id == -1)  # Return empty
            
            materials = query.order_by(AcousticMaterial.name).all()
            
            self.acoustic_materials_list.clear()
            
            for mat in materials:
                nrc_text = f"{mat.nrc:.2f}" if mat.nrc is not None else "—"
                text = f"{mat.name} - NRC: {nrc_text}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, mat.id)
                
                # Build tooltip
                tooltip_parts = [f"Name: {mat.name}"]
                if mat.category:
                    tooltip_parts.append(f"Category: {mat.category.name}")
                if mat.manufacturer:
                    tooltip_parts.append(f"Manufacturer: {mat.manufacturer}")
                if mat.mounting_type:
                    tooltip_parts.append(f"Mounting: {mat.mounting_type}")
                if mat.thickness:
                    tooltip_parts.append(f"Thickness: {mat.thickness}")
                item.setToolTip("\n".join(tooltip_parts))
                
                self.acoustic_materials_list.addItem(item)
            
            if self.acoustic_materials_list.count() == 0:
                placeholder = QListWidgetItem(
                    "No materials found. Click 'Manual Treatment Add' to create one." if not self.show_only_project_materials
                    else "No materials used in this project yet."
                )
                placeholder.setFlags(Qt.ItemIsEnabled)
                placeholder.setForeground(QColor(120, 120, 120))
                self.acoustic_materials_list.addItem(placeholder)
            
            session.close()
            
            # Clear selection and preview
            self._clear_acoustic_material_preview()
            
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load acoustic materials:\n{e}")
    
    def _clear_acoustic_material_preview(self) -> None:
        """Clear the absorption table"""
        if hasattr(self, 'acoustic_absorption_table') and self.acoustic_absorption_table is not None:
            for c in range(self.acoustic_absorption_table.columnCount()):
                item = self.acoustic_absorption_table.item(0, c)
                if item:
                    item.setText("")
        self.acoustic_material_dirty = False
        if hasattr(self, 'save_material_btn'):
            self.save_material_btn.setEnabled(False)
    
    def _on_acoustic_material_selected(self) -> None:
        """Handle acoustic material selection change"""
        current = self.acoustic_materials_list.currentItem()
        if not current or current.data(Qt.UserRole) is None:
            self._clear_acoustic_material_preview()
            return
        
        material_id = current.data(Qt.UserRole)
        
        try:
            session = get_session()
            material = session.query(AcousticMaterial).filter(AcousticMaterial.id == material_id).first()
            session.close()
            
            if not material:
                self._clear_acoustic_material_preview()
                return
            
            # Disconnect signal temporarily to avoid triggering dirty state
            try:
                self.acoustic_absorption_table.cellChanged.disconnect()
            except Exception:
                pass
            
            # Fill absorption coefficients
            coefficients = [
                material.absorption_125,
                material.absorption_250,
                material.absorption_500,
                material.absorption_1000,
                material.absorption_2000,
                material.absorption_4000
            ]
            
            for c, coeff in enumerate(coefficients):
                val_text = f"{coeff:.2f}" if coeff is not None else ""
                self.acoustic_absorption_table.item(0, c).setText(val_text)
            
            # Fill NRC (last column)
            nrc_text = f"{material.nrc:.2f}" if material.nrc is not None else ""
            self.acoustic_absorption_table.item(0, 6).setText(nrc_text)
            
            # Reconnect signal
            self.acoustic_absorption_table.cellChanged.connect(self._on_acoustic_material_cell_changed)
            
            # Reset dirty state
            self.acoustic_material_dirty = False
            if hasattr(self, 'save_material_btn'):
                self.save_material_btn.setEnabled(False)
                
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load material:\n{e}")
            self._clear_acoustic_material_preview()
    
    def _toggle_acoustic_material_buttons(self) -> None:
        """Enable/disable edit and delete buttons based on selection"""
        has_sel = self.acoustic_materials_list.currentItem() is not None
        valid_sel = has_sel and self.acoustic_materials_list.currentItem().data(Qt.UserRole) is not None
        if hasattr(self, 'edit_material_btn'):
            self.edit_material_btn.setEnabled(valid_sel)
        if hasattr(self, 'delete_material_btn'):
            self.delete_material_btn.setEnabled(valid_sel)
    
    def _on_acoustic_material_filter_changed(self, _state: int) -> None:
        """Handle filter checkbox state change"""
        self.show_only_project_materials = self.materials_filter_checkbox.isChecked()
        self.refresh_acoustic_materials()
    
    def _on_acoustic_material_cell_changed(self, row: int, col: int) -> None:
        """Mark table dirty when user edits absorption coefficients"""
        if col < 6:  # Only for editable columns (not NRC)
            self.acoustic_material_dirty = True
            if hasattr(self, 'save_material_btn'):
                self.save_material_btn.setEnabled(True)
            
            # Auto-calculate NRC from 250, 500, 1000, 2000 Hz (indices 1,2,3,4)
            try:
                coeffs = []
                for idx in [1, 2, 3, 4]:  # 250, 500, 1000, 2000
                    text = self.acoustic_absorption_table.item(0, idx).text().strip()
                    if text:
                        coeffs.append(float(text))
                
                if len(coeffs) == 4:
                    nrc = sum(coeffs) / 4.0
                    # Update NRC cell without triggering cellChanged
                    try:
                        self.acoustic_absorption_table.cellChanged.disconnect()
                    except Exception:
                        pass
                    self.acoustic_absorption_table.item(0, 6).setText(f"{nrc:.2f}")
                    self.acoustic_absorption_table.cellChanged.connect(self._on_acoustic_material_cell_changed)
            except Exception:
                pass
    
    def save_acoustic_material_changes(self) -> None:
        """Save direct table edits to database"""
        if not self.acoustic_material_dirty:
            return
        
        current = self.acoustic_materials_list.currentItem()
        if not current or current.data(Qt.UserRole) is None:
            QMessageBox.information(self, "Save", "Select an acoustic material first.")
            return
        
        material_id = current.data(Qt.UserRole)
        
        try:
            session = get_session()
            material = session.query(AcousticMaterial).filter(AcousticMaterial.id == material_id).first()
            
            if not material:
                session.close()
                QMessageBox.warning(self, "Save", "Selected material not found in database.")
                return
            
            # Read values from table
            def as_float(txt: str):
                try:
                    return float(txt.strip())
                except Exception:
                    return None
            
            material.absorption_125 = as_float(self.acoustic_absorption_table.item(0, 0).text())
            material.absorption_250 = as_float(self.acoustic_absorption_table.item(0, 1).text())
            material.absorption_500 = as_float(self.acoustic_absorption_table.item(0, 2).text())
            material.absorption_1000 = as_float(self.acoustic_absorption_table.item(0, 3).text())
            material.absorption_2000 = as_float(self.acoustic_absorption_table.item(0, 4).text())
            material.absorption_4000 = as_float(self.acoustic_absorption_table.item(0, 5).text())
            
            # Recalculate NRC
            material.calculate_nrc()
            
            session.commit()
            session.close()
            
            self.acoustic_material_dirty = False
            self.save_material_btn.setEnabled(False)
            self.library_updated.emit()
            
            # Refresh list to show updated NRC
            self.refresh_acoustic_materials()
            
            QMessageBox.information(self, "Saved", "Absorption coefficients saved to database.")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes:\n{e}")
    
    def manual_add_acoustic_material(self) -> None:
        """Open dialog to manually add a new acoustic material"""
        dlg = ManualAcousticMaterialAddDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_acoustic_materials()
            self.library_updated.emit()
    
    def edit_selected_acoustic_material(self) -> None:
        """Edit the selected acoustic material"""
        current = self.acoustic_materials_list.currentItem()
        if not current or current.data(Qt.UserRole) is None:
            return
        
        material_id = current.data(Qt.UserRole)
        
        try:
            session = get_session()
            material = session.query(AcousticMaterial).filter(AcousticMaterial.id == material_id).first()
            session.close()
            
            if not material:
                return
            
            dlg = AcousticMaterialEditDialog(self, material)
            if dlg.exec() == QDialog.Accepted:
                self.refresh_acoustic_materials()
                self.library_updated.emit()
                
        except Exception as e:
            QMessageBox.critical(self, "Edit Error", f"Failed to open edit dialog:\n{e}")
    
    def delete_selected_acoustic_material(self) -> None:
        """Delete the selected acoustic material"""
        current = self.acoustic_materials_list.currentItem()
        if not current or current.data(Qt.UserRole) is None:
            return
        
        material_id = current.data(Qt.UserRole)
        
        try:
            session = get_session()
            material = session.query(AcousticMaterial).filter(AcousticMaterial.id == material_id).first()
            
            if not material:
                session.close()
                QMessageBox.warning(self, "Delete", "Selected material not found.")
                return
            
            # Check if material is used in any project
            usage_count = session.query(RoomSurfaceInstance).filter(
                RoomSurfaceInstance.material_id == material_id
            ).count()
            
            warning_msg = f"Delete acoustic material '{material.name}'?"
            if usage_count > 0:
                warning_msg += f"\n\nWarning: This material is currently used in {usage_count} surface instance(s)."
            
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                warning_msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                session.close()
                return
            
            # Delete the material
            session.delete(material)
            session.commit()
            session.close()
            
            self.refresh_acoustic_materials()
            self.library_updated.emit()
            QMessageBox.information(self, "Deleted", "Acoustic material deleted.")
            
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete material:\n{e}")
    
    # Material Schedule Management Methods
    def refresh_material_schedules(self) -> None:
        """Refresh the material schedules list"""
        if not hasattr(self, 'material_schedules_list'):
            return
        
        try:
            from models import MaterialSchedule
            from models.drawing_sets import DrawingSet
            
            session = get_session()
            
            # Load all drawing sets with their material schedules
            drawing_sets = (
                session.query(DrawingSet)
                .filter(DrawingSet.project_id == self.project_id)
                .order_by(DrawingSet.created_date)
                .all()
            )
            
            self.material_schedules_list.clear()
            
            phase_icons = {'DD': '🟦', 'SD': '🟨', 'CD': '🟥', 'Final': '🟩', 'Legacy': '⚫'}
            
            for ds in drawing_sets:
                # Get schedules for this drawing set
                schedules = (
                    session.query(MaterialSchedule)
                    .filter(MaterialSchedule.drawing_set_id == ds.id)
                    .order_by(MaterialSchedule.name)
                    .all()
                )
                
                if schedules:
                    # Add drawing set header
                    icon = phase_icons.get(ds.phase_type, '⚪')
                    header_text = f"═══ {icon} {ds.name} ({ds.phase_type}) ═══"
                    header_item = QListWidgetItem(header_text)
                    header_item.setFlags(Qt.ItemIsEnabled)  # Not selectable
                    header_item.setForeground(QColor(180, 180, 180))
                    self.material_schedules_list.addItem(header_item)
                    
                    # Add schedules
                    for ms in schedules:
                        schedule_text = f"  📄 {ms.name} ({ms.schedule_type})"
                        item = QListWidgetItem(schedule_text)
                        item.setData(Qt.UserRole, ms.id)
                        self.material_schedules_list.addItem(item)
            
            if self.material_schedules_list.count() == 0:
                placeholder = QListWidgetItem("No material schedules. Click 'Add Schedule' to create one.")
                placeholder.setFlags(Qt.ItemIsEnabled)
                placeholder.setForeground(QColor(120, 120, 120))
                self.material_schedules_list.addItem(placeholder)
            
            session.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load material schedules:\n{e}")
    
    def on_material_schedule_selected(self) -> None:
        """Handle material schedule selection change"""
        if not hasattr(self, 'material_schedules_list'):
            return
        
        current = self.material_schedules_list.currentItem()
        
        # Enable/disable buttons based on selection
        has_selection = current is not None and current.data(Qt.UserRole) is not None
        if hasattr(self, 'edit_material_schedule_btn'):
            self.edit_material_schedule_btn.setEnabled(has_selection)
        if hasattr(self, 'delete_material_schedule_btn'):
            self.delete_material_schedule_btn.setEnabled(has_selection)
        
        if not has_selection:
            return
        
        schedule_id = current.data(Qt.UserRole)
        
        try:
            from models import MaterialSchedule
            
            session = get_session()
            schedule = session.query(MaterialSchedule).filter(
                MaterialSchedule.id == schedule_id
            ).first()
            session.close()
            
            if not schedule:
                return
            
            # Load PDF in viewer
            file_path = schedule.get_display_path()
            if file_path and hasattr(self, 'material_schedule_viewer'):
                import os
                if os.path.exists(file_path):
                    self.material_schedule_viewer.load_pdf(file_path)
                else:
                    QMessageBox.warning(self, "File Not Found", 
                                      f"PDF file not found:\n{file_path}")
        
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load schedule:\n{e}")
    
    def add_material_schedule(self) -> None:
        """Open dialog to add a new material schedule"""
        try:
            from ui.dialogs.material_schedule_dialog import MaterialScheduleDialog
            from models import Project
            
            # Get project location
            session = get_session()
            project = session.query(Project).filter(Project.id == self.project_id).first()
            session.close()
            
            if not project:
                QMessageBox.warning(self, "Add Schedule", "Project not found.")
                return
            
            dialog = MaterialScheduleDialog(
                self, 
                project_id=self.project_id,
                project_location=project.location
            )
            
            if dialog.exec() == QDialog.Accepted:
                self.refresh_material_schedules()
        
        except Exception as e:
            QMessageBox.critical(self, "Add Schedule", f"Failed to add material schedule:\n{e}")
    
    def edit_material_schedule(self) -> None:
        """Edit the selected material schedule"""
        if not hasattr(self, 'material_schedules_list'):
            return
        
        current = self.material_schedules_list.currentItem()
        if not current or current.data(Qt.UserRole) is None:
            QMessageBox.information(self, "Edit Schedule", "Select a material schedule to edit.")
            return
        
        schedule_id = current.data(Qt.UserRole)
        
        try:
            from ui.dialogs.material_schedule_dialog import MaterialScheduleDialog
            from models import MaterialSchedule, Project
            
            session = get_session()
            schedule = session.query(MaterialSchedule).filter(
                MaterialSchedule.id == schedule_id
            ).first()
            project = session.query(Project).filter(Project.id == self.project_id).first()
            session.close()
            
            if not schedule:
                QMessageBox.warning(self, "Edit Schedule", "Selected schedule not found.")
                return
            
            dialog = MaterialScheduleDialog(
                self,
                project_id=self.project_id,
                project_location=project.location if project else None,
                material_schedule=schedule
            )
            
            if dialog.exec() == QDialog.Accepted:
                self.refresh_material_schedules()
        
        except Exception as e:
            QMessageBox.critical(self, "Edit Schedule", f"Failed to edit material schedule:\n{e}")
    
    def delete_material_schedule(self) -> None:
        """Delete the selected material schedule"""
        if not hasattr(self, 'material_schedules_list'):
            return
        
        current = self.material_schedules_list.currentItem()
        if not current or current.data(Qt.UserRole) is None:
            QMessageBox.information(self, "Delete Schedule", "Select a material schedule to delete.")
            return
        
        schedule_id = current.data(Qt.UserRole)
        
        try:
            from models import MaterialSchedule
            
            session = get_session()
            schedule = session.query(MaterialSchedule).filter(
                MaterialSchedule.id == schedule_id
            ).first()
            
            if not schedule:
                session.close()
                QMessageBox.warning(self, "Delete Schedule", "Selected schedule not found.")
                return
            
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Delete material schedule '{schedule.name}'?\n\n"
                "Note: The PDF file itself will not be deleted from disk.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                session.close()
                return
            
            # Delete the schedule record (files remain on disk)
            session.delete(schedule)
            session.commit()
            session.close()
            
            self.refresh_material_schedules()
            QMessageBox.information(self, "Deleted", "Material schedule deleted.")
        
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete schedule:\n{e}")
    
    def load_material_schedule_pdf(self) -> None:
        """Load a PDF directly into the material schedule viewer"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF to Preview",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path and hasattr(self, 'material_schedule_viewer'):
            try:
                self.material_schedule_viewer.load_pdf(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Preview Error", f"Failed to load PDF:\n{e}")
    
    def compare_material_schedules(self) -> None:
        """Open the material schedule comparison dialog"""
        try:
            from ui.dialogs.material_schedule_comparison_dialog import MaterialScheduleComparisonDialog
            
            dialog = MaterialScheduleComparisonDialog(self, project_id=self.project_id)
            dialog.exec()
        
        except Exception as e:
            QMessageBox.critical(self, "Comparison Error", 
                               f"Failed to open comparison dialog:\n{e}")
    
    def open_materials_database_setup(self) -> None:
        """Open the Materials Database Setup dialog"""
        try:
            from ui.dialogs.materials_database_setup_dialog import MaterialsDatabaseSetupDialog
            
            dialog = MaterialsDatabaseSetupDialog(self)
            dialog.exec()
            # Refresh materials list after dialog closes in case user made changes
            self.refresh_acoustic_materials()
        
        except Exception as e:
            QMessageBox.critical(self, "Database Setup Error", 
                               f"Failed to open database setup dialog:\n{e}")


class MechanicalUnitEditDialog(QDialog):
    """Simple editor for MechanicalUnit properties, including extras JSON."""

    def __init__(self, parent: Optional[QWidget], unit: MechanicalUnit):
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
        self.cfm_spin.setToolTip("Design supply CFM - used for HVAC component calculations")
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
            
            # Validate and set CFM
            cfm_value = self.cfm_spin.value() if self.cfm_spin.value() > 0 else None
            if cfm_value and not is_valid_cfm_value(cfm_value):
                QMessageBox.warning(self, "CFM Validation", f"CFM value {cfm_value:.0f} is outside typical range.")
            db_unit.airflow_cfm = cfm_value
            
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


class SilencerEditDialog(QDialog):
    def __init__(self, parent=None, silencer: Optional[SilencerProduct] = None):
        super().__init__(parent)
        self.silencer = silencer
        self.setWindowTitle("Edit Silencer" if silencer else "Add Silencer")
        self.resize(500, 450)
        self.setModal(True)
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.mfr_edit = QLineEdit(silencer.manufacturer if silencer else "")
        self.model_edit = QLineEdit(silencer.model_number if silencer else "")
        self.type_edit = QLineEdit(silencer.silencer_type if silencer else "")
        form.addRow("Manufacturer:", self.mfr_edit)
        form.addRow("Model:", self.model_edit)
        form.addRow("Type:", self.type_edit)
        v.addLayout(form)
        btns = QHBoxLayout()
        cancel = QPushButton("Cancel"); save = QPushButton("Save")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        btns.addStretch(); btns.addWidget(cancel); btns.addWidget(save)
        v.addLayout(btns)

    def _save(self):
        try:
            session = get_session()
            if self.silencer:
                s = session.query(SilencerProduct).filter(SilencerProduct.id == self.silencer.id).first()
                if not s:
                    session.close(); QMessageBox.warning(self, "Silencer", "Not found"); return
                s.manufacturer = self.mfr_edit.text().strip()
                s.model_number = self.model_edit.text().strip()
                s.silencer_type = self.type_edit.text().strip()
            else:
                s = SilencerProduct(
                    manufacturer=self.mfr_edit.text().strip(),
                    model_number=self.model_edit.text().strip(),
                    silencer_type=self.type_edit.text().strip() or 'dissipative',
                )
                session.add(s)
            session.commit(); session.close()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save silencer: {e}")

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
                def pick_val(i: Optional[int]) -> str:
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



class ManualMechanicalUnitAddDialog(QDialog):
    """Dialog to manually add a MechanicalUnit with octave-band data."""

    def __init__(self, parent: Optional[QWidget], project_id: Optional[int]):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("Manual Component Add")
        self.resize(640, 520)
        self.setModal(True)

        self.band_order = ["63", "125", "250", "500", "1000", "2000", "4000", "8000"]

        v = QVBoxLayout(self)
        form = QFormLayout()

        # Type (editable combo) and Name
        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems(["AHU", "RTU", "RF", "EF", "VAV", "DOAS", "FCU", "TF"])
        self.type_combo.setCurrentText("AHU")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., 1-1 or AHU-1")

        # CFM input
        self.cfm_spin = QDoubleSpinBox()
        self.cfm_spin.setRange(10, 100000)
        self.cfm_spin.setDecimals(0)
        self.cfm_spin.setSuffix(" CFM")
        self.cfm_spin.setValue(1000)  # Default value

        # Entry type (sound power/pressure)
        self.entry_type_combo = QComboBox()
        self.entry_type_combo.addItem("Sound Power (Lw)", userData="sound_power")
        self.entry_type_combo.addItem("Sound Pressure (Lp)", userData="sound_pressure")

        form.addRow("Type:", self.type_combo)
        form.addRow("Name:", self.name_edit)
        form.addRow("Airflow (CFM):", self.cfm_spin)
        form.addRow("Entry Type:", self.entry_type_combo)
        v.addLayout(form)

        # Band editors
        def build_band_group(title: str):
            grp = QGroupBox(title)
            grid = QGridLayout()
            # headers
            for c, b in enumerate(self.band_order):
                grid.addWidget(QLabel(b), 0, c + 1)
            grid.addWidget(QLabel("Band (Hz)"), 0, 0)
            # inputs in one row
            edits = []
            grid.addWidget(QLabel("dB"), 1, 0)
            for c in range(len(self.band_order)):
                e = QLineEdit()
                e.setMaximumWidth(70)
                edits.append(e)
                grid.addWidget(e, 1, c + 1)
            grp.setLayout(grid)
            return grp, edits

        self.inlet_group, self.inlet_edits = build_band_group("Inlet Levels")
        self.radiated_group, self.radiated_edits = build_band_group("Radiated Levels")
        self.outlet_group, self.outlet_edits = build_band_group("Outlet Levels")

        v.addWidget(self.inlet_group)
        v.addWidget(self.radiated_group)
        v.addWidget(self.outlet_group)

        # Buttons
        btns = QHBoxLayout()
        cancel = QPushButton("Cancel")
        save = QPushButton("Save")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        btns.addStretch(); btns.addWidget(cancel); btns.addWidget(save)
        v.addLayout(btns)

    def _collect_band_values(self, edits: list[QLineEdit]) -> dict[str, float]:
        values: dict[str, float] = {}
        for b, e in zip(self.band_order, edits):
            txt = e.text().strip()
            if not txt:
                continue
            try:
                values[b] = float(txt)
            except Exception:
                continue
        return values

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        unit_type = self.type_combo.currentText().strip() or None
        if not name:
            QMessageBox.information(self, "Manual Add", "Enter a component name.")
            return
        try:
            session = get_session()
            unit = MechanicalUnit(project_id=self.project_id, name=name, unit_type=unit_type)
            
            # Set CFM
            cfm_value = self.cfm_spin.value()
            if cfm_value and not is_valid_cfm_value(cfm_value, unit_type):
                QMessageBox.warning(self, "CFM Validation", f"CFM value {cfm_value:.0f} may be unusual for {unit_type or 'this component type'}.")
            unit.airflow_cfm = cfm_value
            
            inlet = self._collect_band_values(self.inlet_edits)
            radiated = self._collect_band_values(self.radiated_edits)
            outlet = self._collect_band_values(self.outlet_edits)
            import json as _json
            unit.inlet_levels_json = _json.dumps(inlet) if inlet else None
            unit.radiated_levels_json = _json.dumps(radiated) if radiated else None
            unit.outlet_levels_json = _json.dumps(outlet) if outlet else None
            etype = self.entry_type_combo.currentData() or "sound_power"
            unit.extra_json = _json.dumps({"entry_type": etype, "manual": True})
            session.add(unit)
            session.commit()
            session.close()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save component:\n{e}")


class ManualAcousticMaterialAddDialog(QDialog):
    """Dialog to manually add an acoustic material with absorption coefficients"""
    
    def __init__(self, parent: Optional[QWidget]):
        super().__init__(parent)
        self.setWindowTitle("Manual Treatment Add")
        self.resize(600, 650)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Basic information form
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Acoustic Ceiling Tile")
        form.addRow("Name*:", self.name_edit)
        
        # Category dropdown
        self.category_combo = QComboBox()
        self.category_combo.addItem("(No Category)", None)
        try:
            session = get_session()
            categories = session.query(SurfaceCategory).order_by(SurfaceCategory.name).all()
            for cat in categories:
                self.category_combo.addItem(cat.name, cat.id)
            session.close()
        except Exception:
            pass
        form.addRow("Category:", self.category_combo)
        
        self.manufacturer_edit = QLineEdit()
        form.addRow("Manufacturer:", self.manufacturer_edit)
        
        self.product_code_edit = QLineEdit()
        form.addRow("Product Code:", self.product_code_edit)
        
        self.mounting_combo = QComboBox()
        self.mounting_combo.addItems(["", "direct", "suspended", "spaced"])
        form.addRow("Mounting Type:", self.mounting_combo)
        
        self.thickness_edit = QLineEdit()
        self.thickness_edit.setPlaceholderText("e.g., 1 inch, 25mm")
        form.addRow("Thickness:", self.thickness_edit)
        
        layout.addLayout(form)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        layout.addWidget(self.description_edit)
        
        # Absorption coefficients
        coeff_group = QGroupBox("Absorption Coefficients (0.00 - 1.00)")
        coeff_layout = QGridLayout()
        
        self.band_labels = ["125 Hz", "250 Hz", "500 Hz", "1000 Hz", "2000 Hz", "4000 Hz"]
        self.coeff_spinboxes = []
        
        for i, label in enumerate(self.band_labels):
            coeff_layout.addWidget(QLabel(label), i, 0)
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 1.0)
            spinbox.setDecimals(2)
            spinbox.setSingleStep(0.01)
            spinbox.setValue(0.0)
            spinbox.valueChanged.connect(self._update_nrc)
            self.coeff_spinboxes.append(spinbox)
            coeff_layout.addWidget(spinbox, i, 1)
        
        coeff_group.setLayout(coeff_layout)
        layout.addWidget(coeff_group)
        
        # NRC display
        nrc_layout = QHBoxLayout()
        nrc_layout.addWidget(QLabel("Calculated NRC:"))
        self.nrc_display = QLineEdit()
        self.nrc_display.setReadOnly(True)
        self.nrc_display.setText("0.00")
        self.nrc_display.setMaximumWidth(100)
        nrc_layout.addWidget(self.nrc_display)
        nrc_layout.addStretch()
        layout.addLayout(nrc_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
    
    def _update_nrc(self):
        """Auto-calculate NRC from 250, 500, 1000, 2000 Hz"""
        try:
            # Indices 1, 2, 3, 4 correspond to 250, 500, 1000, 2000 Hz
            nrc_bands = [self.coeff_spinboxes[i].value() for i in [1, 2, 3, 4]]
            nrc = sum(nrc_bands) / 4.0
            self.nrc_display.setText(f"{nrc:.2f}")
        except Exception:
            self.nrc_display.setText("0.00")
    
    def _save(self):
        """Validate and save the new material"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.information(self, "Manual Treatment Add", "Please enter a material name.")
            return
        
        # Check if at least one coefficient is > 0
        coeffs = [sb.value() for sb in self.coeff_spinboxes]
        if all(c == 0.0 for c in coeffs):
            QMessageBox.information(self, "Manual Treatment Add", 
                                  "Please enter at least one absorption coefficient greater than 0.")
            return
        
        try:
            session = get_session()
            
            material = AcousticMaterial(
                name=name,
                category_id=self.category_combo.currentData(),
                manufacturer=self.manufacturer_edit.text().strip() or None,
                product_code=self.product_code_edit.text().strip() or None,
                mounting_type=self.mounting_combo.currentText().strip() or None,
                thickness=self.thickness_edit.text().strip() or None,
                description=self.description_edit.toPlainText().strip() or None,
                absorption_125=coeffs[0],
                absorption_250=coeffs[1],
                absorption_500=coeffs[2],
                absorption_1000=coeffs[3],
                absorption_2000=coeffs[4],
                absorption_4000=coeffs[5]
            )
            
            # Calculate NRC
            material.calculate_nrc()
            
            session.add(material)
            session.commit()
            session.close()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save acoustic material:\n{e}")


class AcousticMaterialEditDialog(QDialog):
    """Dialog to edit an existing acoustic material"""
    
    def __init__(self, parent: Optional[QWidget], material: AcousticMaterial):
        super().__init__(parent)
        self.material = material
        self.setWindowTitle(f"Edit Acoustic Material: {material.name}")
        self.resize(600, 650)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Basic information form
        form = QFormLayout()
        
        self.name_edit = QLineEdit(material.name or "")
        form.addRow("Name*:", self.name_edit)
        
        # Category dropdown
        self.category_combo = QComboBox()
        self.category_combo.addItem("(No Category)", None)
        try:
            session = get_session()
            categories = session.query(SurfaceCategory).order_by(SurfaceCategory.name).all()
            for cat in categories:
                self.category_combo.addItem(cat.name, cat.id)
                if material.category_id == cat.id:
                    self.category_combo.setCurrentIndex(self.category_combo.count() - 1)
            session.close()
        except Exception:
            pass
        form.addRow("Category:", self.category_combo)
        
        self.manufacturer_edit = QLineEdit(material.manufacturer or "")
        form.addRow("Manufacturer:", self.manufacturer_edit)
        
        self.product_code_edit = QLineEdit(material.product_code or "")
        form.addRow("Product Code:", self.product_code_edit)
        
        self.mounting_combo = QComboBox()
        self.mounting_combo.addItems(["", "direct", "suspended", "spaced"])
        if material.mounting_type:
            idx = self.mounting_combo.findText(material.mounting_type)
            if idx >= 0:
                self.mounting_combo.setCurrentIndex(idx)
        form.addRow("Mounting Type:", self.mounting_combo)
        
        self.thickness_edit = QLineEdit(material.thickness or "")
        form.addRow("Thickness:", self.thickness_edit)
        
        layout.addLayout(form)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlainText(material.description or "")
        layout.addWidget(self.description_edit)
        
        # Absorption coefficients
        coeff_group = QGroupBox("Absorption Coefficients (0.00 - 1.00)")
        coeff_layout = QGridLayout()
        
        self.band_labels = ["125 Hz", "250 Hz", "500 Hz", "1000 Hz", "2000 Hz", "4000 Hz"]
        self.coeff_spinboxes = []
        coefficients = [
            material.absorption_125 or 0.0,
            material.absorption_250 or 0.0,
            material.absorption_500 or 0.0,
            material.absorption_1000 or 0.0,
            material.absorption_2000 or 0.0,
            material.absorption_4000 or 0.0
        ]
        
        for i, (label, value) in enumerate(zip(self.band_labels, coefficients)):
            coeff_layout.addWidget(QLabel(label), i, 0)
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 1.0)
            spinbox.setDecimals(2)
            spinbox.setSingleStep(0.01)
            spinbox.setValue(value)
            spinbox.valueChanged.connect(self._update_nrc)
            self.coeff_spinboxes.append(spinbox)
            coeff_layout.addWidget(spinbox, i, 1)
        
        coeff_group.setLayout(coeff_layout)
        layout.addWidget(coeff_group)
        
        # NRC display
        nrc_layout = QHBoxLayout()
        nrc_layout.addWidget(QLabel("Calculated NRC:"))
        self.nrc_display = QLineEdit()
        self.nrc_display.setReadOnly(True)
        self.nrc_display.setText(f"{material.nrc:.2f}" if material.nrc is not None else "0.00")
        self.nrc_display.setMaximumWidth(100)
        nrc_layout.addWidget(self.nrc_display)
        nrc_layout.addStretch()
        layout.addLayout(nrc_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
    
    def _update_nrc(self):
        """Auto-calculate NRC from 250, 500, 1000, 2000 Hz"""
        try:
            # Indices 1, 2, 3, 4 correspond to 250, 500, 1000, 2000 Hz
            nrc_bands = [self.coeff_spinboxes[i].value() for i in [1, 2, 3, 4]]
            nrc = sum(nrc_bands) / 4.0
            self.nrc_display.setText(f"{nrc:.2f}")
        except Exception:
            self.nrc_display.setText("0.00")
    
    def _save(self):
        """Validate and save changes to the material"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.information(self, "Edit Material", "Please enter a material name.")
            return
        
        # Check if at least one coefficient is > 0
        coeffs = [sb.value() for sb in self.coeff_spinboxes]
        if all(c == 0.0 for c in coeffs):
            QMessageBox.information(self, "Edit Material", 
                                  "Please enter at least one absorption coefficient greater than 0.")
            return
        
        try:
            session = get_session()
            db_material = session.query(AcousticMaterial).filter(
                AcousticMaterial.id == self.material.id
            ).first()
            
            if not db_material:
                session.close()
                QMessageBox.critical(self, "Edit Error", "Material not found in database.")
                return
            
            # Update fields
            db_material.name = name
            db_material.category_id = self.category_combo.currentData()
            db_material.manufacturer = self.manufacturer_edit.text().strip() or None
            db_material.product_code = self.product_code_edit.text().strip() or None
            db_material.mounting_type = self.mounting_combo.currentText().strip() or None
            db_material.thickness = self.thickness_edit.text().strip() or None
            db_material.description = self.description_edit.toPlainText().strip() or None
            db_material.absorption_125 = coeffs[0]
            db_material.absorption_250 = coeffs[1]
            db_material.absorption_500 = coeffs[2]
            db_material.absorption_1000 = coeffs[3]
            db_material.absorption_2000 = coeffs[4]
            db_material.absorption_4000 = coeffs[5]
            
            # Recalculate NRC
            db_material.calculate_nrc()
            
            session.commit()
            session.close()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes:\n{e}")
