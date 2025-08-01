"""
Results Widget - Comprehensive display of acoustic analysis results
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTabWidget, QTableWidget, QTableWidgetItem,
                             QTextEdit, QGroupBox, QPushButton, QFrame,
                             QScrollArea, QProgressBar, QSplitter)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPalette, QColor

from models import get_session, Project, Space, Drawing
from models.hvac import HVACPath, HVACComponent
from calculations import HVACPathCalculator, NCRatingAnalyzer
from data.excel_exporter import ExcelExporter, EXCEL_EXPORT_AVAILABLE


class ResultsWidget(QWidget):
    """Comprehensive results display widget"""
    
    export_requested = Signal()
    
    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project = None
        
        # Calculators
        self.hvac_calculator = HVACPathCalculator()
        self.nc_analyzer = NCRatingAnalyzer()
        
        self.init_ui()
        self.load_project_data()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Header
        header = self.create_results_header()
        layout.addWidget(header)
        
        # Main content with tabs
        self.tab_widget = QTabWidget()
        
        # Summary tab
        self.summary_tab = self.create_summary_tab()
        self.tab_widget.addTab(self.summary_tab, "Project Summary")
        
        # Spaces tab
        self.spaces_tab = self.create_spaces_tab()
        self.tab_widget.addTab(self.spaces_tab, "Spaces Analysis")
        
        # HVAC tab
        self.hvac_tab = self.create_hvac_tab()
        self.tab_widget.addTab(self.hvac_tab, "HVAC Analysis")
        
        # NC Analysis tab
        self.nc_tab = self.create_nc_analysis_tab()
        self.tab_widget.addTab(self.nc_tab, "NC Compliance")
        
        # Issues & Recommendations tab
        self.issues_tab = self.create_issues_tab()
        self.tab_widget.addTab(self.issues_tab, "Issues & Recommendations")
        
        layout.addWidget(self.tab_widget)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh Data")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        self.export_btn = QPushButton("📊 Export to Excel")
        self.export_btn.clicked.connect(self.export_requested.emit)
        self.export_btn.setEnabled(EXCEL_EXPORT_AVAILABLE)
        
        self.recalc_btn = QPushButton("🧮 Recalculate All")
        self.recalc_btn.clicked.connect(self.recalculate_all)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.recalc_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_results_header(self):
        """Create results header with key metrics"""
        header = QFrame()
        header.setFrameStyle(QFrame.Box)
        header.setStyleSheet("QFrame { background-color: #f0f0f0; border: 1px solid #ccc; }")
        
        layout = QHBoxLayout()
        
        # Project info
        self.project_name_label = QLabel("Project: Loading...")
        self.project_name_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.project_name_label)
        
        layout.addStretch()
        
        # Key metrics
        self.spaces_count_label = QLabel("Spaces: 0")
        self.hvac_paths_label = QLabel("HVAC Paths: 0")
        self.avg_rt60_label = QLabel("Avg RT60: --")
        self.avg_nc_label = QLabel("Avg NC: --")
        
        for label in [self.spaces_count_label, self.hvac_paths_label, 
                      self.avg_rt60_label, self.avg_nc_label]:
            label.setFont(QFont("Arial", 10, QFont.Bold))
            layout.addWidget(label)
        
        header.setLayout(layout)
        return header
    
    def create_summary_tab(self):
        """Create project summary tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Progress overview
        progress_group = QGroupBox("Calculation Progress")
        progress_layout = QVBoxLayout()
        
        self.rt60_progress = QProgressBar()
        self.rt60_progress.setFormat("RT60 Calculations: %v/%m (%p%)")
        progress_layout.addWidget(QLabel("RT60 Analysis:"))
        progress_layout.addWidget(self.rt60_progress)
        
        self.hvac_progress = QProgressBar()
        self.hvac_progress.setFormat("HVAC Noise Calculations: %v/%m (%p%)")
        progress_layout.addWidget(QLabel("HVAC Noise Analysis:"))
        progress_layout.addWidget(self.hvac_progress)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Statistics summary
        stats_group = QGroupBox("Project Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Recent activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        
        self.activity_text = QTextEdit()
        self.activity_text.setMaximumHeight(150)
        self.activity_text.setReadOnly(True)
        activity_layout.addWidget(self.activity_text)
        
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_spaces_tab(self):
        """Create spaces analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Spaces table
        self.spaces_table = QTableWidget()
        self.spaces_table.setColumnCount(8)
        self.spaces_table.setHorizontalHeaderLabels([
            "Space Name", "Area (sf)", "Volume (cf)", "Target RT60", 
            "Calculated RT60", "Status", "Materials", "Issues"
        ])
        
        layout.addWidget(QLabel("Spaces RT60 Analysis:"))
        layout.addWidget(self.spaces_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_hvac_tab(self):
        """Create HVAC analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # HVAC paths table
        self.hvac_table = QTableWidget()
        self.hvac_table.setColumnCount(7)
        self.hvac_table.setHorizontalHeaderLabels([
            "Path Name", "Type", "Target Space", "Noise Level (dB)", 
            "NC Rating", "Length (ft)", "Status"
        ])
        
        layout.addWidget(QLabel("HVAC Noise Analysis:"))
        layout.addWidget(self.hvac_table)
        
        # HVAC summary
        hvac_summary_group = QGroupBox("HVAC Summary")
        hvac_summary_layout = QVBoxLayout()
        
        self.hvac_summary_text = QTextEdit()
        self.hvac_summary_text.setMaximumHeight(120)
        self.hvac_summary_text.setReadOnly(True)
        hvac_summary_layout.addWidget(self.hvac_summary_text)
        
        hvac_summary_group.setLayout(hvac_summary_layout)
        layout.addWidget(hvac_summary_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_nc_analysis_tab(self):
        """Create NC compliance analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # NC compliance table
        self.nc_table = QTableWidget()
        self.nc_table.setColumnCount(6)
        self.nc_table.setHorizontalHeaderLabels([
            "Space/Path", "Measured NC", "Required NC", "Status", 
            "Exceedance", "Space Type"
        ])
        
        layout.addWidget(QLabel("NC Compliance Analysis:"))
        layout.addWidget(self.nc_table)
        
        # NC distribution
        nc_dist_group = QGroupBox("NC Rating Distribution")
        nc_dist_layout = QVBoxLayout()
        
        self.nc_distribution_text = QTextEdit()
        self.nc_distribution_text.setMaximumHeight(150)
        self.nc_distribution_text.setReadOnly(True)
        nc_dist_layout.addWidget(self.nc_distribution_text)
        
        nc_dist_group.setLayout(nc_dist_layout)
        layout.addWidget(nc_dist_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_issues_tab(self):
        """Create issues and recommendations tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Issues list
        issues_group = QGroupBox("Issues Found")
        issues_layout = QVBoxLayout()
        
        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)
        issues_layout.addWidget(self.issues_text)
        
        issues_group.setLayout(issues_layout)
        layout.addWidget(issues_group)
        
        # Recommendations
        recommendations_group = QGroupBox("Recommendations")
        recommendations_layout = QVBoxLayout()
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        recommendations_layout.addWidget(self.recommendations_text)
        
        recommendations_group.setLayout(recommendations_layout)
        layout.addWidget(recommendations_group)
        
        widget.setLayout(layout)
        return widget
    
    def load_project_data(self):
        """Load project data from database"""
        try:
            session = get_session()
            self.project = session.query(Project).filter(Project.id == self.project_id).first()
            session.close()
            
            if self.project:
                self.project_name_label.setText(f"Project: {self.project.name}")
                self.refresh_data()
            
        except Exception as e:
            print(f"Error loading project data: {e}")
    
    def refresh_data(self):
        """Refresh all data displays"""
        try:
            session = get_session()
            
            # Get all project data
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            hvac_paths = session.query(HVACPath).filter(HVACPath.project_id == self.project_id).all()
            hvac_components = session.query(HVACComponent).filter(HVACComponent.project_id == self.project_id).all()
            drawings = session.query(Drawing).filter(Drawing.project_id == self.project_id).all()
            
            session.close()
            
            # Update header metrics
            self.update_header_metrics(spaces, hvac_paths)
            
            # Update summary tab
            self.update_summary_tab(spaces, hvac_paths, hvac_components, drawings)
            
            # Update spaces tab
            self.update_spaces_tab(spaces)
            
            # Update HVAC tab
            self.update_hvac_tab(hvac_paths)
            
            # Update NC analysis tab
            self.update_nc_analysis_tab(hvac_paths, spaces)
            
            # Update issues tab
            self.update_issues_tab(spaces, hvac_paths)
            
        except Exception as e:
            print(f"Error refreshing data: {e}")
    
    def update_header_metrics(self, spaces, hvac_paths):
        """Update header metrics"""
        self.spaces_count_label.setText(f"Spaces: {len(spaces)}")
        self.hvac_paths_label.setText(f"HVAC Paths: {len(hvac_paths)}")
        
        # Calculate averages
        rt60_values = [s.calculated_rt60 for s in spaces if s.calculated_rt60]
        if rt60_values:
            avg_rt60 = sum(rt60_values) / len(rt60_values)
            self.avg_rt60_label.setText(f"Avg RT60: {avg_rt60:.2f}s")
        else:
            self.avg_rt60_label.setText("Avg RT60: --")
        
        nc_values = [p.calculated_nc for p in hvac_paths if p.calculated_nc]
        if nc_values:
            avg_nc = sum(nc_values) / len(nc_values)
            self.avg_nc_label.setText(f"Avg NC: {avg_nc:.0f}")
        else:
            self.avg_nc_label.setText("Avg NC: --")
    
    def update_summary_tab(self, spaces, hvac_paths, hvac_components, drawings):
        """Update summary tab content"""
        # Update progress bars
        rt60_calculated = len([s for s in spaces if s.calculated_rt60])
        self.rt60_progress.setMaximum(len(spaces))
        self.rt60_progress.setValue(rt60_calculated)
        
        hvac_calculated = len([p for p in hvac_paths if p.calculated_noise])
        self.hvac_progress.setMaximum(len(hvac_paths))
        self.hvac_progress.setValue(hvac_calculated)
        
        # Update statistics
        stats_text = f"Project Statistics:\n\n"
        stats_text += f"• Total Drawings: {len(drawings)}\n"
        stats_text += f"• Total Spaces: {len(spaces)}\n"
        stats_text += f"• Spaces with RT60: {rt60_calculated} ({rt60_calculated/len(spaces)*100:.0f}%)\n" if spaces else "• No spaces defined\n"
        stats_text += f"• Total HVAC Paths: {len(hvac_paths)}\n"
        stats_text += f"• Paths with Noise Analysis: {hvac_calculated} ({hvac_calculated/len(hvac_paths)*100:.0f}%)\n" if hvac_paths else "• No HVAC paths defined\n"
        stats_text += f"• Total HVAC Components: {len(hvac_components)}\n\n"
        
        # Performance summary
        rt60_values = [s.calculated_rt60 for s in spaces if s.calculated_rt60]
        if spaces and rt60_values:
            stats_text += f"RT60 Performance:\n"
            stats_text += f"• Average: {sum(rt60_values)/len(rt60_values):.2f} seconds\n"
            stats_text += f"• Range: {min(rt60_values):.2f} - {max(rt60_values):.2f} seconds\n\n"
        
        nc_values = [p.calculated_nc for p in hvac_paths if p.calculated_nc]
        if hvac_paths and nc_values:
            stats_text += f"HVAC Noise Performance:\n"
            stats_text += f"• Average NC: {sum(nc_values)/len(nc_values):.0f}\n"
            stats_text += f"• NC Range: {min(nc_values)} - {max(nc_values)}\n"
            stats_text += f"• Paths exceeding NC-35: {len([n for n in nc_values if n > 35])}\n"
        
        self.stats_text.setPlainText(stats_text)
        
        # Update activity (simplified)
        activity_text = "Recent Activity:\n\n"
        activity_text += f"• Last data refresh: {QTimer().remainingTime()//1000}s ago\n"
        activity_text += f"• Calculations status: {'Complete' if rt60_calculated == len(spaces) and hvac_calculated == len(hvac_paths) else 'In Progress'}\n"
        
        self.activity_text.setPlainText(activity_text)
    
    def update_spaces_tab(self, spaces):
        """Update spaces analysis tab"""
        self.spaces_table.setRowCount(len(spaces))
        
        for row, space in enumerate(spaces):
            # Space name
            self.spaces_table.setItem(row, 0, QTableWidgetItem(space.name))
            
            # Area
            area_item = QTableWidgetItem(f"{space.floor_area or 0:.0f}")
            self.spaces_table.setItem(row, 1, area_item)
            
            # Volume
            volume_item = QTableWidgetItem(f"{space.volume or 0:.0f}")
            self.spaces_table.setItem(row, 2, volume_item)
            
            # Target RT60
            target_item = QTableWidgetItem(f"{space.target_rt60 or 0:.2f}")
            self.spaces_table.setItem(row, 3, target_item)
            
            # Calculated RT60
            calc_rt60 = space.calculated_rt60 or 0
            calc_item = QTableWidgetItem(f"{calc_rt60:.2f}")
            self.spaces_table.setItem(row, 4, calc_item)
            
            # Status
            if space.calculated_rt60 and space.target_rt60:
                difference = abs(space.calculated_rt60 - space.target_rt60)
                tolerance = space.target_rt60 * 0.1
                status = "✓ Good" if difference <= tolerance else "⚠ Check"
                status_item = QTableWidgetItem(status)
                if status.startswith("⚠"):
                    status_item.setBackground(QColor(255, 255, 0, 100))  # Light yellow
            else:
                status_item = QTableWidgetItem("-- Pending")
            
            self.spaces_table.setItem(row, 5, status_item)
            
            # Materials summary
            materials = []
            if space.ceiling_material:
                materials.append(f"C:{space.ceiling_material[:10]}")
            if space.wall_material:
                materials.append(f"W:{space.wall_material[:10]}")
            if space.floor_material:
                materials.append(f"F:{space.floor_material[:10]}")
            
            materials_item = QTableWidgetItem(", ".join(materials))
            self.spaces_table.setItem(row, 6, materials_item)
            
            # Issues
            issues = []
            if not space.calculated_rt60:
                issues.append("No RT60")
            elif space.target_rt60 and abs(space.calculated_rt60 - space.target_rt60) > space.target_rt60 * 0.1:
                issues.append("RT60 out of tolerance")
            
            issues_item = QTableWidgetItem(", ".join(issues) if issues else "None")
            self.spaces_table.setItem(row, 7, issues_item)
        
        self.spaces_table.resizeColumnsToContents()
    
    def update_hvac_tab(self, hvac_paths):
        """Update HVAC analysis tab"""
        self.hvac_table.setRowCount(len(hvac_paths))
        
        for row, path in enumerate(hvac_paths):
            # Path name
            self.hvac_table.setItem(row, 0, QTableWidgetItem(path.name))
            
            # Type
            self.hvac_table.setItem(row, 1, QTableWidgetItem(path.path_type or "supply"))
            
            # Target space
            target_space = path.target_space.name if path.target_space else "None"
            self.hvac_table.setItem(row, 2, QTableWidgetItem(target_space))
            
            # Noise level
            noise_level = path.calculated_noise or 0
            noise_item = QTableWidgetItem(f"{noise_level:.1f}")
            self.hvac_table.setItem(row, 3, noise_item)
            
            # NC rating
            nc_rating = path.calculated_nc or 0
            nc_item = QTableWidgetItem(f"NC-{nc_rating}")
            if nc_rating > 45:
                nc_item.setBackground(QColor(255, 200, 200))  # Light red
            elif nc_rating > 35:
                nc_item.setBackground(QColor(255, 255, 200))  # Light yellow
            self.hvac_table.setItem(row, 4, nc_item)
            
            # Length
            total_length = sum(seg.length or 0 for seg in path.segments)
            length_item = QTableWidgetItem(f"{total_length:.0f}")
            self.hvac_table.setItem(row, 5, length_item)
            
            # Status
            if path.calculated_noise:
                status = "✓ Complete"
            else:
                status = "-- Pending"
            self.hvac_table.setItem(row, 6, QTableWidgetItem(status))
        
        self.hvac_table.resizeColumnsToContents()
        
        # Update HVAC summary
        if hvac_paths:
            noise_levels = [p.calculated_noise for p in hvac_paths if p.calculated_noise]
            nc_ratings = [p.calculated_nc for p in hvac_paths if p.calculated_nc]
            
            summary_text = "HVAC Analysis Summary:\n\n"
            if noise_levels:
                summary_text += f"• Average Noise Level: {sum(noise_levels)/len(noise_levels):.1f} dB(A)\n"
                summary_text += f"• Noise Range: {min(noise_levels):.1f} - {max(noise_levels):.1f} dB(A)\n"
            
            if nc_ratings:
                summary_text += f"• Average NC Rating: NC-{sum(nc_ratings)/len(nc_ratings):.0f}\n"
                summary_text += f"• NC Range: NC-{min(nc_ratings)} to NC-{max(nc_ratings)}\n"
                summary_text += f"• Paths exceeding NC-35: {len([n for n in nc_ratings if n > 35])}\n"
                summary_text += f"• Paths exceeding NC-45: {len([n for n in nc_ratings if n > 45])}\n"
        else:
            summary_text = "No HVAC paths analyzed yet."
        
        self.hvac_summary_text.setPlainText(summary_text)
    
    def update_nc_analysis_tab(self, hvac_paths, spaces):
        """Update NC compliance analysis tab"""
        # For now, use HVAC paths data
        self.nc_table.setRowCount(len(hvac_paths))
        
        for row, path in enumerate(hvac_paths):
            # Path name
            self.nc_table.setItem(row, 0, QTableWidgetItem(path.name))
            
            # Measured NC
            measured_nc = path.calculated_nc or 0
            self.nc_table.setItem(row, 1, QTableWidgetItem(f"NC-{measured_nc}"))
            
            # Required NC (simplified - would need space type info)
            required_nc = 35  # Default office requirement
            self.nc_table.setItem(row, 2, QTableWidgetItem(f"NC-{required_nc}"))
            
            # Status
            if measured_nc <= required_nc:
                status = "✓ Compliant"
                status_item = QTableWidgetItem(status)
                status_item.setBackground(QColor(200, 255, 200))  # Light green
            else:
                status = "✗ Non-compliant"
                status_item = QTableWidgetItem(status)
                status_item.setBackground(QColor(255, 200, 200))  # Light red
            
            self.nc_table.setItem(row, 3, status_item)
            
            # Exceedance
            exceedance = max(0, measured_nc - required_nc)
            exceedance_text = f"+{exceedance}" if exceedance > 0 else "0"
            self.nc_table.setItem(row, 4, QTableWidgetItem(exceedance_text))
            
            # Space type (simplified)
            space_type = "Office"  # Would need actual space type data
            self.nc_table.setItem(row, 5, QTableWidgetItem(space_type))
        
        self.nc_table.resizeColumnsToContents()
        
        # Update NC distribution
        if hvac_paths:
            nc_ratings = [p.calculated_nc for p in hvac_paths if p.calculated_nc]
            if nc_ratings:
                dist_text = "NC Rating Distribution:\n\n"
                
                # Count by NC ranges
                nc_ranges = {
                    "NC-15 to NC-25": len([n for n in nc_ratings if 15 <= n <= 25]),
                    "NC-26 to NC-35": len([n for n in nc_ratings if 26 <= n <= 35]),
                    "NC-36 to NC-45": len([n for n in nc_ratings if 36 <= n <= 45]),
                    "NC-46 and above": len([n for n in nc_ratings if n > 45])
                }
                
                for range_name, count in nc_ranges.items():
                    percentage = (count / len(nc_ratings)) * 100
                    dist_text += f"• {range_name}: {count} paths ({percentage:.0f}%)\n"
                
                dist_text += f"\nTotal analyzed paths: {len(nc_ratings)}"
            else:
                dist_text = "No NC ratings calculated yet."
        else:
            dist_text = "No HVAC paths defined."
        
        self.nc_distribution_text.setPlainText(dist_text)
    
    def update_issues_tab(self, spaces, hvac_paths):
        """Update issues and recommendations tab"""
        issues = []
        recommendations = []
        
        # Analyze spaces issues
        for space in spaces:
            if not space.calculated_rt60:
                issues.append(f"Space '{space.name}': No RT60 calculation")
                recommendations.append(f"Calculate RT60 for space '{space.name}' using room properties dialog")
            elif space.target_rt60:
                difference = abs(space.calculated_rt60 - space.target_rt60)
                if difference > space.target_rt60 * 0.1:
                    issues.append(f"Space '{space.name}': RT60 out of tolerance ({space.calculated_rt60:.2f}s vs target {space.target_rt60:.2f}s)")
                    if space.calculated_rt60 > space.target_rt60:
                        recommendations.append(f"Add sound absorption to space '{space.name}' to reduce RT60")
                    else:
                        recommendations.append(f"Reduce sound absorption in space '{space.name}' to increase RT60")
        
        # Analyze HVAC issues
        for path in hvac_paths:
            if not path.calculated_noise:
                issues.append(f"HVAC Path '{path.name}': No noise calculation")
                recommendations.append(f"Calculate noise for HVAC path '{path.name}' using path analysis tools")
            elif path.calculated_nc and path.calculated_nc > 35:
                issues.append(f"HVAC Path '{path.name}': High NC rating (NC-{path.calculated_nc})")
                if path.calculated_nc > 45:
                    recommendations.append(f"Major noise control required for path '{path.name}' - consider equipment replacement")
                else:
                    recommendations.append(f"Add duct silencing for path '{path.name}' to reduce noise levels")
        
        # Update issues text
        if issues:
            issues_text = "Issues Found:\n\n"
            for i, issue in enumerate(issues, 1):
                issues_text += f"{i}. {issue}\n"
        else:
            issues_text = "No issues found. ✓"
        
        self.issues_text.setPlainText(issues_text)
        
        # Update recommendations text
        if recommendations:
            rec_text = "Recommendations:\n\n"
            for i, rec in enumerate(recommendations, 1):
                rec_text += f"{i}. {rec}\n"
        else:
            rec_text = "No recommendations at this time."
        
        self.recommendations_text.setPlainText(rec_text)
    
    def recalculate_all(self):
        """Recalculate all analyses"""
        try:
            # Get all paths and recalculate
            results = self.hvac_calculator.calculate_all_project_paths(self.project_id)
            
            completed = len([r for r in results if r.calculation_valid])
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Recalculation Complete", 
                                   f"Recalculated {completed} HVAC paths.\n"
                                   f"Results have been updated in the database.")
            
            # Refresh display
            self.refresh_data()
            
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Recalculation Error", f"Failed to recalculate:\n{str(e)}")
    
    def closeEvent(self, event):
        """Clean up when widget is closed"""
        if self.refresh_timer:
            self.refresh_timer.stop()
        event.accept()