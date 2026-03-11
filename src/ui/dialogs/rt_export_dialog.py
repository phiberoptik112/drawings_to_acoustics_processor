"""
RT Export Dialog — Space selection and export options for RT60 acoustic report generation.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QRadioButton, QButtonGroup,
    QFileDialog, QLineEdit, QGroupBox, QMessageBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt


class RTExportDialog(QDialog):
    """
    Dialog that lets the user:
      1. Select which project spaces to include (checkbox list, all checked by default)
      2. Choose export format: PDF (single file) or PNG (one image per space)
      3. Choose the output file / folder path
    """

    def __init__(self, parent, project_id: int):
        super().__init__(parent)
        self.project_id = project_id
        self._spaces: list = []

        # Outputs populated on accept()
        self.selected_space_ids: list = []
        self.export_format: str = 'pdf'
        self.export_path: str = ''

        self._load_spaces()
        self._init_ui()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_spaces(self):
        try:
            from models import get_session
            from models.space import Space

            session = get_session()
            try:
                self._spaces = (
                    session.query(Space)
                    .filter(Space.project_id == self.project_id)
                    .order_by(Space.name)
                    .all()
                )
                # Touch attributes while session is open
                for sp in self._spaces:
                    _ = sp.id, sp.name, sp.room_type, sp.volume
            finally:
                session.close()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(f'Failed to load spaces: {exc}')

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        self.setWindowTitle('Export RT60 Report')
        self.setMinimumSize(540, 580)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # ---- Space selection ----
        space_group = QGroupBox('Select Spaces to Export')
        space_vbox = QVBoxLayout()
        space_vbox.setSpacing(6)

        # Select / Deselect all buttons
        sel_row = QHBoxLayout()
        sel_all_btn = QPushButton('Select All')
        sel_all_btn.setFixedWidth(90)
        sel_all_btn.clicked.connect(self._select_all)
        desel_btn = QPushButton('Deselect All')
        desel_btn.setFixedWidth(90)
        desel_btn.clicked.connect(self._deselect_all)
        sel_row.addWidget(sel_all_btn)
        sel_row.addWidget(desel_btn)
        sel_row.addStretch()
        space_vbox.addLayout(sel_row)

        self._space_list = QListWidget()
        self._space_list.setSelectionMode(QAbstractItemView.NoSelection)
        self._space_list.setAlternatingRowColors(True)

        if self._spaces:
            for space in self._spaces:
                item = QListWidgetItem()
                rt_label = (space.room_type or 'Custom').replace('_', ' ').title()
                vol_str  = f"{space.volume:,.0f} cu ft" if space.volume else 'no volume set'
                item.setText(f"  {space.name}   ({rt_label} — {vol_str})")
                item.setData(Qt.UserRole, space.id)
                item.setCheckState(Qt.Checked)
                self._space_list.addItem(item)
        else:
            placeholder = QListWidgetItem('No spaces found in this project.')
            placeholder.setFlags(Qt.NoItemFlags)
            self._space_list.addItem(placeholder)

        space_vbox.addWidget(self._space_list)
        space_group.setLayout(space_vbox)
        layout.addWidget(space_group)

        # ---- Export format ----
        fmt_group = QGroupBox('Export Format')
        fmt_vbox = QVBoxLayout()

        self._radio_pdf = QRadioButton(
            'PDF  — all selected spaces in a single file  (one page per space)'
        )
        self._radio_png = QRadioButton(
            'PNG  — one image file per space, saved into a folder'
        )
        self._radio_pdf.setChecked(True)
        self._radio_pdf.toggled.connect(self._on_format_changed)

        btn_group = QButtonGroup(self)
        btn_group.addButton(self._radio_pdf, 0)
        btn_group.addButton(self._radio_png, 1)

        fmt_vbox.addWidget(self._radio_pdf)
        fmt_vbox.addWidget(self._radio_png)
        fmt_group.setLayout(fmt_vbox)
        layout.addWidget(fmt_group)

        # ---- Output path ----
        path_group = QGroupBox('Export Location')
        path_row = QHBoxLayout()

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText('Click Browse to choose a file or folder...')
        self._path_edit.setReadOnly(True)

        browse_btn = QPushButton('Browse…')
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_path)

        path_row.addWidget(self._path_edit)
        path_row.addWidget(browse_btn)
        path_group.setLayout(path_row)
        layout.addWidget(path_group)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        self._export_btn = QPushButton('Export')
        self._export_btn.setDefault(True)
        self._export_btn.setFixedWidth(90)
        self._export_btn.clicked.connect(self._on_export_clicked)

        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(self._export_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _select_all(self):
        for i in range(self._space_list.count()):
            item = self._space_list.item(i)
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(Qt.Checked)

    def _deselect_all(self):
        for i in range(self._space_list.count()):
            item = self._space_list.item(i)
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(Qt.Unchecked)

    def _on_format_changed(self):
        # Clear path when format changes so user picks a new location
        self._path_edit.clear()

    def _browse_path(self):
        if self._radio_pdf.isChecked():
            path, _ = QFileDialog.getSaveFileName(
                self,
                'Save RT60 Report PDF',
                'RT60_Report.pdf',
                'PDF Files (*.pdf);;All Files (*)',
            )
        else:
            path = QFileDialog.getExistingDirectory(
                self,
                'Select Folder for PNG Images',
            )
        if path:
            self._path_edit.setText(path)

    def _on_export_clicked(self):
        # Validate: at least one space selected
        selected_ids = []
        for i in range(self._space_list.count()):
            item = self._space_list.item(i)
            if (item.flags() & Qt.ItemIsEnabled) and item.checkState() == Qt.Checked:
                selected_ids.append(item.data(Qt.UserRole))

        if not selected_ids:
            QMessageBox.warning(
                self, 'No Spaces Selected',
                'Please select at least one space to include in the report.',
            )
            return

        # Validate: path chosen
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(
                self, 'No Export Location',
                'Please choose an export location using the Browse button.',
            )
            return

        self.selected_space_ids = selected_ids
        self.export_format = 'pdf' if self._radio_pdf.isChecked() else 'png'
        self.export_path = path
        self.accept()
