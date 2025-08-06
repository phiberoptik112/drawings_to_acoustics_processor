"""
HVAC Path Analysis Dialog - Detailed noise analysis and comparison of HVAC paths
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QListWidget,
                             QListWidgetItem, QSplitter, QTabWidget, QWidget,
                             QProgressDialog)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from models import get_session
from models.hvac import HVACPath, HVACComponent, HVACSegment
from models.space import Space
from calculations.hvac_path_calculator import HVACPathCalculator
from calculations.nc_rating_analyzer import NCRatingAnalyzer


class AnalysisThread(QThread):
    """Background thread for HVAC path analysis"""
    
    analysis_complete = Signal(dict)
    progress_update = Signal(str)
    
    def __init__(self, path_ids, project_id):
        super().__init__()
        self.path_ids = path_ids
        self.project_id = project_id
        self.calculator = HVACPathCalculator()
        
    def run(self):
        try:
            results = {}
            
            for i, path_id in enumerate(self.path_ids):
                self.progress_update.emit(f"Analyzing path {i+1}/{len(self.path_ids)}...")
                
                result = self.calculator.calculate_path_noise(path_id)
                results[path_id] = result
                
            self.analysis_complete.emit(results)
            
        except Exception as e:
            self.analysis_complete.emit({'error': str(e)})


class HVACPathAnalysisDialog(QDialog):
    """Dialog for detailed HVAC path analysis and comparison"""
    
    def __init__(self, parent=None, project_id=None, space_id=None):
        super().__init__(parent)
        self.project_id = project_id
        self.space_id = space_id
        self.analysis_results = {}
        self.selected_paths = []
        
        # Calculators
        self.path_calculator = HVACPathCalculator()
        self.nc_analyzer = NCRatingAnalyzer()
        
        self.init_ui()
        self.load_paths()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("HVAC Path Analysis")
        self.setModal(True)
        self.resize(1000, 800)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("HVAC Path Analysis & Comparison")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Main content in tabs
        tabs = QTabWidget()
        
        # Path Selection tab
        selection_tab = self.create_selection_tab()
        tabs.addTab(selection_tab, "Path Selection")
        
        # Analysis Results tab
        results_tab = self.create_results_tab()
        tabs.addTab(results_tab, "Analysis Results")
        
        # Comparison tab
        comparison_tab = self.create_comparison_tab()
        tabs.addTab(comparison_tab, "Path Comparison")
        
        # Charts tab
        charts_tab = self.create_charts_tab()
        tabs.addTab(charts_tab, "Charts")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Analyze Selected Paths")
        self.analyze_btn.clicked.connect(self.analyze_paths)
        self.analyze_btn.setEnabled(False)
        button_layout.addWidget(self.analyze_btn)
        
        button_layout.addStretch()
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_selection_tab(self):
        """Create the path selection tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Filter options
        filter_group = QGroupBox("Filter Options")
        filter_layout = QHBoxLayout()
        
        # Path type filter
        filter_layout.addWidget(QLabel("Path Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "supply", "return", "exhaust"])
        self.type_filter.currentTextChanged.connect(self.filter_paths)
        filter_layout.addWidget(self.type_filter)
        
        # Space filter
        filter_layout.addWidget(QLabel("Target Space:"))
        self.space_filter = QComboBox()
        self.space_filter.addItems(["All"])
        self.load_spaces_for_filter()
        self.space_filter.currentTextChanged.connect(self.filter_paths)
        filter_layout.addWidget(self.space_filter)
        
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Available paths
        available_group = QGroupBox("Available HVAC Paths")
        available_layout = QVBoxLayout()
        
        self.paths_list = QListWidget()
        self.paths_list.setSelectionMode(QListWidget.MultiSelection)
        self.paths_list.itemSelectionChanged.connect(self.on_path_selection_changed)
        available_layout.addWidget(self.paths_list)
        
        # Selection buttons
        select_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_paths)
        select_layout.addWidget(self.select_all_btn)
        
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        select_layout.addWidget(self.clear_selection_btn)
        
        select_layout.addStretch()
        available_layout.addLayout(select_layout)
        
        available_group.setLayout(available_layout)
        layout.addWidget(available_group)
        
        # Selected paths summary
        summary_group = QGroupBox("Selected Paths")
        summary_layout = QVBoxLayout()
        
        self.selection_summary = QLabel("No paths selected")
        self.selection_summary.setStyleSheet("color: #666; font-style: italic;")
        summary_layout.addWidget(self.selection_summary)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_results_tab(self):
        """Create the analysis results tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Results table
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Path Name", "Type", "Target Space", "Source Noise", 
            "Terminal Noise", "Attenuation", "NC Rating"
        ])
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Detailed results
        detail_group = QGroupBox("Detailed Results")
        detail_layout = QVBoxLayout()
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(200)
        detail_layout.addWidget(self.detail_text)
        
        detail_group.setLayout(detail_layout)
        layout.addWidget(detail_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_comparison_tab(self):
        """Create the path comparison tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Comparison table
        comparison_group = QGroupBox("Path Comparison")
        comparison_layout = QVBoxLayout()
        
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(8)
        self.comparison_table.setHorizontalHeaderLabels([
            "Path", "Components", "Segments", "Total Length", 
            "Source Noise", "Terminal Noise", "Attenuation", "NC Rating"
        ])
        
        # Set column widths
        header = self.comparison_table.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        
        comparison_layout.addWidget(self.comparison_table)
        
        comparison_group.setLayout(comparison_layout)
        layout.addWidget(comparison_group)
        
        # Performance summary
        performance_group = QGroupBox("Performance Summary")
        performance_layout = QVBoxLayout()
        
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setMaximumHeight(150)
        performance_layout.addWidget(self.performance_text)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_charts_tab(self):
        """Create the charts tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Noise comparison chart
        chart_group = QGroupBox("Noise Comparison")
        chart_layout = QVBoxLayout()
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)
        
        # Chart controls
        controls_group = QGroupBox("Chart Controls")
        controls_layout = QHBoxLayout()
        
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Noise Levels", "Attenuation", "NC Ratings"])
        self.chart_type_combo.currentTextChanged.connect(self.update_chart)
        controls_layout.addWidget(QLabel("Chart Type:"))
        controls_layout.addWidget(self.chart_type_combo)
        
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        widget.setLayout(layout)
        return widget
        
    def load_spaces_for_filter(self):
        """Load spaces for the filter dropdown"""
        try:
            session = get_session()
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            
            for space in spaces:
                self.space_filter.addItem(space.name)
            
            session.close()
            
        except Exception as e:
            print(f"Error loading spaces: {e}")
    
    def load_paths(self):
        """Load HVAC paths for the project"""
        try:
            session = get_session()
            
            query = session.query(HVACPath).filter(HVACPath.project_id == self.project_id)
            
            # Apply space filter if specified
            if self.space_id:
                query = query.filter(HVACPath.target_space_id == self.space_id)
            
            paths = query.all()
            
            self.all_paths = paths
            self.update_paths_list()
            
            session.close()
            
        except Exception as e:
            print(f"Error loading paths: {e}")
    
    def update_paths_list(self):
        """Update the paths list with current filter"""
        self.paths_list.clear()
        
        type_filter = self.type_filter.currentText()
        space_filter = self.space_filter.currentText()
        
        for path in self.all_paths:
            # Apply type filter
            if type_filter != "All" and path.path_type != type_filter:
                continue
            
            # Apply space filter
            if space_filter != "All":
                if not path.target_space or path.target_space.name != space_filter:
                    continue
            
            # Create list item
            space_name = path.target_space.name if path.target_space else "None"
            item_text = f"{path.name} ({path.path_type}) → {space_name}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, path)
            self.paths_list.addItem(item)
    
    def filter_paths(self):
        """Filter paths based on current selections"""
        self.update_paths_list()
    
    def on_path_selection_changed(self):
        """Handle path selection change"""
        selected_items = self.paths_list.selectedItems()
        self.selected_paths = [item.data(Qt.UserRole) for item in selected_items]
        
        # Update summary
        if self.selected_paths:
            summary = f"Selected {len(self.selected_paths)} path(s):\n"
            for path in self.selected_paths:
                summary += f"• {path.name} ({path.path_type})\n"
        else:
            summary = "No paths selected"
        
        self.selection_summary.setText(summary)
        
        # Enable/disable analyze button
        self.analyze_btn.setEnabled(len(self.selected_paths) > 0)
    
    def select_all_paths(self):
        """Select all visible paths"""
        for i in range(self.paths_list.count()):
            self.paths_list.item(i).setSelected(True)
    
    def clear_selection(self):
        """Clear all selections"""
        self.paths_list.clearSelection()
    
    def analyze_paths(self):
        """Analyze selected paths"""
        if not self.selected_paths:
            return
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog("Analyzing HVAC paths...", "Cancel", 0, len(self.selected_paths), self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        
        # Start analysis thread
        path_ids = [path.id for path in self.selected_paths]
        self.analysis_thread = AnalysisThread(path_ids, self.project_id)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.progress_update.connect(self.progress_dialog.setLabelText)
        self.analysis_thread.start()
    
    def on_analysis_complete(self, results):
        """Handle completed analysis"""
        self.progress_dialog.close()
        
        if 'error' in results:
            QMessageBox.critical(self, "Analysis Error", f"Error during analysis: {results['error']}")
            return
        
        self.analysis_results = results
        self.display_results()
        self.update_comparison()
        self.update_chart()
        self.export_btn.setEnabled(True)
    
    def display_results(self):
        """Display analysis results in table"""
        self.results_table.setRowCount(0)
        
        for path_id, result in self.analysis_results.items():
            # Find the path object
            path = next((p for p in self.selected_paths if p.id == path_id), None)
            if not path:
                continue
            
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # Path name
            self.results_table.setItem(row, 0, QTableWidgetItem(path.name))
            
            # Path type
            self.results_table.setItem(row, 1, QTableWidgetItem(path.path_type or "unknown"))
            
            # Target space
            space_name = path.target_space.name if path.target_space else "None"
            self.results_table.setItem(row, 2, QTableWidgetItem(space_name))
            
            # Source noise
            source_noise = result.source_noise if result.calculation_valid else 0
            self.results_table.setItem(row, 3, QTableWidgetItem(f"{source_noise:.1f} dB(A)"))
            
            # Terminal noise
            terminal_noise = result.terminal_noise if result.calculation_valid else 0
            self.results_table.setItem(row, 4, QTableWidgetItem(f"{terminal_noise:.1f} dB(A)"))
            
            # Attenuation
            attenuation = result.total_attenuation if result.calculation_valid else 0
            self.results_table.setItem(row, 5, QTableWidgetItem(f"{attenuation:.1f} dB"))
            
            # NC rating
            nc_rating = result.nc_rating if result.calculation_valid else 0
            self.results_table.setItem(row, 6, QTableWidgetItem(f"NC-{nc_rating:.0f}"))
            
            # Color code based on NC rating
            if result.calculation_valid:
                if nc_rating <= 30:
                    color = "#90EE90"  # Light green
                elif nc_rating <= 40:
                    color = "#FFFF99"  # Light yellow
                else:
                    color = "#FFB6C1"  # Light red
                
                for col in range(7):
                    self.results_table.item(row, col).setBackground(Qt.lightGray)
    
    def update_comparison(self):
        """Update the comparison table"""
        self.comparison_table.setRowCount(0)
        
        for path_id, result in self.analysis_results.items():
            path = next((p for p in self.selected_paths if p.id == path_id), None)
            if not path or not result.calculation_valid:
                continue
            
            row = self.comparison_table.rowCount()
            self.comparison_table.insertRow(row)
            
            # Path name
            self.comparison_table.setItem(row, 0, QTableWidgetItem(path.name))
            
            # Component count
            component_count = len(path.segments) + 1 if path.segments else 0
            self.comparison_table.setItem(row, 1, QTableWidgetItem(str(component_count)))
            
            # Segment count
            segment_count = len(path.segments)
            self.comparison_table.setItem(row, 2, QTableWidgetItem(str(segment_count)))
            
            # Total length
            total_length = sum(seg.length for seg in path.segments) if path.segments else 0
            self.comparison_table.setItem(row, 3, QTableWidgetItem(f"{total_length:.1f} ft"))
            
            # Source noise
            self.comparison_table.setItem(row, 4, QTableWidgetItem(f"{result.source_noise:.1f} dB(A)"))
            
            # Terminal noise
            self.comparison_table.setItem(row, 5, QTableWidgetItem(f"{result.terminal_noise:.1f} dB(A)"))
            
            # Attenuation
            self.comparison_table.setItem(row, 6, QTableWidgetItem(f"{result.total_attenuation:.1f} dB"))
            
            # NC rating
            self.comparison_table.setItem(row, 7, QTableWidgetItem(f"NC-{result.nc_rating:.0f}"))
        
        # Update performance summary
        self.update_performance_summary()
    
    def update_performance_summary(self):
        """Update the performance summary"""
        if not self.analysis_results:
            self.performance_text.setHtml("<i>No analysis results available</i>")
            return
        
        valid_results = [r for r in self.analysis_results.values() if r.calculation_valid]
        
        if not valid_results:
            self.performance_text.setHtml("<i>No valid analysis results</i>")
            return
        
        # Calculate statistics
        nc_ratings = [r.nc_rating for r in valid_results]
        terminal_noises = [r.terminal_noise for r in valid_results]
        attenuations = [r.total_attenuation for r in valid_results]
        
        html = "<h4>Performance Summary</h4>"
        html += f"<p><b>Paths Analyzed:</b> {len(valid_results)}</p>"
        html += f"<p><b>Average NC Rating:</b> {sum(nc_ratings)/len(nc_ratings):.1f}</p>"
        html += f"<p><b>Best NC Rating:</b> {min(nc_ratings):.0f}</p>"
        html += f"<p><b>Worst NC Rating:</b> {max(nc_ratings):.0f}</p>"
        html += f"<p><b>Average Terminal Noise:</b> {sum(terminal_noises)/len(terminal_noises):.1f} dB(A)</p>"
        html += f"<p><b>Average Attenuation:</b> {sum(attenuations)/len(attenuations):.1f} dB</p>"
        
        # Performance categories
        excellent = len([r for r in valid_results if r.nc_rating <= 30])
        good = len([r for r in valid_results if 30 < r.nc_rating <= 40])
        poor = len([r for r in valid_results if r.nc_rating > 40])
        
        html += "<h5>Performance Distribution</h5>"
        html += f"<p>Excellent (NC ≤ 30): {excellent} paths<br>"
        html += f"Good (NC 31-40): {good} paths<br>"
        html += f"Poor (NC > 40): {poor} paths</p>"
        
        self.performance_text.setHtml(html)
    
    def update_chart(self):
        """Update the chart display"""
        if not self.analysis_results:
            return
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        chart_type = self.chart_type_combo.currentText()
        valid_results = [(p, r) for p, r in zip(self.selected_paths, self.analysis_results.values()) 
                        if r.calculation_valid]
        
        if not valid_results:
            ax.text(0.5, 0.5, 'No valid data to display', ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw()
            return
        
        paths = [p.name for p, _ in valid_results]
        
        if chart_type == "Noise Levels":
            source_noises = [r.source_noise for _, r in valid_results]
            terminal_noises = [r.terminal_noise for _, r in valid_results]
            
            x = range(len(paths))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], source_noises, width, label='Source Noise', alpha=0.8)
            ax.bar([i + width/2 for i in x], terminal_noises, width, label='Terminal Noise', alpha=0.8)
            
            ax.set_ylabel('Noise Level (dB(A))')
            ax.set_title('HVAC Path Noise Levels')
            ax.legend()
            
        elif chart_type == "Attenuation":
            attenuations = [r.total_attenuation for _, r in valid_results]
            
            ax.bar(paths, attenuations, alpha=0.8)
            ax.set_ylabel('Attenuation (dB)')
            ax.set_title('HVAC Path Attenuation')
            
        elif chart_type == "NC Ratings":
            nc_ratings = [r.nc_rating for _, r in valid_results]
            
            bars = ax.bar(paths, nc_ratings, alpha=0.8)
            
            # Color code bars
            for bar, nc in zip(bars, nc_ratings):
                if nc <= 30:
                    bar.set_color('green')
                elif nc <= 40:
                    bar.set_color('yellow')
                else:
                    bar.set_color('red')
            
            ax.set_ylabel('NC Rating')
            ax.set_title('HVAC Path NC Ratings')
            
            # Add target lines
            ax.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Excellent (NC 30)')
            ax.axhline(y=40, color='orange', linestyle='--', alpha=0.7, label='Good (NC 40)')
            ax.legend()
        
        ax.set_xticklabels(paths, rotation=45, ha='right')
        self.figure.tight_layout()
        self.canvas.draw()
    
    def export_results(self):
        """Export analysis results"""
        if not self.analysis_results:
            QMessageBox.information(self, "No Data", "No analysis results to export.")
            return
        
        try:
            from data.excel_exporter import ExcelExporter
            
            if not ExcelExporter.is_available():
                QMessageBox.warning(self, "Export Not Available", 
                                   "Excel export is not available. Please install openpyxl.")
                return
            
            # Prepare data for export
            export_data = []
            for path_id, result in self.analysis_results.items():
                path = next((p for p in self.selected_paths if p.id == path_id), None)
                if not path:
                    continue
                
                export_data.append({
                    'Path Name': path.name,
                    'Path Type': path.path_type or 'unknown',
                    'Target Space': path.target_space.name if path.target_space else 'None',
                    'Source Noise (dB(A))': result.source_noise if result.calculation_valid else 0,
                    'Terminal Noise (dB(A))': result.terminal_noise if result.calculation_valid else 0,
                    'Total Attenuation (dB)': result.total_attenuation if result.calculation_valid else 0,
                    'NC Rating': result.nc_rating if result.calculation_valid else 0,
                    'Calculation Valid': result.calculation_valid,
                    'Warnings': '; '.join(result.warnings) if result.warnings else ''
                })
            
            # Export to Excel
            exporter = ExcelExporter()
            filename = f"hvac_path_analysis_{self.project_id}.xlsx"
            
            success = exporter.export_data(export_data, filename, "HVAC Path Analysis")
            
            if success:
                QMessageBox.information(self, "Export Successful", 
                                       f"Results exported to {filename}")
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to export results.")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error during export:\n{str(e)}")


# Convenience function to show dialog
def show_hvac_path_analysis_dialog(parent=None, project_id=None, space_id=None):
    """Show HVAC path analysis dialog"""
    dialog = HVACPathAnalysisDialog(parent, project_id, space_id)
    return dialog.exec() 