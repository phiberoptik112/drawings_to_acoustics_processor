"""
Drawing Spaces Panel - Collapsible panel listing spaces on the current drawing by PDF page.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models import get_session
from models.space import RoomBoundary, Space
from sqlalchemy.orm import joinedload


def _boundary_center(boundary: RoomBoundary) -> tuple:
    """Return center x/y for a room boundary."""
    cx = boundary.x_position + (boundary.width / 2.0)
    cy = boundary.y_position + (boundary.height / 2.0)
    return cx, cy


class DrawingSpacesPanel(QWidget):
    """Collapsible panel showing spaces on the current drawing, grouped by page."""

    page_navigate_requested = Signal(int)
    space_navigate_requested = Signal(int, float, float)

    def __init__(self, drawing_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.drawing_id = drawing_id
        self._current_page: Optional[int] = None
        self._page_items: Dict[int, QTreeWidgetItem] = {}
        self._init_ui()
        if drawing_id is not None:
            self.refresh()

    def _init_ui(self):
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet("""
            DrawingSpacesPanel {
                background-color: #f5f5f5;
                color: #333;
            }
            DrawingSpacesPanel QWidget {
                background-color: #f5f5f5;
                color: #333;
            }
            DrawingSpacesPanel QLabel {
                color: #333;
                background-color: transparent;
            }
            DrawingSpacesPanel QPushButton, DrawingSpacesPanel QToolButton {
                background-color: #e0e0e0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px 8px;
            }
            DrawingSpacesPanel QPushButton:hover, DrawingSpacesPanel QToolButton:hover {
                background-color: #d0d0d0;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        self.collapse_btn = QToolButton()
        self.collapse_btn.setText("◀")
        self.collapse_btn.setToolTip("Collapse panel")
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.collapse_btn)

        title_label = QLabel("Drawing Spaces")
        title_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        refresh_row = QHBoxLayout()
        self.refresh_btn = QPushButton("⟳ Refresh")
        self.refresh_btn.setToolTip("Reload spaces for this drawing")
        self.refresh_btn.clicked.connect(self.refresh)
        refresh_row.addWidget(self.refresh_btn)
        refresh_row.addStretch()
        content_layout.addLayout(refresh_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Space", "Count"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 200)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        content_layout.addWidget(self.tree, 1)

        self.summary_label = QLabel("No spaces on this drawing")
        self.summary_label.setStyleSheet("color: #888; font-style: italic;")
        content_layout.addWidget(self.summary_label)

        layout.addWidget(self.content_widget, 1)
        self.setLayout(layout)

    def _toggle_collapse(self):
        if self.content_widget.isVisible():
            self.content_widget.hide()
            self.collapse_btn.setText("▶")
            self.collapse_btn.setToolTip("Expand panel")
            self.setMaximumWidth(40)
        else:
            self.content_widget.show()
            self.collapse_btn.setText("◀")
            self.collapse_btn.setToolTip("Collapse panel")
            self.setMaximumWidth(16777215)

    def collapse(self):
        if self.content_widget.isVisible():
            self._toggle_collapse()

    def expand(self):
        if not self.content_widget.isVisible():
            self._toggle_collapse()

    def set_drawing_id(self, drawing_id: int):
        self.drawing_id = drawing_id
        self.refresh()

    def set_current_page(self, page_number: int):
        """Highlight the tree row for the active PDF page."""
        self._current_page = page_number
        normal_font = QFont("Arial", 10, QFont.Bold)
        highlight_font = QFont("Arial", 10, QFont.Bold)

        for page_num, item in self._page_items.items():
            if page_num == page_number:
                item.setFont(0, highlight_font)
                item.setForeground(0, QColor("#1565C0"))
            else:
                item.setFont(0, normal_font)
                item.setForeground(0, QColor("#333333"))

    def refresh(self):
        """Reload the space tree for the current drawing."""
        self.tree.clear()
        self._page_items.clear()

        if not self.drawing_id:
            self.summary_label.setText("No drawing loaded")
            return

        session = None
        try:
            session = get_session()
            boundaries = (
                session.query(RoomBoundary)
                .options(joinedload(RoomBoundary.space))
                .filter(RoomBoundary.drawing_id == self.drawing_id)
                .order_by(RoomBoundary.page_number, RoomBoundary.id)
                .all()
            )

            spaces_on_drawing = (
                session.query(Space)
                .filter(Space.drawing_id == self.drawing_id)
                .all()
            )

            placed_space_ids: Set[int] = set()
            pages: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

            for boundary in boundaries:
                space = boundary.space
                if not space:
                    continue
                page_num = boundary.page_number or 1
                cx, cy = _boundary_center(boundary)
                entry = {
                    "space_id": space.id,
                    "name": space.name or "Unnamed Space",
                    "page_number": page_num,
                    "center_x": cx,
                    "center_y": cy,
                }
                existing_ids = {e["space_id"] for e in pages[page_num]}
                if space.id not in existing_ids:
                    pages[page_num].append(entry)
                    placed_space_ids.add(space.id)

            unplaced: List[Space] = [
                s for s in spaces_on_drawing if s.id not in placed_space_ids
            ]

            total_spaces = sum(len(v) for v in pages.values()) + len(unplaced)
            if total_spaces == 0:
                self.summary_label.setText("No spaces on this drawing")
                return

            for page_num in sorted(pages.keys()):
                spaces_on_page = pages[page_num]
                page_label = f"Page {page_num}" if page_num > 1 else "Page 1"
                page_item = QTreeWidgetItem(self.tree)
                page_item.setText(0, f"📋 {page_label}")
                page_item.setText(1, str(len(spaces_on_page)))
                page_item.setFont(0, QFont("Arial", 10, QFont.Bold))
                page_item.setData(
                    0,
                    Qt.UserRole,
                    {"type": "page", "page_number": page_num},
                )
                page_item.setExpanded(True)
                self._page_items[page_num] = page_item

                for entry in sorted(spaces_on_page, key=lambda e: e["name"].lower()):
                    space_item = QTreeWidgetItem(page_item)
                    space_item.setText(0, f"  🏠 {entry['name']}")
                    space_item.setData(0, Qt.UserRole, {"type": "space", **entry})
                    space_item.setForeground(0, QColor("#90CAF9"))

            if unplaced:
                unplaced_item = QTreeWidgetItem(self.tree)
                unplaced_item.setText(0, "📋 Unplaced")
                unplaced_item.setText(1, str(len(unplaced)))
                unplaced_item.setFont(0, QFont("Arial", 10, QFont.Bold))
                unplaced_item.setExpanded(True)

                for space in sorted(unplaced, key=lambda s: (s.name or "").lower()):
                    space_item = QTreeWidgetItem(unplaced_item)
                    space_item.setText(0, f"  🏠 {space.name or 'Unnamed Space'}")
                    space_item.setData(
                        0,
                        Qt.UserRole,
                        {
                            "type": "space",
                            "space_id": space.id,
                            "page_number": None,
                            "center_x": None,
                            "center_y": None,
                        },
                    )
                    space_item.setForeground(0, QColor("#90CAF9"))

            self.summary_label.setText(
                f"{total_spaces} space{'s' if total_spaces != 1 else ''} on this drawing"
            )

            if self._current_page is not None:
                self.set_current_page(self._current_page)

        except Exception as e:
            self.summary_label.setText(f"Error loading spaces: {e}")
        finally:
            if session is not None:
                session.close()

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        payload = item.data(0, Qt.UserRole)
        if not payload or not isinstance(payload, dict):
            return

        item_type = payload.get("type")
        if item_type == "page":
            page_number = payload.get("page_number")
            if page_number is not None:
                self.page_navigate_requested.emit(int(page_number))
        elif item_type == "space":
            page_number = payload.get("page_number")
            center_x = payload.get("center_x")
            center_y = payload.get("center_y")
            if page_number is None:
                return
            if center_x is not None and center_y is not None:
                self.space_navigate_requested.emit(
                    int(page_number), float(center_x), float(center_y)
                )
            else:
                self.page_navigate_requested.emit(int(page_number))
