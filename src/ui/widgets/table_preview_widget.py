"""
Table Preview Widget
-------------------
Side-by-side preview of source image and extracted table data
with editing, validation, and issue highlighting capabilities.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QScrollArea, QCheckBox,
    QTextEdit, QComboBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap, QBrush


class ValidationIssueType(Enum):
    """Types of validation issues"""
    MISSING_VALUE = "missing"
    INVALID_FORMAT = "invalid"
    OUT_OF_RANGE = "range"
    DUPLICATE = "duplicate"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """A validation issue for a cell or row"""
    row: int
    col: Optional[int] = None
    issue_type: ValidationIssueType = ValidationIssueType.WARNING
    message: str = ""
    auto_fixable: bool = False


@dataclass
class CellData:
    """Data for a single table cell"""
    value: str
    confidence: float = 1.0
    original_value: str = ""
    
    def __post_init__(self):
        if not self.original_value:
            self.original_value = self.value


class TablePreviewWidget(QWidget):
    """
    Side-by-side preview widget showing source image and editable table
    """
    
    data_modified = Signal()
    validation_changed = Signal(list)  # List of ValidationIssue
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data
        self.source_pixmap: Optional[QPixmap] = None
        self.table_data: List[List[CellData]] = []
        self.row_included: List[bool] = []
        self.headers: List[str] = []
        self.validation_issues: List[ValidationIssue] = []
        
        # State
        self.show_confidence = True
        self.auto_fix_enabled = True
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the widget UI"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.issues_label = QLabel("Issues: 0")
        self.issues_label.setStyleSheet("font-weight: bold; color: #f44336;")
        toolbar_layout.addWidget(self.issues_label)
        
        toolbar_layout.addSpacing(20)
        
        show_all_btn = QPushButton("Show All Issues")
        show_all_btn.clicked.connect(self._show_all_issues)
        toolbar_layout.addWidget(show_all_btn)
        
        self.auto_fix_btn = QPushButton("Auto-Fix Issues")
        self.auto_fix_btn.clicked.connect(self._auto_fix_issues)
        toolbar_layout.addWidget(self.auto_fix_btn)
        
        toolbar_layout.addStretch()
        
        self.confidence_check = QCheckBox("Show Confidence")
        self.confidence_check.setChecked(True)
        self.confidence_check.toggled.connect(self._toggle_confidence)
        toolbar_layout.addWidget(self.confidence_check)
        
        export_csv_btn = QPushButton("Export CSV...")
        export_csv_btn.clicked.connect(self._export_csv)
        toolbar_layout.addWidget(export_csv_btn)
        
        toolbar.setLayout(toolbar_layout)
        layout.addWidget(toolbar)
        
        # Main splitter: source image | table
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Source image with highlighting
        left_widget = self._create_source_panel()
        splitter.addWidget(left_widget)
        
        # Right: Editable table
        right_widget = self._create_table_panel()
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter, 1)
        
        # Validation summary
        self.validation_summary = QTextEdit()
        self.validation_summary.setReadOnly(True)
        self.validation_summary.setMaximumHeight(80)
        self.validation_summary.setPlaceholderText("Validation issues will appear here")
        layout.addWidget(self.validation_summary)
        
        self.setLayout(layout)
    
    def _create_source_panel(self) -> QWidget:
        """Create source image panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Source Image</b>"))
        
        self.highlight_combo = QComboBox()
        self.highlight_combo.addItems(["Headers", "Data", "Both", "None"])
        self.highlight_combo.setCurrentText("Data")
        self.highlight_combo.currentTextChanged.connect(self._update_source_highlighting)
        header_layout.addWidget(QLabel("Highlight:"))
        header_layout.addWidget(self.highlight_combo)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Image display (scrollable)
        scroll = QScrollArea()
        self.source_image_label = QLabel("No image loaded")
        self.source_image_label.setAlignment(Qt.AlignCenter)
        self.source_image_label.setStyleSheet("background: #f5f5f5; border: 1px solid #ccc;")
        self.source_image_label.setMinimumSize(300, 200)
        scroll.setWidget(self.source_image_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setMaximumWidth(30)
        zoom_layout.addWidget(zoom_out_btn)
        zoom_layout.addWidget(QLabel("Zoom"))
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setMaximumWidth(30)
        zoom_layout.addWidget(zoom_in_btn)
        fit_btn = QPushButton("Fit")
        zoom_layout.addWidget(fit_btn)
        zoom_layout.addStretch()
        layout.addLayout(zoom_layout)
        
        widget.setLayout(layout)
        return widget
    
    def _create_table_panel(self) -> QWidget:
        """Create editable table panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Extracted Data (Editable)</b>"))
        header_layout.addStretch()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_rows)
        header_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all_rows)
        header_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(header_layout)
        
        # Table
        self.data_table = QTableWidget()
        self.data_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.data_table.itemChanged.connect(self._on_cell_changed)
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.data_table, 1)
        
        widget.setLayout(layout)
        return widget
    
    def set_source_image(self, pixmap: QPixmap):
        """Set the source image"""
        self.source_pixmap = pixmap
        self._update_source_display()
    
    def set_table_data(self, data: List[List[str]], headers: Optional[List[str]] = None, confidences: Optional[List[List[float]]] = None):
        """
        Set the table data
        
        Args:
            data: 2D list of cell values
            headers: Optional column headers
            confidences: Optional 2D list of confidence scores (0.0-1.0)
        """
        self.table_data = []
        self.row_included = []
        
        for i, row in enumerate(data):
            cell_row = []
            for j, cell_value in enumerate(row):
                confidence = 1.0
                if confidences and i < len(confidences) and j < len(confidences[i]):
                    confidence = confidences[i][j]
                
                cell_row.append(CellData(
                    value=cell_value,
                    confidence=confidence,
                    original_value=cell_value
                ))
            self.table_data.append(cell_row)
            self.row_included.append(True)
        
        if headers:
            self.headers = headers
        else:
            # Auto-generate headers
            max_cols = max(len(row) for row in data) if data else 0
            self.headers = [f"Col {i+1}" for i in range(max_cols)]
        
        self._populate_table()
        self._validate_data()
    
    def _populate_table(self):
        """Populate the data table widget"""
        if not self.table_data:
            return
        
        num_rows = len(self.table_data)
        max_cols = max(len(row) for row in self.table_data)
        
        # Add Include column
        self.data_table.setColumnCount(max_cols + 1)
        self.data_table.setRowCount(num_rows)
        
        # Set headers
        headers = ["Include"] + self.headers[:max_cols]
        self.data_table.setHorizontalHeaderLabels(headers)
        
        # Block signals during population
        self.data_table.blockSignals(True)
        
        for i, row in enumerate(self.table_data):
            # Include checkbox
            include_item = QTableWidgetItem()
            include_item.setCheckState(Qt.Checked if self.row_included[i] else Qt.Unchecked)
            include_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            self.data_table.setItem(i, 0, include_item)
            
            # Data cells
            for j, cell in enumerate(row):
                item = QTableWidgetItem(cell.value)
                
                # Color code by confidence if enabled
                if self.show_confidence:
                    if cell.confidence < 0.5:
                        item.setBackground(QBrush(QColor(255, 200, 200)))  # Red - low confidence
                    elif cell.confidence < 0.8:
                        item.setBackground(QBrush(QColor(255, 255, 200)))  # Yellow - medium confidence
                
                # Set tooltip with confidence
                if self.show_confidence:
                    item.setToolTip(f"Confidence: {cell.confidence:.0%}\nOriginal: {cell.original_value}")
                
                self.data_table.setItem(i, j + 1, item)
        
        self.data_table.blockSignals(False)
        
        # Resize columns to content
        self.data_table.resizeColumnsToContents()
        self.data_table.setColumnWidth(0, 60)  # Include column
    
    def _validate_data(self):
        """Validate table data and highlight issues"""
        self.validation_issues.clear()
        
        if not self.table_data:
            return
        
        # Check for missing values
        for i, row in enumerate(self.table_data):
            for j, cell in enumerate(row):
                if not cell.value.strip():
                    self.validation_issues.append(ValidationIssue(
                        row=i,
                        col=j,
                        issue_type=ValidationIssueType.MISSING_VALUE,
                        message=f"Row {i+1}, Col {j+1}: Missing value",
                        auto_fixable=False
                    ))
        
        # Check for invalid numeric values (if expected)
        # TODO: Add more sophisticated validation based on column type
        
        # Check for duplicate names (if first column is name)
        if self.table_data:
            names = {}
            for i, row in enumerate(self.table_data):
                if row:
                    name = row[0].value.strip()
                    if name:
                        if name in names:
                            self.validation_issues.append(ValidationIssue(
                                row=i,
                                col=0,
                                issue_type=ValidationIssueType.DUPLICATE,
                                message=f"Row {i+1}: Duplicate name '{name}' (also in row {names[name]+1})",
                                auto_fixable=False
                            ))
                        else:
                            names[name] = i
        
        self._update_validation_display()
    
    def _update_validation_display(self):
        """Update validation issue display"""
        count = len(self.validation_issues)
        self.issues_label.setText(f"Issues: {count}")
        
        if count == 0:
            self.validation_summary.setPlainText("✓ No validation issues found")
            self.validation_summary.setStyleSheet("color: #4CAF50;")
            self.auto_fix_btn.setEnabled(False)
        else:
            # Group issues by type
            missing = [i for i in self.validation_issues if i.issue_type == ValidationIssueType.MISSING_VALUE]
            invalid = [i for i in self.validation_issues if i.issue_type == ValidationIssueType.INVALID_FORMAT]
            duplicates = [i for i in self.validation_issues if i.issue_type == ValidationIssueType.DUPLICATE]
            
            summary = []
            if missing:
                summary.append(f"⚠ {len(missing)} missing value(s)")
            if invalid:
                summary.append(f"⚠ {len(invalid)} invalid format(s)")
            if duplicates:
                summary.append(f"⚠ {len(duplicates)} duplicate(s)")
            
            self.validation_summary.setPlainText("\n".join(summary))
            self.validation_summary.setStyleSheet("color: #f44336;")
            
            # Check if any auto-fixable
            fixable = any(i.auto_fixable for i in self.validation_issues)
            self.auto_fix_btn.setEnabled(fixable)
        
        # Highlight cells with issues
        self._highlight_issues()
        
        self.validation_changed.emit(self.validation_issues)
    
    def _highlight_issues(self):
        """Highlight cells with validation issues"""
        # Reset backgrounds first
        for i in range(self.data_table.rowCount()):
            for j in range(1, self.data_table.columnCount()):  # Skip Include column
                item = self.data_table.item(i, j)
                if item:
                    # Reset to confidence-based color or white
                    if self.show_confidence and i < len(self.table_data) and (j-1) < len(self.table_data[i]):
                        cell = self.table_data[i][j-1]
                        if cell.confidence < 0.5:
                            item.setBackground(QBrush(QColor(255, 200, 200)))
                        elif cell.confidence < 0.8:
                            item.setBackground(QBrush(QColor(255, 255, 200)))
                        else:
                            item.setBackground(QBrush(QColor(255, 255, 255)))
                    else:
                        item.setBackground(QBrush(QColor(255, 255, 255)))
        
        # Apply issue highlighting
        for issue in self.validation_issues:
            if issue.col is not None:
                item = self.data_table.item(issue.row, issue.col + 1)  # +1 for Include column
                if item:
                    if issue.issue_type == ValidationIssueType.MISSING_VALUE:
                        item.setBackground(QBrush(QColor(255, 100, 100)))  # Red
                    elif issue.issue_type == ValidationIssueType.DUPLICATE:
                        item.setBackground(QBrush(QColor(255, 165, 0)))  # Orange
                    elif issue.issue_type == ValidationIssueType.INVALID_FORMAT:
                        item.setBackground(QBrush(QColor(255, 255, 100)))  # Yellow
                    
                    # Add issue to tooltip
                    current_tip = item.toolTip()
                    item.setToolTip(f"{current_tip}\n⚠ {issue.message}" if current_tip else f"⚠ {issue.message}")
    
    def _show_all_issues(self):
        """Show detailed list of all issues"""
        if not self.validation_issues:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Validation", "No validation issues found!")
            return
        
        # Build detailed message
        msg = "Validation Issues:\n\n"
        for i, issue in enumerate(self.validation_issues, 1):
            msg += f"{i}. {issue.message}\n"
        
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Validation Issues", msg)
    
    def _auto_fix_issues(self):
        """Automatically fix auto-fixable issues"""
        fixed_count = 0
        for issue in self.validation_issues:
            if issue.auto_fixable:
                # Apply fix based on issue type
                # TODO: Implement specific fixes
                fixed_count += 1
        
        if fixed_count > 0:
            self._validate_data()
            self.data_modified.emit()
        
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Auto-Fix", f"Fixed {fixed_count} issue(s)")
    
    def _toggle_confidence(self, checked: bool):
        """Toggle confidence display"""
        self.show_confidence = checked
        self._populate_table()
    
    def _on_cell_changed(self, item: QTableWidgetItem):
        """Handle cell value change"""
        row = item.row()
        col = item.column()
        
        if col == 0:
            # Include checkbox changed
            self.row_included[row] = (item.checkState() == Qt.Checked)
        else:
            # Data cell changed
            new_value = item.text()
            if row < len(self.table_data) and (col-1) < len(self.table_data[row]):
                self.table_data[row][col-1].value = new_value
                self._validate_data()
        
        self.data_modified.emit()
    
    def _update_source_display(self):
        """Update source image display"""
        if self.source_pixmap:
            scaled = self.source_pixmap.scaled(
                400, 400,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.source_image_label.setPixmap(scaled)
        else:
            self.source_image_label.setText("No image loaded")
    
    def _update_source_highlighting(self, mode: str):
        """Update source image highlighting"""
        # TODO: Implement highlighting overlay on source image
        pass
    
    def _select_all_rows(self):
        """Select all rows for import"""
        self.data_table.blockSignals(True)
        for i in range(len(self.row_included)):
            self.row_included[i] = True
            item = self.data_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Checked)
        self.data_table.blockSignals(False)
        self.data_modified.emit()
    
    def _deselect_all_rows(self):
        """Deselect all rows"""
        self.data_table.blockSignals(True)
        for i in range(len(self.row_included)):
            self.row_included[i] = False
            item = self.data_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self.data_table.blockSignals(False)
        self.data_modified.emit()
    
    def _export_csv(self):
        """Export current table to CSV"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Table to CSV",
            "",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write headers
                    writer.writerow(self.headers)
                    # Write data rows
                    for i, row in enumerate(self.table_data):
                        if self.row_included[i]:
                            writer.writerow([cell.value for cell in row])
                
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Export", f"Table exported to:\n{file_path}")
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")
    
    def get_validated_data(self) -> List[Dict[str, Any]]:
        """
        Get validated table data as list of dictionaries
        Only includes rows marked for inclusion
        """
        result = []
        for i, row in enumerate(self.table_data):
            if self.row_included[i]:
                row_dict = {}
                for j, cell in enumerate(row):
                    if j < len(self.headers):
                        row_dict[self.headers[j]] = cell.value
                result.append(row_dict)
        return result
    
    def has_validation_errors(self) -> bool:
        """Check if there are any validation errors (not warnings)"""
        return any(
            issue.issue_type in [ValidationIssueType.MISSING_VALUE, ValidationIssueType.INVALID_FORMAT]
            for issue in self.validation_issues
        )
    
    def get_included_row_count(self) -> int:
        """Get count of rows marked for inclusion"""
        return sum(1 for included in self.row_included if included)
