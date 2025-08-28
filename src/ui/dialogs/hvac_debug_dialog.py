"""
HVAC Debug Dialog - Comprehensive debugging information for HVAC paths
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QTreeWidget, QTreeWidgetItem, QTabWidget, QWidget,
    QSplitter, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import json
import os


class HVACDebugDialog(QDialog):
    """Dedicated dialog for HVAC system debugging"""
    
    def __init__(self, parent=None, project_id=None, path_id=None):
        super().__init__(parent)
        self.project_id = project_id
        self.path_id = path_id
        self.debug_data = None
        self.debug_report = None
        
        self.setWindowTitle("HVAC Debug Information")
        self.setMinimumSize(900, 700)
        self.resize(1200, 800)
        
        self.setup_ui()
        self.load_debug_data()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("HVAC Path Debug Information")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        if self.path_id:
            path_label = QLabel(f"Path ID: {self.path_id}")
            header_layout.addWidget(path_label)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_debug_data)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export Debug Data")
        export_btn.clicked.connect(self.export_debug_data)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Main content with tabs
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Tab 1: Debug Report Overview
        self.create_report_tab()
        
        # Tab 2: Path Connectivity
        self.create_connectivity_tab()
        
        # Tab 3: Validation Results
        self.create_validation_tab()
        
        # Tab 4: Raw Debug Data
        self.create_raw_data_tab()
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_report_tab(self):
        """Create the debug report overview tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Issues and recommendations
        splitter = QSplitter(Qt.Vertical)
        
        # Issues tree
        issues_label = QLabel("Issues Detected:")
        issues_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(issues_label)
        
        self.issues_tree = QTreeWidget()
        self.issues_tree.setHeaderLabels(["Type", "Description"])
        splitter.addWidget(self.issues_tree)
        
        # System health
        health_label = QLabel("System Health:")
        health_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(health_label)
        
        self.health_tree = QTreeWidget()
        self.health_tree.setHeaderLabels(["Component", "Status"])
        splitter.addWidget(self.health_tree)
        
        layout.addWidget(splitter)
        self.tab_widget.addTab(tab, "Debug Report")
    
    def create_connectivity_tab(self):
        """Create the path connectivity tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        connectivity_label = QLabel("Segment Connectivity:")
        connectivity_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(connectivity_label)
        
        self.connectivity_tree = QTreeWidget()
        self.connectivity_tree.setHeaderLabels([
            "Position", "Segment ID", "From Component", "To Component", 
            "Length", "Dimensions", "Order"
        ])
        layout.addWidget(self.connectivity_tree)
        
        self.tab_widget.addTab(tab, "Path Connectivity")
    
    def create_validation_tab(self):
        """Create the validation results tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        validation_label = QLabel("Validation Results:")
        validation_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(validation_label)
        
        self.validation_tree = QTreeWidget()
        self.validation_tree.setHeaderLabels(["Type", "Message"])
        layout.addWidget(self.validation_tree)
        
        self.tab_widget.addTab(tab, "Validation")
    
    def create_raw_data_tab(self):
        """Create the raw debug data tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        raw_label = QLabel("Raw Debug Data (JSON):")
        raw_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(raw_label)
        
        self.raw_text = QTextEdit()
        self.raw_text.setFont(QFont("Courier", 9))
        self.raw_text.setReadOnly(True)
        layout.addWidget(self.raw_text)
        
        self.tab_widget.addTab(tab, "Raw Data")
    
    def load_debug_data(self):
        """Load debug data for the path"""
        try:
            if not self.path_id or not self.project_id:
                QMessageBox.warning(self, "Missing Information", 
                                  "Path ID and Project ID are required for debug analysis.")
                return
            
            from src.calculations.hvac_path_calculator import HVACPathCalculator
            
            calculator = HVACPathCalculator(self.project_id)
            self.debug_report = calculator.generate_debug_report(self.path_id)

            # Also try to get enhanced JSON + CSV exports directly from the calculator
            try:
                # Force debug export to generate fresh data (JSON + CSV)
                os.environ['HVAC_DEBUG_EXPORT'] = '1'
                # Running the calculation ensures _debug_export_path_result is invoked
                calculator.calculate_path_noise(self.path_id, debug=True)
            except Exception:
                pass
            finally:
                # Clean up environment
                if 'HVAC_DEBUG_EXPORT' in os.environ:
                    del os.environ['HVAC_DEBUG_EXPORT']
            
            self.populate_debug_displays()
            
        except Exception as e:
            QMessageBox.critical(self, "Debug Load Error", f"Failed to load debug data:\n{str(e)}")
    
    def populate_debug_displays(self):
        """Populate all debug displays with loaded data"""
        if not self.debug_report:
            return
        
        # Populate report tab
        self.populate_report_tab()
        
        # Populate connectivity tab (if we have path data)
        self.populate_connectivity_tab()
        
        # Populate validation tab
        self.populate_validation_tab()
        
        # Populate raw data tab
        self.populate_raw_data_tab()
    
    def populate_report_tab(self):
        """Populate the debug report tab"""
        self.issues_tree.clear()
        self.health_tree.clear()
        
        # Issues
        for issue in self.debug_report.get('issues_detected', []):
            item = QTreeWidgetItem(self.issues_tree)
            item.setText(0, "Issue")
            item.setText(1, str(issue))
        
        for rec in self.debug_report.get('recommendations', []):
            item = QTreeWidgetItem(self.issues_tree)
            item.setText(0, "Recommendation")
            item.setText(1, str(rec))
        
        # System health
        health_data = self.debug_report.get('system_health', {})
        for key, value in health_data.items():
            item = QTreeWidgetItem(self.health_tree)
            item.setText(0, key.replace('_', ' ').title())
            item.setText(1, str(value))
        
        # Expand all items
        self.issues_tree.expandAll()
        self.health_tree.expandAll()
    
    def populate_connectivity_tab(self):
        """Populate the connectivity tab"""
        self.connectivity_tree.clear()
        
        # This would need to be populated with actual segment data
        # For now, show a placeholder
        item = QTreeWidgetItem(self.connectivity_tree)
        item.setText(0, "...")
        item.setText(1, "Connectivity data would be shown here")
        item.setText(2, "when available from path analysis")
    
    def populate_validation_tab(self):
        """Populate the validation tab"""
        self.validation_tree.clear()
        
        validation = self.debug_report.get('validation_summary', {})
        if validation:
            # Summary item
            summary_item = QTreeWidgetItem(self.validation_tree)
            summary_item.setText(0, "Summary")
            summary_item.setText(1, f"Valid: {validation.get('is_valid', 'Unknown')}")
            
            # Counts
            counts_item = QTreeWidgetItem(self.validation_tree)
            counts_item.setText(0, "Counts")
            counts_item.setText(1, f"Errors: {validation.get('error_count', 0)}, "
                                   f"Warnings: {validation.get('warning_count', 0)}, "
                                   f"Info: {validation.get('info_count', 0)}")
        
        self.validation_tree.expandAll()
    
    def populate_raw_data_tab(self):
        """Populate the raw data tab"""
        try:
            json_str = json.dumps(self.debug_report, indent=2, default=str)
            self.raw_text.setPlainText(json_str)
        except Exception as e:
            self.raw_text.setPlainText(f"Error formatting debug data: {e}")
    
    def export_debug_data(self):
        """Export debug data to file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Debug Data", f"hvac_debug_path_{self.path_id}.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(self.debug_report, f, indent=2, default=str)
                
                QMessageBox.information(self, "Export Complete", 
                                      f"Debug data exported to:\n{filename}")
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export debug data:\n{str(e)}")
