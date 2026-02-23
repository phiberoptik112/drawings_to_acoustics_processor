"""
Wall Type Library Dialog

Provides a simple interface for managing user-defined wall type codes
with STC ratings. Users read wall type codes (e.g., W1, W2, P1) from
project drawings and assign corresponding STC values here.

Used for LEED acoustic certification to document partition performance.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QSpinBox, QTextEdit, QFormLayout, QGroupBox,
    QDialogButtonBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import get_session, WallType


class WallTypeEditDialog(QDialog):
    """Dialog for adding or editing a single wall type."""

    def __init__(self, parent=None, wall_type: Optional[WallType] = None):
        super().__init__(parent)
        self.wall_type = wall_type
        self.is_editing = wall_type is not None

        self.setWindowTitle("Edit Wall Type" if self.is_editing else "Add Wall Type")
        self.setModal(True)
        self.resize(400, 300)

        self._build_ui()

        if self.is_editing:
            self._load_wall_type()

    def _build_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)

        # Form group
        form_group = QGroupBox("Wall Type Information")
        form_layout = QFormLayout()

        # Code input
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g., W1, W2, P1")
        self.code_edit.setMaxLength(50)
        form_layout.addRow("Type Code:", self.code_edit)

        # STC rating
        self.stc_spin = QSpinBox()
        self.stc_spin.setRange(20, 80)
        self.stc_spin.setValue(45)
        self.stc_spin.setSuffix(" STC")
        form_layout.addRow("STC Rating:", self.stc_spin)

        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g., GWB on metal stud")
        self.description_edit.setMaxLength(200)
        form_layout.addRow("Description:", self.description_edit)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes about this wall type...")
        self.notes_edit.setMaximumHeight(80)
        form_layout.addRow("Notes:", self.notes_edit)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Reference info
        info_label = QLabel(
            "Enter the wall type code as shown on the project drawings.\n"
            "The STC rating should match the specified partition assembly."
        )
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_wall_type(self):
        """Load existing wall type data into form."""
        if not self.wall_type:
            return

        self.code_edit.setText(self.wall_type.code or "")
        self.stc_spin.setValue(self.wall_type.stc_rating or 45)
        self.description_edit.setText(self.wall_type.description or "")
        self.notes_edit.setText(self.wall_type.notes or "")

    def _save(self):
        """Validate and accept the dialog."""
        code = self.code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, "Validation Error",
                                "Please enter a wall type code.")
            self.code_edit.setFocus()
            return

        self.accept()

    def get_data(self) -> dict:
        """Get the form data as a dictionary."""
        return {
            'code': self.code_edit.text().strip().upper(),
            'stc_rating': self.stc_spin.value(),
            'description': self.description_edit.text().strip() or None,
            'notes': self.notes_edit.toPlainText().strip() or None
        }


class WallTypeLibraryDialog(QDialog):
    """Dialog for managing wall type library."""

    # Signal emitted when wall types are modified
    wall_types_changed = Signal()

    def __init__(self, parent=None, project_id: Optional[int] = None):
        super().__init__(parent)
        self.project_id = project_id

        self.setWindowTitle("Wall Type Library")
        self.setModal(False)
        self.setWindowFlags(Qt.Window)
        self.resize(700, 450)

        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Wall Type Library")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        help_label = QLabel(
            "Define wall type codes from project drawings with their STC ratings."
        )
        help_label.setStyleSheet("color: #666;")
        header_layout.addWidget(help_label)
        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Code", "STC", "Description", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Wall Type")
        self.add_btn.clicked.connect(self._add_wall_type)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_selected)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        self.delete_btn.clicked.connect(self._delete_selected)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # STC reference info
        reference_group = QGroupBox("STC Reference")
        reference_layout = QVBoxLayout()
        reference_text = QLabel(
            "Typical STC values:\n"
            "  STC 35-39: Normal speech easily understood\n"
            "  STC 40-44: Loud speech audible but not intelligible\n"
            "  STC 45-49: Loud speech heard as murmur\n"
            "  STC 50-54: Loud speech barely audible\n"
            "  STC 55+: Excellent privacy"
        )
        reference_text.setStyleSheet("font-family: monospace; color: #444;")
        reference_layout.addWidget(reference_text)
        reference_group.setLayout(reference_layout)
        layout.addWidget(reference_group)

    def _refresh_table(self):
        """Refresh the table with current wall types."""
        self.table.setRowCount(0)

        if not self.project_id:
            return

        try:
            session = get_session()
            wall_types = (
                session.query(WallType)
                .filter(WallType.project_id == self.project_id)
                .order_by(WallType.code)
                .all()
            )

            for wt in wall_types:
                row = self.table.rowCount()
                self.table.insertRow(row)

                # Store wall type ID in first column item
                code_item = QTableWidgetItem(wt.code)
                code_item.setData(Qt.UserRole, wt.id)
                self.table.setItem(row, 0, code_item)

                self.table.setItem(row, 1, QTableWidgetItem(str(wt.stc_rating)))
                self.table.setItem(row, 2, QTableWidgetItem(wt.description or ""))
                self.table.setItem(row, 3, QTableWidgetItem(wt.notes or ""))

            session.close()

        except Exception as e:
            QMessageBox.warning(self, "Error",
                                f"Failed to load wall types:\n{e}")

    def _get_selected_wall_type_id(self) -> Optional[int]:
        """Get the ID of the currently selected wall type."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return None

        item = self.table.item(current_row, 0)
        if not item:
            return None

        return item.data(Qt.UserRole)

    def _add_wall_type(self):
        """Add a new wall type."""
        dialog = WallTypeEditDialog(self)

        if dialog.exec():
            data = dialog.get_data()

            try:
                session = get_session()

                # Check for duplicate code
                existing = (
                    session.query(WallType)
                    .filter(WallType.project_id == self.project_id)
                    .filter(WallType.code == data['code'])
                    .first()
                )

                if existing:
                    session.close()
                    QMessageBox.warning(
                        self, "Duplicate Code",
                        f"Wall type code '{data['code']}' already exists."
                    )
                    return

                wall_type = WallType(
                    project_id=self.project_id,
                    code=data['code'],
                    stc_rating=data['stc_rating'],
                    description=data['description'],
                    notes=data['notes']
                )
                session.add(wall_type)
                session.commit()
                session.close()

                self._refresh_table()
                self.wall_types_changed.emit()

            except Exception as e:
                QMessageBox.critical(self, "Error",
                                     f"Failed to add wall type:\n{e}")

    def _edit_selected(self):
        """Edit the selected wall type."""
        wall_type_id = self._get_selected_wall_type_id()
        if not wall_type_id:
            QMessageBox.information(self, "No Selection",
                                    "Please select a wall type to edit.")
            return

        try:
            session = get_session()
            wall_type = session.query(WallType).get(wall_type_id)

            if not wall_type:
                session.close()
                QMessageBox.warning(self, "Not Found",
                                    "Wall type not found.")
                return

            dialog = WallTypeEditDialog(self, wall_type)

            if dialog.exec():
                data = dialog.get_data()

                # Check for duplicate code (excluding current)
                existing = (
                    session.query(WallType)
                    .filter(WallType.project_id == self.project_id)
                    .filter(WallType.code == data['code'])
                    .filter(WallType.id != wall_type_id)
                    .first()
                )

                if existing:
                    session.close()
                    QMessageBox.warning(
                        self, "Duplicate Code",
                        f"Wall type code '{data['code']}' already exists."
                    )
                    return

                wall_type.code = data['code']
                wall_type.stc_rating = data['stc_rating']
                wall_type.description = data['description']
                wall_type.notes = data['notes']

                session.commit()
                self._refresh_table()
                self.wall_types_changed.emit()

            session.close()

        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to edit wall type:\n{e}")

    def _delete_selected(self):
        """Delete the selected wall type."""
        wall_type_id = self._get_selected_wall_type_id()
        if not wall_type_id:
            QMessageBox.information(self, "No Selection",
                                    "Please select a wall type to delete.")
            return

        current_row = self.table.currentRow()
        code = self.table.item(current_row, 0).text() if current_row >= 0 else ""

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete wall type '{code}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            session = get_session()
            wall_type = session.query(WallType).get(wall_type_id)

            if wall_type:
                session.delete(wall_type)
                session.commit()

            session.close()

            self._refresh_table()
            self.wall_types_changed.emit()

        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to delete wall type:\n{e}")


def show_wall_type_library(parent=None, project_id: Optional[int] = None):
    """Show the wall type library dialog."""
    dialog = WallTypeLibraryDialog(parent, project_id)
    return dialog.exec()
