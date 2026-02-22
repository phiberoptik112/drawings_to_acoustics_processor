"""
OCR Settings Dialog
------------------
Dialog for configuring OCR and import preferences.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QRadioButton, QCheckBox,
    QSpinBox, QLineEdit, QComboBox, QFormLayout,
    QMessageBox
)
from PySide6.QtCore import Qt

from utils.ocr_settings import OCRSettings, OCRSettingsManager


class OCRSettingsDialog(QDialog):
    """
    Dialog for configuring OCR and table import settings
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OCR & Import Settings")
        self.setModal(True)
        self.resize(600, 700)
        
        self.settings_manager = OCRSettingsManager.get_instance()
        self.settings = self.settings_manager.get_settings()
        
        self._build_ui()
        self._load_current_settings()
    
    def _build_ui(self):
        """Build the dialog UI"""
        layout = QVBoxLayout()
        
        # OCR Engine Selection
        engine_group = QGroupBox("OCR Engine")
        engine_layout = QVBoxLayout()
        
        self.auto_radio = QRadioButton("Auto (Try PaddleOCR → EasyOCR → Tesseract)")
        self.auto_radio.setToolTip("Automatically use the best available OCR engine")
        engine_layout.addWidget(self.auto_radio)
        
        self.paddle_radio = QRadioButton("PaddleOCR (Recommended - Best accuracy)")
        self.paddle_radio.setToolTip("Use PaddleOCR for best accuracy on complex tables")
        engine_layout.addWidget(self.paddle_radio)
        
        self.easy_radio = QRadioButton("EasyOCR (Good accuracy, lightweight)")
        self.easy_radio.setToolTip("Use EasyOCR for good accuracy with lower resource usage")
        engine_layout.addWidget(self.easy_radio)
        
        self.tesseract_radio = QRadioButton("Tesseract (Basic - Fastest)")
        self.tesseract_radio.setToolTip("Use Tesseract OCR for basic recognition")
        engine_layout.addWidget(self.tesseract_radio)
        
        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)
        
        # Table Detection
        detection_group = QGroupBox("Table Detection")
        detection_layout = QVBoxLayout()
        
        self.auto_detect_check = QCheckBox("Enable automatic table detection")
        self.auto_detect_check.setToolTip("Use AI model to automatically detect table regions")
        detection_layout.addWidget(self.auto_detect_check)
        
        self.show_confidence_check = QCheckBox("Show confidence scores")
        self.show_confidence_check.setToolTip("Display OCR confidence scores for each cell")
        detection_layout.addWidget(self.show_confidence_check)
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Minimum confidence threshold:"))
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(0, 100)
        self.confidence_spin.setSuffix("%")
        self.confidence_spin.setToolTip("Minimum confidence for auto-detected tables")
        threshold_layout.addWidget(self.confidence_spin)
        threshold_layout.addStretch()
        detection_layout.addLayout(threshold_layout)
        
        detection_group.setLayout(detection_layout)
        layout.addWidget(detection_group)
        
        # Validation
        validation_group = QGroupBox("Validation")
        validation_layout = QVBoxLayout()
        
        self.auto_fix_check = QCheckBox("Auto-fix common OCR errors")
        self.auto_fix_check.setToolTip("Automatically fix common OCR mistakes (O→0, l→1)")
        validation_layout.addWidget(self.auto_fix_check)
        
        self.highlight_missing_check = QCheckBox("Highlight missing frequency values")
        self.highlight_missing_check.setToolTip("Highlight cells with missing data in preview")
        validation_layout.addWidget(self.highlight_missing_check)
        
        self.warn_duplicates_check = QCheckBox("Warn on duplicate unit names")
        self.warn_duplicates_check.setToolTip("Show warning when duplicate unit names are detected")
        validation_layout.addWidget(self.warn_duplicates_check)
        
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        # Cloud OCR (Optional)
        cloud_group = QGroupBox("Cloud OCR (Optional)")
        cloud_layout = QVBoxLayout()
        
        self.cloud_enable_check = QCheckBox("Enable cloud OCR service")
        self.cloud_enable_check.setToolTip("Use cloud API for better accuracy on challenging documents")
        self.cloud_enable_check.toggled.connect(self._toggle_cloud_settings)
        cloud_layout.addWidget(self.cloud_enable_check)
        
        cloud_form = QFormLayout()
        
        self.cloud_service_combo = QComboBox()
        self.cloud_service_combo.addItems(["Google Vision", "AWS Textract", "Azure Document Intelligence"])
        cloud_form.addRow("Service:", self.cloud_service_combo)
        
        self.cloud_api_key_edit = QLineEdit()
        self.cloud_api_key_edit.setEchoMode(QLineEdit.Password)
        self.cloud_api_key_edit.setPlaceholderText("Enter API key")
        cloud_form.addRow("API Key:", self.cloud_api_key_edit)
        
        cloud_layout.addLayout(cloud_form)
        
        self.cloud_settings_widget = QWidget()
        self.cloud_settings_widget.setLayout(cloud_form)
        self.cloud_settings_widget.setEnabled(False)
        cloud_layout.addWidget(self.cloud_settings_widget)
        
        cloud_group.setLayout(cloud_layout)
        layout.addWidget(cloud_group)
        
        # Import Options
        import_group = QGroupBox("Import Options")
        import_layout = QVBoxLayout()
        
        self.backup_check = QCheckBox("Create backup before import")
        self.backup_check.setToolTip("Create database backup before importing new units")
        import_layout.addWidget(self.backup_check)
        
        self.skip_duplicates_check = QCheckBox("Skip duplicate unit names")
        self.skip_duplicates_check.setToolTip("Skip units with names that already exist in database")
        import_layout.addWidget(self.skip_duplicates_check)
        
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(reset_btn)
        
        btn_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _load_current_settings(self):
        """Load current settings into UI"""
        # OCR Engine
        engine = self.settings.preferred_engine
        if engine == "auto":
            self.auto_radio.setChecked(True)
        elif engine == "paddle":
            self.paddle_radio.setChecked(True)
        elif engine == "easy":
            self.easy_radio.setChecked(True)
        elif engine == "tesseract":
            self.tesseract_radio.setChecked(True)
        
        # Table Detection
        self.auto_detect_check.setChecked(self.settings.enable_auto_detection)
        self.show_confidence_check.setChecked(self.settings.show_confidence_scores)
        self.confidence_spin.setValue(int(self.settings.detection_confidence_threshold * 100))
        
        # Validation
        self.auto_fix_check.setChecked(self.settings.auto_fix_common_errors)
        self.highlight_missing_check.setChecked(self.settings.highlight_missing_values)
        self.warn_duplicates_check.setChecked(self.settings.warn_on_duplicates)
        
        # Cloud OCR
        self.cloud_enable_check.setChecked(self.settings.enable_cloud_ocr)
        service_map = {"google": 0, "aws": 1, "azure": 2}
        self.cloud_service_combo.setCurrentIndex(service_map.get(self.settings.cloud_service, 0))
        self.cloud_api_key_edit.setText(self.settings.cloud_api_key)
        self._toggle_cloud_settings(self.settings.enable_cloud_ocr)
        
        # Import Options
        self.backup_check.setChecked(self.settings.create_backup_before_import)
        self.skip_duplicates_check.setChecked(self.settings.skip_duplicate_units)
    
    def _toggle_cloud_settings(self, enabled: bool):
        """Enable/disable cloud settings based on checkbox"""
        self.cloud_settings_widget.setEnabled(enabled)
    
    def _save_and_close(self):
        """Save settings and close dialog"""
        # Get OCR engine preference
        if self.auto_radio.isChecked():
            engine = "auto"
        elif self.paddle_radio.isChecked():
            engine = "paddle"
        elif self.easy_radio.isChecked():
            engine = "easy"
        else:
            engine = "tesseract"
        
        # Get cloud service
        service_map = {0: "google", 1: "aws", 2: "azure"}
        cloud_service = service_map[self.cloud_service_combo.currentIndex()]
        
        # Update settings
        self.settings_manager.update_settings(
            preferred_engine=engine,
            enable_auto_detection=self.auto_detect_check.isChecked(),
            detection_confidence_threshold=self.confidence_spin.value() / 100.0,
            show_confidence_scores=self.show_confidence_check.isChecked(),
            auto_fix_common_errors=self.auto_fix_check.isChecked(),
            highlight_missing_values=self.highlight_missing_check.isChecked(),
            warn_on_duplicates=self.warn_duplicates_check.isChecked(),
            enable_cloud_ocr=self.cloud_enable_check.isChecked(),
            cloud_service=cloud_service,
            cloud_api_key=self.cloud_api_key_edit.text(),
            create_backup_before_import=self.backup_check.isChecked(),
            skip_duplicate_units=self.skip_duplicates_check.isChecked()
        )
        
        QMessageBox.information(self, "Settings Saved", "OCR & Import settings have been saved.")
        self.accept()
    
    def _reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all OCR & Import settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_defaults()
            self.settings = self.settings_manager.get_settings()
            self._load_current_settings()
            QMessageBox.information(self, "Reset Complete", "Settings have been reset to defaults.")
