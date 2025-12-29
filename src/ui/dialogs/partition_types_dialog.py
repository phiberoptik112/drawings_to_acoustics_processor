"""
Partition Types Library Dialog - Manage project-level partition assemblies and reference PDFs.

This dialog allows users to:
- View and manage a library of partition assembly types with STC ratings
- Import a reference PDF showing the project's partition schedule
- View the reference PDF while editing partition types
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QLineEdit, QSpinBox, QTextEdit, QFileDialog, QMessageBox,
    QHeaderView, QWidget, QFormLayout, QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage

from models import get_session
from models.database import get_hvac_session
from models.partition import PartitionType, PartitionScheduleDocument

# Try to import PDF rendering
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    print("Warning: PyMuPDF not available - PDF preview disabled")


class PDFPreviewWidget(QWidget):
    """Widget to display a PDF page as preview"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pdf_path = None
        self.current_page = 0
        self.pdf_document = None
        self.zoom_level = 1.0
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # PDF display label
        self.pdf_label = QLabel("No PDF loaded")
        self.pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_label.setMinimumSize(400, 500)
        self.pdf_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.pdf_label, 1)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        controls_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 0 / 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        controls_layout.addWidget(self.next_btn)
        
        controls_layout.addStretch()
        
        # Zoom controls
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setMaximumWidth(30)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setMaximumWidth(30)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.zoom_in_btn)
        
        layout.addLayout(controls_layout)
        self.setLayout(layout)
    
    def load_pdf(self, pdf_path, page=0):
        """Load a PDF file and display the specified page"""
        if not HAS_PYMUPDF:
            self.pdf_label.setText("PDF preview not available\n(PyMuPDF not installed)")
            return False
        
        if not pdf_path or not os.path.exists(pdf_path):
            self.pdf_label.setText("PDF file not found")
            return False
        
        try:
            if self.pdf_document:
                self.pdf_document.close()
            
            self.pdf_document = fitz.open(pdf_path)
            self.current_pdf_path = pdf_path
            self.current_page = min(page, len(self.pdf_document) - 1)
            
            self.update_controls()
            self.render_page()
            return True
            
        except Exception as e:
            self.pdf_label.setText(f"Error loading PDF:\n{str(e)}")
            return False
    
    def render_page(self):
        """Render the current page"""
        if not self.pdf_document or not HAS_PYMUPDF:
            return
        
        try:
            page = self.pdf_document[self.current_page]
            
            # Calculate zoom matrix
            mat = fitz.Matrix(self.zoom_level * 1.5, self.zoom_level * 1.5)
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to QImage
            img = QImage(
                pix.samples, pix.width, pix.height,
                pix.stride, QImage.Format.Format_RGB888
            )
            
            # Scale to fit label if needed
            label_size = self.pdf_label.size()
            pixmap = QPixmap.fromImage(img)
            
            if pixmap.width() > label_size.width() or pixmap.height() > label_size.height():
                pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            self.pdf_label.setPixmap(pixmap)
            
        except Exception as e:
            self.pdf_label.setText(f"Error rendering page:\n{str(e)}")
    
    def update_controls(self):
        """Update navigation controls"""
        if self.pdf_document:
            total_pages = len(self.pdf_document)
            self.page_label.setText(f"Page {self.current_page + 1} / {total_pages}")
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < total_pages - 1)
        else:
            self.page_label.setText("Page 0 / 0")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
        
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_controls()
            self.render_page()
    
    def next_page(self):
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.update_controls()
            self.render_page()
    
    def zoom_in(self):
        if self.zoom_level < 3.0:
            self.zoom_level += 0.25
            self.update_controls()
            self.render_page()
    
    def zoom_out(self):
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.25
            self.update_controls()
            self.render_page()
    
    def get_current_page(self):
        return self.current_page
    
    def cleanup(self):
        """Clean up resources"""
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None


class PartitionTypeEditWidget(QWidget):
    """Widget for editing a single partition type"""
    
    saved = Signal()
    cancelled = Signal()
    
    def __init__(self, partition_type=None, parent=None):
        super().__init__(parent)
        self.partition_type = partition_type
        self.init_ui()
        
        if partition_type:
            self.load_data()
    
    def init_ui(self):
        layout = QFormLayout()
        
        # Assembly ID
        self.assembly_id_edit = QLineEdit()
        self.assembly_id_edit.setPlaceholderText("e.g., K11, P3")
        layout.addRow("Assembly ID:", self.assembly_id_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("e.g., 5/8\" GWB both sides, 3-5/8\" metal studs")
        layout.addRow("Description:", self.description_edit)
        
        # STC Rating
        self.stc_spin = QSpinBox()
        self.stc_spin.setRange(0, 100)
        self.stc_spin.setValue(45)
        self.stc_spin.setSuffix(" STC")
        layout.addRow("STC Rating:", self.stc_spin)
        
        # Source document
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("e.g., A6.1, Partition Schedule")
        layout.addRow("Source Document:", self.source_edit)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        self.notes_edit.setPlaceholderText("Additional notes...")
        layout.addRow("Notes:", self.notes_edit)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addRow("", btn_layout)
        
        self.setLayout(layout)
    
    def load_data(self):
        """Load data from partition type"""
        if self.partition_type:
            self.assembly_id_edit.setText(self.partition_type.assembly_id or "")
            self.description_edit.setPlainText(self.partition_type.description or "")
            self.stc_spin.setValue(self.partition_type.stc_rating or 45)
            self.source_edit.setText(self.partition_type.source_document or "")
            self.notes_edit.setPlainText(self.partition_type.notes or "")
    
    def get_data(self):
        """Get edited data as dictionary"""
        return {
            'assembly_id': self.assembly_id_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'stc_rating': self.stc_spin.value(),
            'source_document': self.source_edit.text().strip(),
            'notes': self.notes_edit.toPlainText().strip(),
        }
    
    def validate(self):
        """Validate input"""
        if not self.assembly_id_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Assembly ID is required.")
            return False
        return True
    
    def save(self):
        if self.validate():
            self.saved.emit()
    
    def cancel(self):
        self.cancelled.emit()


class PartitionTypesDialog(QDialog):
    """Main dialog for managing partition types library"""
    
    # Signal emitted when partition types change
    partition_types_changed = Signal()
    
    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.current_edit_widget = None
        
        self.setWindowTitle("Partition Types Library")
        self.setModal(False)
        self.setWindowFlags(Qt.WindowType.Window)
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: PDF Preview
        pdf_group = QGroupBox("Reference PDF")
        pdf_layout = QVBoxLayout()
        
        # PDF import controls
        pdf_controls = QHBoxLayout()
        
        self.import_pdf_btn = QPushButton("📄 Import PDF")
        self.import_pdf_btn.clicked.connect(self.import_pdf)
        pdf_controls.addWidget(self.import_pdf_btn)
        
        self.pdf_name_label = QLabel("No PDF loaded")
        self.pdf_name_label.setStyleSheet("color: #888; font-style: italic;")
        pdf_controls.addWidget(self.pdf_name_label, 1)
        
        self.remove_pdf_btn = QPushButton("🗑️")
        self.remove_pdf_btn.setMaximumWidth(30)
        self.remove_pdf_btn.setToolTip("Remove PDF")
        self.remove_pdf_btn.clicked.connect(self.remove_pdf)
        self.remove_pdf_btn.setEnabled(False)
        pdf_controls.addWidget(self.remove_pdf_btn)
        
        pdf_layout.addLayout(pdf_controls)
        
        # PDF preview widget
        self.pdf_preview = PDFPreviewWidget()
        pdf_layout.addWidget(self.pdf_preview, 1)
        
        pdf_group.setLayout(pdf_layout)
        splitter.addWidget(pdf_group)
        
        # Right side: Partition types list and editor
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Partition types table
        types_group = QGroupBox("Partition Types")
        types_layout = QVBoxLayout()
        
        self.types_table = QTableWidget()
        self.types_table.setColumnCount(4)
        self.types_table.setHorizontalHeaderLabels(["Assembly ID", "Description", "STC", "Source"])
        self.types_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.types_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.types_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.types_table.itemDoubleClicked.connect(self.edit_partition_type)
        
        # Configure columns
        header = self.types_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        
        self.types_table.setColumnWidth(0, 100)
        self.types_table.setColumnWidth(2, 60)
        self.types_table.setColumnWidth(3, 120)
        
        types_layout.addWidget(self.types_table)
        
        # Table buttons
        table_btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add")
        self.add_btn.clicked.connect(self.add_partition_type)
        table_btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_partition_type)
        self.edit_btn.setEnabled(False)
        table_btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_partition_type)
        self.delete_btn.setEnabled(False)
        table_btn_layout.addWidget(self.delete_btn)
        
        table_btn_layout.addStretch()
        
        types_layout.addLayout(table_btn_layout)
        types_group.setLayout(types_layout)
        right_layout.addWidget(types_group, 1)
        
        # Editor frame (shown when adding/editing)
        self.editor_frame = QFrame()
        self.editor_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.editor_frame.setVisible(False)
        editor_layout = QVBoxLayout()
        
        self.editor_title = QLabel("Edit Partition Type")
        self.editor_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        editor_layout.addWidget(self.editor_title)
        
        self.editor_placeholder = QVBoxLayout()
        editor_layout.addLayout(self.editor_placeholder)
        
        self.editor_frame.setLayout(editor_layout)
        right_layout.addWidget(self.editor_frame)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Set splitter proportions
        splitter.setSizes([500, 700])
        
        layout.addWidget(splitter, 1)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_data(self):
        """Load partition types and reference PDF from database"""
        try:
            with get_hvac_session() as session:
                # Load partition types
                partition_types = session.query(PartitionType).filter(
                    PartitionType.project_id == self.project_id
                ).order_by(PartitionType.assembly_id).all()
                
                self.types_table.setRowCount(len(partition_types))
                
                for row, pt in enumerate(partition_types):
                    # Store the ID in the first column item
                    id_item = QTableWidgetItem(pt.assembly_id or "")
                    id_item.setData(Qt.ItemDataRole.UserRole, pt.id)
                    self.types_table.setItem(row, 0, id_item)
                    
                    desc_item = QTableWidgetItem(pt.description or "")
                    self.types_table.setItem(row, 1, desc_item)
                    
                    stc_item = QTableWidgetItem(str(pt.stc_rating) if pt.stc_rating else "")
                    self.types_table.setItem(row, 2, stc_item)
                    
                    source_item = QTableWidgetItem(pt.source_document or "")
                    self.types_table.setItem(row, 3, source_item)
                
                # Load reference PDF document
                pdf_doc = session.query(PartitionScheduleDocument).filter(
                    PartitionScheduleDocument.project_id == self.project_id
                ).first()
                
                if pdf_doc and pdf_doc.has_valid_file():
                    pdf_path = pdf_doc.get_display_path()
                    self.pdf_name_label.setText(pdf_doc.name)
                    self.pdf_name_label.setStyleSheet("color: #90CAF9;")
                    self.remove_pdf_btn.setEnabled(True)
                    self.pdf_preview.load_pdf(pdf_path, pdf_doc.page_number - 1)
                else:
                    self.pdf_name_label.setText("No PDF loaded")
                    self.pdf_name_label.setStyleSheet("color: #888; font-style: italic;")
                    self.remove_pdf_btn.setEnabled(False)
                    
        except Exception as e:
            print(f"Error loading partition data: {e}")
            QMessageBox.warning(self, "Load Error", f"Failed to load partition data:\n{e}")
    
    def on_selection_changed(self):
        """Handle table selection change"""
        has_selection = bool(self.types_table.selectedItems())
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def get_selected_partition_id(self):
        """Get the ID of the currently selected partition type"""
        selected_rows = self.types_table.selectedItems()
        if selected_rows:
            row = self.types_table.currentRow()
            id_item = self.types_table.item(row, 0)
            if id_item:
                return id_item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def add_partition_type(self):
        """Show editor to add new partition type"""
        self.show_editor(None)
    
    def edit_partition_type(self):
        """Edit selected partition type"""
        partition_id = self.get_selected_partition_id()
        if partition_id:
            try:
                with get_hvac_session() as session:
                    partition_type = session.query(PartitionType).filter(
                        PartitionType.id == partition_id
                    ).first()
                    if partition_type:
                        self.show_editor(partition_type)
            except Exception as e:
                print(f"Error loading partition type: {e}")
    
    def show_editor(self, partition_type):
        """Show the editor widget"""
        # Clear existing editor
        if self.current_edit_widget:
            self.editor_placeholder.removeWidget(self.current_edit_widget)
            self.current_edit_widget.deleteLater()
        
        # Create new editor
        self.current_edit_widget = PartitionTypeEditWidget(partition_type)
        self.current_edit_widget.saved.connect(lambda: self.save_partition_type(partition_type))
        self.current_edit_widget.cancelled.connect(self.hide_editor)
        
        self.editor_placeholder.addWidget(self.current_edit_widget)
        
        self.editor_title.setText("Add Partition Type" if partition_type is None else "Edit Partition Type")
        self.editor_frame.setVisible(True)
    
    def hide_editor(self):
        """Hide the editor widget"""
        self.editor_frame.setVisible(False)
        if self.current_edit_widget:
            self.editor_placeholder.removeWidget(self.current_edit_widget)
            self.current_edit_widget.deleteLater()
            self.current_edit_widget = None
    
    def save_partition_type(self, existing_partition_type):
        """Save the partition type"""
        if not self.current_edit_widget:
            return
        
        data = self.current_edit_widget.get_data()
        
        try:
            with get_hvac_session() as session:
                if existing_partition_type:
                    # Update existing
                    pt = session.query(PartitionType).filter(
                        PartitionType.id == existing_partition_type.id
                    ).first()
                    if pt:
                        pt.assembly_id = data['assembly_id']
                        pt.description = data['description']
                        pt.stc_rating = data['stc_rating']
                        pt.source_document = data['source_document']
                        pt.notes = data['notes']
                else:
                    # Create new
                    pt = PartitionType(
                        project_id=self.project_id,
                        assembly_id=data['assembly_id'],
                        description=data['description'],
                        stc_rating=data['stc_rating'],
                        source_document=data['source_document'],
                        notes=data['notes']
                    )
                    session.add(pt)
            
            self.hide_editor()
            self.load_data()
            self.partition_types_changed.emit()
            
        except Exception as e:
            print(f"Error saving partition type: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save partition type:\n{e}")
    
    def delete_partition_type(self):
        """Delete selected partition type"""
        partition_id = self.get_selected_partition_id()
        if not partition_id:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this partition type?\n\n"
            "This will also remove it from any spaces where it's assigned.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with get_hvac_session() as session:
                    pt = session.query(PartitionType).filter(
                        PartitionType.id == partition_id
                    ).first()
                    if pt:
                        session.delete(pt)
                
                self.load_data()
                self.partition_types_changed.emit()
                
            except Exception as e:
                print(f"Error deleting partition type: {e}")
                QMessageBox.critical(self, "Delete Error", f"Failed to delete partition type:\n{e}")
    
    def import_pdf(self):
        """Import a reference PDF document"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Partition Schedule PDF",
            "", "PDF Files (*.pdf);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with get_hvac_session() as session:
                # Remove existing PDF reference
                existing = session.query(PartitionScheduleDocument).filter(
                    PartitionScheduleDocument.project_id == self.project_id
                ).first()
                if existing:
                    session.delete(existing)
                
                # Create new PDF reference
                pdf_name = os.path.basename(file_path)
                pdf_doc = PartitionScheduleDocument(
                    project_id=self.project_id,
                    name=pdf_name,
                    file_path=file_path,
                    page_number=1
                )
                session.add(pdf_doc)
            
            self.load_data()
            
        except Exception as e:
            print(f"Error importing PDF: {e}")
            QMessageBox.critical(self, "Import Error", f"Failed to import PDF:\n{e}")
    
    def remove_pdf(self):
        """Remove the reference PDF"""
        reply = QMessageBox.question(
            self, "Confirm Remove",
            "Remove the reference PDF from this project?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with get_hvac_session() as session:
                    existing = session.query(PartitionScheduleDocument).filter(
                        PartitionScheduleDocument.project_id == self.project_id
                    ).first()
                    if existing:
                        session.delete(existing)
                
                self.load_data()
                
            except Exception as e:
                print(f"Error removing PDF: {e}")
                QMessageBox.critical(self, "Remove Error", f"Failed to remove PDF:\n{e}")
    
    def closeEvent(self, event):
        """Clean up resources when dialog closes"""
        self.pdf_preview.cleanup()
        super().closeEvent(event)

