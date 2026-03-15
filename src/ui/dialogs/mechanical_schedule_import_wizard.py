"""
Mechanical Schedule Import Wizard
----------------------------------
Multi-step wizard for importing mechanical schedules from images or PDFs
with table detection, OCR, preview, validation, and error correction.

Steps:
1. Load File (PDF/Image)
2. Auto-Detect Tables (optional)
3. Select Region
4. Extract Data (OCR)
5. Preview & Validate
6. Confirm Import
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QFileDialog, QMessageBox,
    QProgressBar, QGroupBox, QRadioButton, QCheckBox,
    QTableWidget, QTableWidgetItem, QSplitter, QTextEdit,
    QSpinBox, QComboBox, QLineEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor


class WizardStep(Enum):
    """Wizard step enumeration"""
    LOAD_FILE = 1
    DETECT_TABLES = 2
    SELECT_REGION = 3
    EXTRACT_DATA = 4
    PREVIEW_VALIDATE = 5
    CONFIRM_IMPORT = 6


@dataclass
class TableRegion:
    """Detected or selected table region"""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    label: str = "Table"
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class ExtractedRow:
    """Single row of extracted data"""
    row_id: int
    cells: List[str]
    include: bool = True
    validation_issues: List[str] = None
    
    def __post_init__(self):
        if self.validation_issues is None:
            self.validation_issues = []


@dataclass
class ColumnMapping:
    """Mapping of table columns to mechanical unit fields"""
    name_col: Optional[int] = None
    type_col: Optional[int] = None
    inlet_start_col: Optional[int] = None
    radiated_start_col: Optional[int] = None
    outlet_start_col: Optional[int] = None


class MechanicalScheduleImportWizard(QDialog):
    """
    Multi-step wizard for importing mechanical schedules with validation
    """
    
    # Signal emitted when import completes successfully
    import_completed = Signal(int)  # number of units imported
    
    def __init__(self, parent=None, project_id: Optional[int] = None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("Mechanical Schedule Import Wizard")
        self.setModal(True)
        self.resize(1200, 800)
        
        # State variables
        self.current_step = WizardStep.LOAD_FILE
        self.loaded_file_path: Optional[str] = None
        self.loaded_pixmap: Optional[QPixmap] = None
        self.current_page: int = 0
        self.total_pages: int = 1
        self.detected_regions: List[TableRegion] = []
        self.selected_region: Optional[TableRegion] = None
        self.extracted_rows: List[ExtractedRow] = []
        self.column_mapping: ColumnMapping = ColumnMapping()
        
        self._build_ui()
        self._update_navigation()
    
    def _build_ui(self):
        """Build the wizard UI"""
        layout = QVBoxLayout()
        
        # Title and step indicator
        self.title_label = QLabel("Step 1 of 6: Load File")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(self.title_label)
        
        # Stacked widget for different steps
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self._create_load_file_page())
        self.stacked_widget.addWidget(self._create_detect_tables_page())
        self.stacked_widget.addWidget(self._create_select_region_page())
        self.stacked_widget.addWidget(self._create_extract_data_page())
        self.stacked_widget.addWidget(self._create_preview_validate_page())
        self.stacked_widget.addWidget(self._create_confirm_import_page())
        layout.addWidget(self.stacked_widget, 1)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("< Back")
        self.back_btn.clicked.connect(self._on_back)
        self.next_btn = QPushButton("Next >")
        self.next_btn.clicked.connect(self._on_next)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        nav_layout.addWidget(self.back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.cancel_btn)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    # ========== Step 1: Load File ==========
    
    def _create_load_file_page(self) -> QWidget:
        """Create the file loading page"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Select an image or PDF file containing a mechanical schedule table.\n"
            "Supported formats: PDF, PNG, JPG, JPEG, TIFF"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        
        file_path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_file)
        file_path_layout.addWidget(QLabel("File:"))
        file_path_layout.addWidget(self.file_path_edit, 1)
        file_path_layout.addWidget(browse_btn)
        file_layout.addLayout(file_path_layout)
        
        # Page selector (for PDFs)
        self.page_selector_widget = QWidget()
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("Page:"))
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(self._on_page_changed)
        page_layout.addWidget(self.page_spin)
        self.page_total_label = QLabel("of 1")
        page_layout.addWidget(self.page_total_label)
        page_layout.addStretch()
        self.page_selector_widget.setLayout(page_layout)
        self.page_selector_widget.setVisible(False)
        file_layout.addWidget(self.page_selector_widget)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        self.file_preview_label = QLabel("No file loaded")
        self.file_preview_label.setAlignment(Qt.AlignCenter)
        self.file_preview_label.setMinimumSize(400, 300)
        self.file_preview_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        preview_layout.addWidget(self.file_preview_label)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group, 1)
        
        widget.setLayout(layout)
        return widget
    
    def _on_browse_file(self):
        """Handle file browse button"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Mechanical Schedule File",
            "",
            "All Supported (*.pdf *.png *.jpg *.jpeg *.tif *.tiff);;PDF Files (*.pdf);;Images (*.png *.jpg *.jpeg *.tif *.tiff)"
        )
        if file_path:
            self._load_file(file_path)
    
    def _load_file(self, file_path: str):
        """Load and preview a file"""
        self.loaded_file_path = file_path
        self.file_path_edit.setText(os.path.basename(file_path))
        
        # Determine file type
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            self._load_pdf(file_path)
        else:
            self._load_image(file_path)
        
        self._update_navigation()
    
    def _load_pdf(self, pdf_path: str):
        """Load PDF and render first page"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            self.total_pages = len(doc)
            self.current_page = 0
            
            # Update page selector
            self.page_spin.setMaximum(self.total_pages)
            self.page_spin.setValue(1)
            self.page_total_label.setText(f"of {self.total_pages}")
            self.page_selector_widget.setVisible(self.total_pages > 1)
            
            # Render first page
            self._render_pdf_page(doc, 0)
            doc.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load PDF:\n{e}")
    
    def _render_pdf_page(self, doc, page_num: int):
        """Render a specific PDF page"""
        import fitz
        
        page = doc[page_num]
        zoom = 2.0  # 144 DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert to QPixmap
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.loaded_pixmap = QPixmap.fromImage(img)
        self._update_preview()
    
    def _load_image(self, image_path: str):
        """Load image file"""
        try:
            self.loaded_pixmap = QPixmap(image_path)
            if self.loaded_pixmap.isNull():
                raise ValueError("Invalid image file")
            
            self.total_pages = 1
            self.current_page = 0
            self.page_selector_widget.setVisible(False)
            self._update_preview()
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load image:\n{e}")
    
    def _update_preview(self):
        """Update the preview label with current pixmap"""
        if self.loaded_pixmap:
            scaled = self.loaded_pixmap.scaled(
                self.file_preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.file_preview_label.setPixmap(scaled)
        else:
            self.file_preview_label.setText("No file loaded")
    
    def _on_page_changed(self, page_num: int):
        """Handle page selection change"""
        if not self.loaded_file_path or not self.loaded_file_path.endswith('.pdf'):
            return
        
        try:
            import fitz
            doc = fitz.open(self.loaded_file_path)
            self.current_page = page_num - 1
            self._render_pdf_page(doc, self.current_page)
            doc.close()
        except Exception as e:
            QMessageBox.warning(self, "Page Load", f"Failed to load page:\n{e}")
    
    # ========== Step 2: Detect Tables ==========
    
    def _create_detect_tables_page(self) -> QWidget:
        """Create the table detection page"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        instructions = QLabel(
            "Automatically detect tables in the document, or proceed to manual selection."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Detection options
        options_group = QGroupBox("Detection Options")
        options_layout = QVBoxLayout()
        
        self.auto_detect_radio = QRadioButton("Auto-detect tables (recommended)")
        self.auto_detect_radio.setChecked(True)
        self.manual_select_radio = QRadioButton("Skip auto-detection (manual selection only)")
        
        options_layout.addWidget(self.auto_detect_radio)
        options_layout.addWidget(self.manual_select_radio)
        
        detect_btn = QPushButton("Run Detection")
        detect_btn.clicked.connect(self._on_run_detection)
        options_layout.addWidget(detect_btn)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Detection results
        results_group = QGroupBox("Detection Results")
        results_layout = QVBoxLayout()
        self.detection_results_text = QTextEdit()
        self.detection_results_text.setReadOnly(True)
        self.detection_results_text.setMaximumHeight(150)
        self.detection_results_text.setPlaceholderText("No detection run yet. Click 'Run Detection' above.")
        results_layout.addWidget(self.detection_results_text)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Preview with detections
        preview_group = QGroupBox("Preview with Detected Regions")
        preview_layout = QVBoxLayout()
        self.detection_preview_label = QLabel("Run detection to see results")
        self.detection_preview_label.setAlignment(Qt.AlignCenter)
        self.detection_preview_label.setMinimumSize(400, 300)
        self.detection_preview_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        preview_layout.addWidget(self.detection_preview_label)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group, 1)
        
        widget.setLayout(layout)
        return widget
    
    def _on_run_detection(self):
        """Run table detection on current image"""
        if not self.loaded_pixmap:
            QMessageBox.information(self, "Detection", "Please load a file first.")
            return
        
        # Placeholder for actual detection logic
        # In full implementation, this would call table detection model
        self.detection_results_text.setPlainText(
            "Table detection not yet implemented.\n"
            "This will use Table Transformer model to detect table regions.\n"
            "For now, proceed to manual selection."
        )
        
        # Mock detected region (for testing)
        # self.detected_regions = [
        #     TableRegion(100, 100, 600, 400, confidence=0.87, label="Mechanical Schedule")
        # ]
        
        self._draw_detection_preview()
    
    def _draw_detection_preview(self):
        """Draw detected regions on preview"""
        if not self.loaded_pixmap:
            return
        
        if not self.detected_regions:
            scaled = self.loaded_pixmap.scaled(
                self.detection_preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.detection_preview_label.setPixmap(scaled)
            return
        
        # Draw bounding boxes on pixmap
        pixmap_copy = self.loaded_pixmap.copy()
        painter = QPainter(pixmap_copy)
        pen = QPen(QColor(0, 255, 0), 3)
        painter.setPen(pen)
        
        for region in self.detected_regions:
            painter.drawRect(region.x, region.y, region.width, region.height)
        
        painter.end()
        
        scaled = pixmap_copy.scaled(
            self.detection_preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.detection_preview_label.setPixmap(scaled)
    
    # ========== Step 3: Select Region ==========
    
    def _create_select_region_page(self) -> QWidget:
        """Create the region selection page"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        instructions = QLabel(
            "Draw a rectangle around the table to import, or select a detected region."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Import region selector widget
        from ui.widgets.region_selector_widget import RegionSelectorWidget
        
        self.region_selector = RegionSelectorWidget()
        self.region_selector.regions_selected.connect(self._on_regions_selected)
        layout.addWidget(self.region_selector, 1)
        
        widget.setLayout(layout)
        return widget
    
    def _on_regions_selected(self, regions: List):
        """Handle region selection changes"""
        if regions:
            self.selected_region = regions[0]  # Use first selection for now
    
    # ========== Step 4: Extract Data ==========
    
    def _create_extract_data_page(self) -> QWidget:
        """Create the data extraction page"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        instructions = QLabel(
            "Extracting table data using OCR..."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Progress bar
        self.extraction_progress = QProgressBar()
        self.extraction_progress.setRange(0, 100)
        layout.addWidget(self.extraction_progress)
        
        # Status text
        self.extraction_status = QTextEdit()
        self.extraction_status.setReadOnly(True)
        self.extraction_status.setMaximumHeight(200)
        layout.addWidget(self.extraction_status)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    # ========== Step 5: Preview & Validate ==========
    
    def _create_preview_validate_page(self) -> QWidget:
        """Create the preview and validation page"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        instructions = QLabel(
            "Review extracted data, correct any errors, and map columns to unit fields."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Import table preview widget
        from ui.widgets.table_preview_widget import TablePreviewWidget
        
        self.table_preview = TablePreviewWidget()
        self.table_preview.data_modified.connect(self._on_preview_data_modified)
        self.table_preview.validation_changed.connect(self._on_validation_changed)
        layout.addWidget(self.table_preview, 1)
        
        # Column mapping button
        mapping_btn = QPushButton("Configure Column Mapping...")
        mapping_btn.clicked.connect(self._on_configure_mapping)
        layout.addWidget(mapping_btn)
        
        widget.setLayout(layout)
        return widget
    
    def _on_preview_data_modified(self):
        """Handle preview data modification"""
        # Update summary when data changes
        pass
    
    def _on_validation_changed(self, issues: List):
        """Handle validation changes"""
        # Store validation issues
        self.validation_issues = issues
    
    def _on_configure_mapping(self):
        """Open column mapping dialog"""
        if not self.extracted_rows:
            QMessageBox.information(self, "Column Mapping", "No data extracted yet. Please complete data extraction first.")
            return
        
        from ui.widgets.column_mapper_dialog import ColumnMapperDialog
        
        # Extract headers and sample rows
        headers = self.table_preview.headers if hasattr(self, 'table_preview') else []
        sample_rows = [row.cells for row in self.extracted_rows[:5]] if self.extracted_rows else []
        
        dialog = ColumnMapperDialog(headers, sample_rows, self)
        dialog.mapping_confirmed.connect(self._on_mapping_confirmed)
        dialog.exec()
    
    def _on_mapping_confirmed(self, mapping: Dict):
        """Handle column mapping confirmation"""
        self.column_mapping = mapping
        QMessageBox.information(self, "Mapping Saved", "Column mapping has been updated.")
    
    # ========== Step 6: Confirm Import ==========
    
    def _create_confirm_import_page(self) -> QWidget:
        """Create the import confirmation page"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Summary
        summary_group = QGroupBox("Import Summary")
        summary_layout = QVBoxLayout()
        self.summary_label = QLabel("Ready to import 0 units")
        self.summary_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        summary_layout.addWidget(self.summary_label)
        
        self.summary_details = QTextEdit()
        self.summary_details.setReadOnly(True)
        self.summary_details.setMaximumHeight(150)
        summary_layout.addWidget(self.summary_details)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Options
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout()
        
        self.backup_check = QCheckBox("Create backup before import")
        self.backup_check.setChecked(True)
        options_layout.addWidget(self.backup_check)
        
        self.skip_duplicates_check = QCheckBox("Skip duplicate unit names")
        self.skip_duplicates_check.setChecked(True)
        options_layout.addWidget(self.skip_duplicates_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Final import button
        import_btn = QPushButton("Import to Database")
        import_btn.setStyleSheet("font-size: 14px; padding: 10px; background-color: #4CAF50; color: white;")
        import_btn.clicked.connect(self._on_final_import)
        layout.addWidget(import_btn)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _on_final_import(self):
        """Execute the final import to database.

        Note: This wizard is part of the mechanical schedule PDF import feature
        which is under active development. The import logic will create
        MechanicalUnit records from the validated OCR data.
        """
        QMessageBox.information(
            self,
            "Import Complete",
            "Import functionality will be implemented to save validated units to database."
        )
        self.accept()
    
    # ========== Navigation ==========
    
    def _on_back(self):
        """Handle back button"""
        current_idx = list(WizardStep).index(self.current_step)
        if current_idx > 0:
            self.current_step = list(WizardStep)[current_idx - 1]
            self.stacked_widget.setCurrentIndex(current_idx - 1)
            self._update_navigation()
    
    def _on_next(self):
        """Handle next button"""
        # Validate current step before proceeding
        if not self._validate_current_step():
            return
        
        current_idx = list(WizardStep).index(self.current_step)
        if current_idx < len(WizardStep) - 1:
            self.current_step = list(WizardStep)[current_idx + 1]
            self.stacked_widget.setCurrentIndex(current_idx + 1)
            self._update_navigation()
            
            # Trigger step-specific actions
            self._on_step_entered()
    
    def _validate_current_step(self) -> bool:
        """Validate current step before moving forward"""
        if self.current_step == WizardStep.LOAD_FILE:
            if not self.loaded_file_path or not self.loaded_pixmap:
                QMessageBox.information(self, "Validation", "Please load a file first.")
                return False
        
        # Add more validation as needed
        return True
    
    def _on_step_entered(self):
        """Called when entering a new step"""
        if self.current_step == WizardStep.EXTRACT_DATA:
            # Trigger extraction
            QTimer.singleShot(100, self._run_extraction)
    
    def _run_extraction(self):
        """Run OCR extraction on selected region"""
        # Placeholder for actual extraction
        self.extraction_status.setPlainText(
            "OCR extraction not yet implemented.\n"
            "This will:\n"
            "1. Crop selected region from image\n"
            "2. Run enhanced OCR (PaddleOCR/Tesseract)\n"
            "3. Parse table structure\n"
            "4. Extract rows and cells\n"
            "5. Compute confidence scores"
        )
        self.extraction_progress.setValue(100)
    
    def _update_navigation(self):
        """Update navigation buttons and title"""
        step_names = {
            WizardStep.LOAD_FILE: "Load File",
            WizardStep.DETECT_TABLES: "Detect Tables",
            WizardStep.SELECT_REGION: "Select Region",
            WizardStep.EXTRACT_DATA: "Extract Data",
            WizardStep.PREVIEW_VALIDATE: "Preview & Validate",
            WizardStep.CONFIRM_IMPORT: "Confirm Import"
        }
        
        current_idx = list(WizardStep).index(self.current_step)
        self.title_label.setText(
            f"Step {current_idx + 1} of {len(WizardStep)}: {step_names[self.current_step]}"
        )
        
        # Update button states
        self.back_btn.setEnabled(current_idx > 0)
        
        if current_idx == len(WizardStep) - 1:
            self.next_btn.setVisible(False)
        else:
            self.next_btn.setVisible(True)
            self.next_btn.setText("Next >")
