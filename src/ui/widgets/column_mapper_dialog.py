"""
Column Mapper Dialog
-------------------
Interactive dialog for mapping table columns to mechanical unit fields.
"""

from __future__ import annotations

from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QFormLayout,
    QScrollArea, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal


class ColumnMapperDialog(QDialog):
    """
    Dialog for mapping table columns to mechanical unit fields
    """
    
    mapping_confirmed = Signal(dict)  # Emits mapping dictionary
    
    def __init__(self, headers: List[str], sample_data: List[List[str]], parent=None):
        super().__init__(parent)
        self.headers = headers
        self.sample_data = sample_data
        self.setWindowTitle("Column Mapping Configuration")
        self.setModal(True)
        self.resize(800, 600)
        
        # Frequency bands
        self.frequency_bands = ["63", "125", "250", "500", "1000", "2000", "4000", "8000"]
        
        # Mapping storage
        self.name_combo: Optional[QComboBox] = None
        self.type_combo: Optional[QComboBox] = None
        self.inlet_combos: List[QComboBox] = []
        self.radiated_combos: List[QComboBox] = []
        self.outlet_combos: List[QComboBox] = []
        
        self._build_ui()
        self._suggest_mapping()
    
    def _build_ui(self):
        """Build the dialog UI"""
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Map table columns to mechanical unit fields. "
            "Auto-detected mappings are pre-filled, but you can adjust them manually."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Sample data preview
        sample_group = QGroupBox("Sample Data (First 3 Rows)")
        sample_layout = QVBoxLayout()
        sample_text = self._format_sample_data()
        sample_label = QLabel(sample_text)
        sample_label.setStyleSheet("font-family: monospace; background: #f5f5f5; padding: 10px;")
        sample_label.setWordWrap(True)
        sample_layout.addWidget(sample_label)
        sample_group.setLayout(sample_layout)
        layout.addWidget(sample_group)
        
        # Scrollable mapping area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Basic fields
        basic_group = QGroupBox("Basic Fields")
        basic_form = QFormLayout()
        
        self.name_combo = self._create_column_combo()
        basic_form.addRow("Unit Name:", self.name_combo)
        
        self.type_combo = self._create_column_combo()
        basic_form.addRow("Unit Type:", self.type_combo)
        
        basic_group.setLayout(basic_form)
        scroll_layout.addWidget(basic_group)
        
        # Frequency bands - Inlet
        inlet_group = QGroupBox("Inlet Sound Power Levels")
        inlet_form = QFormLayout()
        
        for freq in self.frequency_bands:
            combo = self._create_column_combo()
            self.inlet_combos.append(combo)
            inlet_form.addRow(f"{freq} Hz:", combo)
        
        inlet_group.setLayout(inlet_form)
        scroll_layout.addWidget(inlet_group)
        
        # Frequency bands - Radiated
        radiated_group = QGroupBox("Radiated Sound Power Levels")
        radiated_form = QFormLayout()
        
        for freq in self.frequency_bands:
            combo = self._create_column_combo()
            self.radiated_combos.append(combo)
            radiated_form.addRow(f"{freq} Hz:", combo)
        
        radiated_group.setLayout(radiated_form)
        scroll_layout.addWidget(radiated_group)
        
        # Frequency bands - Outlet
        outlet_group = QGroupBox("Outlet Sound Power Levels")
        outlet_form = QFormLayout()
        
        for freq in self.frequency_bands:
            combo = self._create_column_combo()
            self.outlet_combos.append(combo)
            outlet_form.addRow(f"{freq} Hz:", combo)
        
        outlet_group.setLayout(outlet_form)
        scroll_layout.addWidget(outlet_group)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        auto_detect_btn = QPushButton("Auto-Detect Mapping")
        auto_detect_btn.clicked.connect(self._suggest_mapping)
        btn_layout.addWidget(auto_detect_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_mapping)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _create_column_combo(self) -> QComboBox:
        """Create a column selection combobox"""
        combo = QComboBox()
        combo.addItem("(Not Mapped)", -1)
        for i, header in enumerate(self.headers):
            combo.addItem(f"Column {i+1}: {header}", i)
        return combo
    
    def _format_sample_data(self) -> str:
        """Format sample data for display"""
        if not self.sample_data:
            return "No sample data available"
        
        lines = []
        
        # Headers
        header_line = " | ".join(f"{h[:15]:15}" for h in self.headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))
        
        # Sample rows (max 3)
        for row in self.sample_data[:3]:
            row_line = " | ".join(f"{str(cell)[:15]:15}" for cell in row[:len(self.headers)])
            lines.append(row_line)
        
        return "\n".join(lines)
    
    def _suggest_mapping(self):
        """Auto-detect and suggest column mapping"""
        from calculations.schedule_validator import ScheduleValidator
        
        validator = ScheduleValidator()
        suggested = validator.suggest_column_mapping(self.headers, self.sample_data)
        
        # Apply suggested mapping
        if suggested.name_col is not None:
            self.name_combo.setCurrentIndex(suggested.name_col + 1)  # +1 for "(Not Mapped)"
        
        if suggested.type_col is not None:
            self.type_combo.setCurrentIndex(suggested.type_col + 1)
        
        # Inlet
        inlet_cols = suggested.get_inlet_cols()
        for i, col_idx in enumerate(inlet_cols):
            if col_idx is not None and i < len(self.inlet_combos):
                self.inlet_combos[i].setCurrentIndex(col_idx + 1)
        
        # Radiated
        radiated_cols = suggested.get_radiated_cols()
        for i, col_idx in enumerate(radiated_cols):
            if col_idx is not None and i < len(self.radiated_combos):
                self.radiated_combos[i].setCurrentIndex(col_idx + 1)
        
        # Outlet
        outlet_cols = suggested.get_outlet_cols()
        for i, col_idx in enumerate(outlet_cols):
            if col_idx is not None and i < len(self.outlet_combos):
                self.outlet_combos[i].setCurrentIndex(col_idx + 1)
    
    def _clear_mapping(self):
        """Clear all column mappings"""
        self.name_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)
        
        for combo in self.inlet_combos + self.radiated_combos + self.outlet_combos:
            combo.setCurrentIndex(0)
    
    def _on_ok(self):
        """Validate and confirm mapping"""
        mapping = self.get_mapping()
        
        # Validate: at least name and some frequency values should be mapped
        if mapping["name_col"] is None:
            QMessageBox.warning(
                self,
                "Incomplete Mapping",
                "Unit Name column must be mapped."
            )
            return
        
        # Check if at least one frequency band set is mapped
        has_inlet = any(mapping["inlet_cols"])
        has_radiated = any(mapping["radiated_cols"])
        has_outlet = any(mapping["outlet_cols"])
        
        if not (has_inlet or has_radiated or has_outlet):
            QMessageBox.warning(
                self,
                "Incomplete Mapping",
                "At least one set of frequency bands (Inlet, Radiated, or Outlet) must be mapped."
            )
            return
        
        self.mapping_confirmed.emit(mapping)
        self.accept()
    
    def get_mapping(self) -> Dict:
        """
        Get the current mapping as a dictionary
        
        Returns:
            Dictionary with mapping information
        """
        def get_col_index(combo: QComboBox) -> Optional[int]:
            col = combo.currentData()
            return col if col >= 0 else None
        
        mapping = {
            "name_col": get_col_index(self.name_combo),
            "type_col": get_col_index(self.type_combo),
            "inlet_cols": [get_col_index(combo) for combo in self.inlet_combos],
            "radiated_cols": [get_col_index(combo) for combo in self.radiated_combos],
            "outlet_cols": [get_col_index(combo) for combo in self.outlet_combos],
        }
        
        return mapping
    
    @staticmethod
    def show_mapper(headers: List[str], sample_data: List[List[str]], parent=None) -> Optional[Dict]:
        """
        Convenience method to show mapper dialog and get result
        
        Args:
            headers: Column headers
            sample_data: Sample data rows
            parent: Parent widget
        
        Returns:
            Mapping dictionary if confirmed, None if cancelled
        """
        dialog = ColumnMapperDialog(headers, sample_data, parent)
        
        if dialog.exec() == QDialog.Accepted:
            return dialog.get_mapping()
        
        return None
