"""
NC Results Table Widget - Displays cumulative octave band values along HVAC path

Shows cumulative noise levels at each path element with NC rating color coding
and silencer row highlighting. Supports real-time updates during silencer
placement mode with revert capability.
"""

from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette, QBrush


# Octave band frequencies for column headers
OCTAVE_BANDS = ['63', '125', '250', '500', '1k', '2k', '4k']
# Full column headers including element name and NC rating
COLUMN_HEADERS = ['Element'] + OCTAVE_BANDS + ['NC']


class NCResultsTableWidget(QWidget):
    """
    Table widget showing cumulative noise levels along an HVAC path.

    Features:
    - Displays cumulative dB values at each path element (source -> terminal)
    - NC column with color coding: green (under target), yellow (within 3), red (over)
    - Silencer rows highlighted with themed light red background
    - Revert capability for cancel operations during silencer placement

    Signals:
        element_selected: Emitted when a row is clicked, (element_type, element_id)
    """

    element_selected = Signal(str, int)  # (element_type, element_id)

    def __init__(self, parent=None, target_nc: int = 35):
        super().__init__(parent)
        self._target_nc = target_nc
        self._last_saved_results: List[Dict] = []
        self._element_mapping: List[Dict] = []  # Maps row index to element info

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)

        # Configure table behavior
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        # Configure column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Element column stretches
        for i in range(1, len(COLUMN_HEADERS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # Make headers sticky (default behavior with QTableWidget)
        self.table.verticalHeader().setVisible(False)

        # Connect selection signal
        self.table.cellClicked.connect(self._on_cell_clicked)

        layout.addWidget(self.table)

    def set_target_nc(self, target_nc: int):
        """Set the target NC rating for color coding"""
        self._target_nc = target_nc
        # Refresh colors if we have data
        if self.table.rowCount() > 0:
            self._refresh_nc_colors()

    def update_results(self, element_results: List[Dict], is_live_update: bool = False):
        """
        Update the table with path element results.

        Args:
            element_results: List of dicts with keys:
                - element_type: 'source', 'segment', 'silencer', 'fitting', 'terminal'
                - element_name: Display name
                - element_id: Database ID (optional)
                - cumulative_spectrum: List[float] with 7 octave band values (63-4000 Hz)
                - nc_rating: NC rating at this point in path
                - is_silencer: bool, True for silencer elements
            is_live_update: If True, don't save as last known state (for live drag updates)
        """
        if not is_live_update:
            self._last_saved_results = element_results.copy()

        self._element_mapping = []
        self.table.setRowCount(len(element_results))

        for row, result in enumerate(element_results):
            self._populate_row(row, result)
            self._element_mapping.append({
                'element_type': result.get('element_type', 'unknown'),
                'element_id': result.get('element_id'),
                'is_silencer': result.get('is_silencer', False),
            })

        # Apply styling
        self._refresh_silencer_highlighting()
        self._refresh_nc_colors()

    def _populate_row(self, row: int, result: Dict):
        """Populate a single row with element data"""
        # Element name column
        element_name = result.get('element_name', 'Unknown')
        name_item = QTableWidgetItem(element_name)
        name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, 0, name_item)

        # Octave band columns (cumulative values)
        spectrum = result.get('cumulative_spectrum', [0.0] * 7)
        for col, value in enumerate(spectrum[:7], start=1):
            value_str = f"{value:.1f}" if value > 0 else "-"
            item = QTableWidgetItem(value_str)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)

        # NC rating column
        nc_rating = result.get('nc_rating', 0)
        nc_str = f"NC-{int(nc_rating)}" if nc_rating > 0 else "-"
        nc_item = QTableWidgetItem(nc_str)
        nc_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, len(COLUMN_HEADERS) - 1, nc_item)

    def _refresh_silencer_highlighting(self):
        """Apply light red background to silencer rows (themed)"""
        # Get palette for theme-aware colors
        palette = self.palette()
        base_color = palette.color(QPalette.Base)

        # Determine if dark or light theme based on base lightness
        is_dark_theme = base_color.lightness() < 128

        # Choose appropriate silencer highlight color
        if is_dark_theme:
            # Dark theme: darker red that's still visible
            silencer_color = QColor(80, 40, 40)  # Dark red
        else:
            # Light theme: light red/pink
            silencer_color = QColor(255, 230, 230)  # Light pink/red

        for row in range(self.table.rowCount()):
            if row < len(self._element_mapping):
                mapping = self._element_mapping[row]
                if mapping.get('is_silencer', False):
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(QBrush(silencer_color))

    def _refresh_nc_colors(self):
        """Apply green/yellow/red color coding to NC column"""
        nc_col = len(COLUMN_HEADERS) - 1

        for row in range(self.table.rowCount()):
            item = self.table.item(row, nc_col)
            if item and item.text() != "-":
                try:
                    # Parse NC rating from "NC-XX" format
                    nc_text = item.text()
                    nc_value = int(nc_text.replace("NC-", ""))
                    color = self._get_nc_color(nc_value)
                    item.setForeground(QBrush(color))
                except (ValueError, AttributeError):
                    pass

    def _get_nc_color(self, nc_rating: int) -> QColor:
        """
        Get color for NC rating based on target.

        Returns:
            Green if nc_rating <= target_nc
            Yellow if nc_rating <= target_nc + 3
            Red if nc_rating > target_nc + 3
        """
        if nc_rating <= self._target_nc:
            return QColor(34, 139, 34)  # Forest green
        elif nc_rating <= self._target_nc + 3:
            return QColor(218, 165, 32)  # Goldenrod/yellow
        else:
            return QColor(220, 20, 60)  # Crimson red

    def _on_cell_clicked(self, row: int, column: int):
        """Handle cell click to emit element selection"""
        if row < len(self._element_mapping):
            mapping = self._element_mapping[row]
            element_type = mapping.get('element_type', 'unknown')
            element_id = mapping.get('element_id')
            if element_id is not None:
                self.element_selected.emit(element_type, element_id)

    def revert_to_saved(self):
        """Revert table to last saved state (for cancel operations)"""
        if self._last_saved_results:
            self.update_results(self._last_saved_results, is_live_update=False)
        else:
            self.clear()

    def clear(self):
        """Clear all data from the table"""
        self.table.setRowCount(0)
        self._element_mapping = []

    def get_target_nc(self) -> int:
        """Get the current target NC rating"""
        return self._target_nc
