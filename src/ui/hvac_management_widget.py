"""
HVAC Management Widget - Comprehensive HVAC path management interface
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QPushButton, QGroupBox, QDoubleSpinBox,
                             QMessageBox, QSpinBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QListWidget,
                             QListWidgetItem, QSplitter, QTabWidget, QWidget,
                             QProgressDialog, QFrame, QDialog)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon

from models import get_session
from models.hvac import HVACPath, HVACComponent, HVACSegment
from models.space import Space
from calculations.hvac_path_calculator import HVACPathCalculator
from ui.dialogs.hvac_component_dialog import HVACComponentDialog
from ui.dialogs.hvac_segment_dialog import HVACSegmentDialog
from ui.dialogs.hvac_path_dialog import HVACPathDialog
from ui.dialogs.hvac_path_analysis_dialog import HVACPathAnalysisDialog
from sqlalchemy.orm import selectinload


class HVACManagementWidget(QWidget):
    """Comprehensive HVAC management widget"""
    
    # Signals
    path_created = Signal(HVACPath)
    path_updated = Signal(HVACPath)
    path_deleted = Signal(int)  # path_id
    component_created = Signal(HVACComponent)
    component_updated = Signal(HVACComponent)
    component_deleted = Signal(int)  # component_id
    
    def __init__(self, project_id=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.current_path = None
        self.current_component = None
        
        # Calculator
        self.path_calculator = HVACPathCalculator()
        
        # Data refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        header_label = QLabel("HVAC Path Management")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        # Quick actions
        self.new_path_btn = QPushButton("New Path")
        self.new_path_btn.clicked.connect(self.create_new_path)
        header_layout.addWidget(self.new_path_btn)
        
        self.new_component_btn = QPushButton("New Component")
        self.new_component_btn.clicked.connect(self.create_new_component)
        header_layout.addWidget(self.new_component_btn)
        
        self.analyze_btn = QPushButton("Analyze Paths")
        self.analyze_btn.clicked.connect(self.analyze_paths)
        header_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(header_layout)
        
        # Main content in splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Paths and components
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Details and analysis
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)
        
        self.setLayout(layout)
        
    def create_left_panel(self):
        """Create the left panel with paths and components"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Paths section
        paths_group = QGroupBox("HVAC Paths")
        paths_layout = QVBoxLayout()
        
        # Path list
        self.paths_list = QListWidget()
        self.paths_list.itemClicked.connect(self.on_path_selected)
        self.paths_list.itemDoubleClicked.connect(self.edit_path)
        paths_layout.addWidget(self.paths_list)
        
        # Path buttons
        path_buttons_layout = QHBoxLayout()
        
        self.edit_path_btn = QPushButton("Edit")
        self.edit_path_btn.setEnabled(False)
        self.edit_path_btn.clicked.connect(self.edit_path)
        path_buttons_layout.addWidget(self.edit_path_btn)
        
        self.delete_path_btn = QPushButton("Delete")
        self.delete_path_btn.setEnabled(False)
        self.delete_path_btn.clicked.connect(self.delete_path)
        path_buttons_layout.addWidget(self.delete_path_btn)
        
        path_buttons_layout.addStretch()
        paths_layout.addLayout(path_buttons_layout)
        
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # Components section
        components_group = QGroupBox("HVAC Components")
        components_layout = QVBoxLayout()
        
        # Component list
        self.components_list = QListWidget()
        self.components_list.itemClicked.connect(self.on_component_selected)
        self.components_list.itemDoubleClicked.connect(self.edit_component)
        components_layout.addWidget(self.components_list)
        
        # Component buttons
        comp_buttons_layout = QHBoxLayout()
        
        self.edit_component_btn = QPushButton("Edit")
        self.edit_component_btn.setEnabled(False)
        self.edit_component_btn.clicked.connect(self.edit_component)
        comp_buttons_layout.addWidget(self.edit_component_btn)
        
        self.delete_component_btn = QPushButton("Delete")
        self.delete_component_btn.setEnabled(False)
        self.delete_component_btn.clicked.connect(self.delete_component)
        comp_buttons_layout.addWidget(self.delete_component_btn)
        
        comp_buttons_layout.addStretch()
        components_layout.addLayout(comp_buttons_layout)
        
        components_group.setLayout(components_layout)
        layout.addWidget(components_group)
        
        panel.setLayout(layout)
        return panel
        
    def create_right_panel(self):
        """Create the right panel with details and analysis"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Tabs for different views
        tabs = QTabWidget()
        
        # Details tab
        details_tab = self.create_details_tab()
        tabs.addTab(details_tab, "Details")
        
        # Analysis tab
        analysis_tab = self.create_analysis_tab()
        tabs.addTab(analysis_tab, "Analysis")
        
        # Summary tab
        summary_tab = self.create_summary_tab()
        tabs.addTab(summary_tab, "Summary")
        
        layout.addWidget(tabs)
        panel.setLayout(layout)
        return panel
        
    def create_details_tab(self):
        """Create the details tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Path details
        self.path_details_group = QGroupBox("Path Details")
        path_details_layout = QVBoxLayout()
        
        self.path_details_text = QTextEdit()
        self.path_details_text.setReadOnly(True)
        self.path_details_text.setMaximumHeight(200)
        self.path_details_text.setHtml("<i>Select a path to view details</i>")
        path_details_layout.addWidget(self.path_details_text)
        
        self.path_details_group.setLayout(path_details_layout)
        layout.addWidget(self.path_details_group)
        
        # Component details
        self.component_details_group = QGroupBox("Component Details")
        component_details_layout = QVBoxLayout()
        
        self.component_details_text = QTextEdit()
        self.component_details_text.setReadOnly(True)
        self.component_details_text.setMaximumHeight(200)
        self.component_details_text.setHtml("<i>Select a component to view details</i>")
        component_details_layout.addWidget(self.component_details_text)
        
        self.component_details_group.setLayout(component_details_layout)
        layout.addWidget(self.component_details_group)
        
        # Segments table
        segments_group = QGroupBox("Path Segments")
        segments_layout = QVBoxLayout()
        
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(6)
        self.segments_table.setHorizontalHeaderLabels([
            "Order", "From", "To", "Length", "Duct Size", "Actions"
        ])
        
        # Set column widths
        header = self.segments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        segments_layout.addWidget(self.segments_table)
        
        # Segment buttons
        segment_buttons_layout = QHBoxLayout()
        
        self.add_segment_btn = QPushButton("Add Segment")
        self.add_segment_btn.setEnabled(False)
        self.add_segment_btn.clicked.connect(self.add_segment)
        segment_buttons_layout.addWidget(self.add_segment_btn)
        
        self.edit_segment_btn = QPushButton("Edit Segment")
        self.edit_segment_btn.setEnabled(False)
        self.edit_segment_btn.clicked.connect(self.edit_segment)
        segment_buttons_layout.addWidget(self.edit_segment_btn)
        
        segment_buttons_layout.addStretch()
        segments_layout.addLayout(segment_buttons_layout)
        
        segments_group.setLayout(segments_layout)
        layout.addWidget(segments_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_analysis_tab(self):
        """Create the analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Associations (Primary Source and Receiver Room)
        assoc_group = QGroupBox("Path Associations")
        assoc_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.receiver_combo = QComboBox()
        self.save_assoc_btn = QPushButton("Save Associations")
        assoc_layout.addWidget(QLabel("Primary Source:"))
        assoc_layout.addWidget(self.source_combo)
        assoc_layout.addSpacing(12)
        assoc_layout.addWidget(QLabel("Receiver Room:"))
        assoc_layout.addWidget(self.receiver_combo)
        assoc_layout.addStretch()
        assoc_layout.addWidget(self.save_assoc_btn)
        assoc_group.setLayout(assoc_layout)
        layout.addWidget(assoc_group)

        # Analysis results
        analysis_group = QGroupBox("Path Analysis")
        analysis_layout = QVBoxLayout()
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setHtml("<i>Select a path and click 'Analyze' to view results</i>")
        analysis_layout.addWidget(self.analysis_text)
        
        # Analysis buttons
        analysis_buttons_layout = QHBoxLayout()
        
        self.analyze_current_btn = QPushButton("Analyze Current Path")
        self.analyze_current_btn.setEnabled(False)
        self.analyze_current_btn.clicked.connect(self.analyze_current_path)
        analysis_buttons_layout.addWidget(self.analyze_current_btn)
        
        self.calculate_all_btn = QPushButton("Calculate All Paths")
        self.calculate_all_btn.clicked.connect(self.calculate_all_paths)
        analysis_buttons_layout.addWidget(self.calculate_all_btn)
        
        analysis_buttons_layout.addStretch()
        analysis_layout.addLayout(analysis_buttons_layout)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        # Performance summary
        performance_group = QGroupBox("Performance Summary")
        performance_layout = QVBoxLayout()
        
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setMaximumHeight(150)
        performance_layout.addWidget(self.performance_text)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        layout.addStretch()
        widget.setLayout(layout)

        # Wire actions
        self.save_assoc_btn.clicked.connect(self.save_path_associations)
        return widget
        
    def create_summary_tab(self):
        """Create the summary tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Project summary
        summary_group = QGroupBox("Project Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Quick stats
        stats_group = QGroupBox("Quick Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_text = QLabel("Loading statistics...")
        stats_layout.addWidget(self.stats_text)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        widget.setLayout(layout)
        return widget
        
    def load_data(self):
        """Load HVAC data from database"""
        try:
            session = get_session()
            
            # Load paths with required relationships eagerly to avoid lazy-load after session close
            paths = (
                session.query(HVACPath)
                .options(
                    selectinload(HVACPath.target_space),
                    selectinload(HVACPath.primary_source),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                    selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                )
                .filter(HVACPath.project_id == self.project_id)
                .all()
            )
            
            self.paths_list.clear()
            for path in paths:
                space_name = path.target_space.name if path.target_space else "None"
                item_text = f"{path.name} ({path.path_type}) → {space_name}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, path)
                self.paths_list.addItem(item)
            
            # Load components
            components = session.query(HVACComponent).filter(
                HVACComponent.project_id == self.project_id
            ).all()
            
            self.components_list.clear()
            for component in components:
                item_text = f"{component.name} ({component.component_type})"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, component)
                self.components_list.addItem(item)
            
            # Load spaces
            spaces = session.query(Space).filter(Space.project_id == self.project_id).all()
            session.close()
            
            # Update summary
            self.update_summary()

            # Populate combos
            self.populate_source_receiver_combos(components, spaces)
            
        except Exception as e:
            print(f"Error loading HVAC data: {e}")

    def populate_source_receiver_combos(self, components, spaces):
        self.source_combo.clear()
        for comp in components:
            self.source_combo.addItem(f"{comp.name} ({comp.component_type})", comp.id)
        self.receiver_combo.clear()
        for sp in spaces:
            self.receiver_combo.addItem(sp.name, sp.id)
        # Default current selections for selected path
        if self.current_path:
            if getattr(self.current_path, 'primary_source_id', None):
                idx = self.source_combo.findData(self.current_path.primary_source_id)
                if idx >= 0:
                    self.source_combo.setCurrentIndex(idx)
            if getattr(self.current_path, 'target_space_id', None):
                idx = self.receiver_combo.findData(self.current_path.target_space_id)
                if idx >= 0:
                    self.receiver_combo.setCurrentIndex(idx)

    def save_path_associations(self):
        if not self.current_path:
            QMessageBox.information(self, "Save Associations", "Select a path first.")
            return
        session = get_session()
        try:
            db_path = session.query(HVACPath).filter(HVACPath.id == self.current_path.id).first()
            if not db_path:
                QMessageBox.warning(self, "Save Associations", "Path not found in database.")
                return
            db_path.primary_source_id = self.source_combo.currentData()
            db_path.target_space_id = self.receiver_combo.currentData()
            session.commit()
            # Update current object for UI display
            self.current_path.primary_source_id = db_path.primary_source_id
            self.current_path.target_space_id = db_path.target_space_id
            QMessageBox.information(self, "Save Associations", "Associations saved.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Save Associations", f"Failed to save: {e}")
        finally:
            session.close()
    
    def refresh_data(self):
        """Refresh data from database"""
        self.load_data()
    
    def on_path_selected(self, item):
        """Handle path selection"""
        self.current_path = item.data(Qt.UserRole)
        self.edit_path_btn.setEnabled(True)
        self.delete_path_btn.setEnabled(True)
        self.add_segment_btn.setEnabled(True)
        self.analyze_current_btn.setEnabled(True)
        
        self.update_path_details()
        self.update_segments_table()
    
    def on_component_selected(self, item):
        """Handle component selection"""
        self.current_component = item.data(Qt.UserRole)
        self.edit_component_btn.setEnabled(True)
        self.delete_component_btn.setEnabled(True)
        
        self.update_component_details()
    
    def update_path_details(self):
        """Update path details display"""
        if not self.current_path:
            return
        
        html = f"<h4>{self.current_path.name}</h4>"
        html += f"<p><b>Type:</b> {self.current_path.path_type or 'Unknown'}<br>"
        html += f"<b>Target Space:</b> {self.current_path.target_space.name if self.current_path.target_space else 'None'}<br>"
        html += f"<b>Components:</b> {len(self.current_path.segments) + 1 if self.current_path.segments else 0}<br>"
        html += f"<b>Segments:</b> {len(self.current_path.segments)}<br>"
        
        if self.current_path.calculated_noise:
            html += f"<b>Calculated Noise:</b> {self.current_path.calculated_noise:.1f} dB(A)<br>"
            html += f"<b>NC Rating:</b> NC-{self.current_path.calculated_nc:.0f}"
        
        if self.current_path.description:
            html += f"<br><br><b>Description:</b><br>{self.current_path.description}"
        
        html += "</p>"
        
        self.path_details_text.setHtml(html)
    
    def update_component_details(self):
        """Update component details display"""
        if not self.current_component:
            return
        
        html = f"<h4>{self.current_component.name}</h4>"
        html += f"<p><b>Type:</b> {self.current_component.component_type}<br>"
        html += f"<b>Position:</b> ({self.current_component.x_position:.0f}, {self.current_component.y_position:.0f})<br>"
        html += f"<b>Noise Level:</b> {self.current_component.noise_level:.1f} dB(A)<br>"
        html += f"<b>Created:</b> {self.current_component.created_date.strftime('%Y-%m-%d %H:%M')}</p>"
        
        self.component_details_text.setHtml(html)
    
    def update_segments_table(self):
        """Update segments table"""
        self.segments_table.setRowCount(0)
        
        if not self.current_path or not self.current_path.segments:
            return
        
        for segment in self.current_path.segments:
            row = self.segments_table.rowCount()
            self.segments_table.insertRow(row)
            
            # Order
            self.segments_table.setItem(row, 0, QTableWidgetItem(str(segment.segment_order)))
            
            # From component
            from_name = segment.from_component.name if segment.from_component else "Unknown"
            self.segments_table.setItem(row, 1, QTableWidgetItem(from_name))
            
            # To component
            to_name = segment.to_component.name if segment.to_component else "Unknown"
            self.segments_table.setItem(row, 2, QTableWidgetItem(to_name))
            
            # Length
            self.segments_table.setItem(row, 3, QTableWidgetItem(f"{segment.length:.1f} ft"))
            
            # Duct size
            if segment.duct_width and segment.duct_height:
                duct_size = f"{segment.duct_width:.0f}×{segment.duct_height:.0f}\""
            else:
                duct_size = "Unknown"
            self.segments_table.setItem(row, 4, QTableWidgetItem(duct_size))
            
            # Actions
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, seg=segment: self.edit_segment(seg))
            self.segments_table.setCellWidget(row, 5, edit_btn)
    
    def update_summary(self):
        """Update project summary"""
        try:
            session = get_session()
            
            # Get counts
            path_count = session.query(HVACPath).filter(
                HVACPath.project_id == self.project_id
            ).count()
            
            component_count = session.query(HVACComponent).filter(
                HVACComponent.project_id == self.project_id
            ).count()
            
            # Get calculated paths
            calculated_paths = session.query(HVACPath).filter(
                HVACPath.project_id == self.project_id,
                HVACPath.calculated_noise.isnot(None)
            ).all()
            
            session.close()
            
            # Update summary text
            html = f"<h4>HVAC Project Summary</h4>"
            html += f"<p><b>Total Paths:</b> {path_count}<br>"
            html += f"<b>Total Components:</b> {component_count}<br>"
            html += f"<b>Calculated Paths:</b> {len(calculated_paths)}</p>"
            
            if calculated_paths:
                avg_noise = sum(p.calculated_noise for p in calculated_paths) / len(calculated_paths)
                avg_nc = sum(p.calculated_nc for p in calculated_paths) / len(calculated_paths)
                
                html += f"<p><b>Average Terminal Noise:</b> {avg_noise:.1f} dB(A)<br>"
                html += f"<b>Average NC Rating:</b> NC-{avg_nc:.0f}</p>"
            
            self.summary_text.setHtml(html)
            
            # Update stats
            stats = f"Paths: {path_count} | Components: {component_count} | Calculated: {len(calculated_paths)}"
            self.stats_text.setText(stats)
            
        except Exception as e:
            print(f"Error updating summary: {e}")
    
    def create_new_path(self):
        """Create a new HVAC path"""
        dialog = HVACPathDialog(self, self.project_id)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()
            self.path_created.emit(dialog.path)
    
    def create_new_component(self):
        """Create a new HVAC component"""
        dialog = HVACComponentDialog(self, self.project_id, None, None)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()
            self.component_created.emit(dialog.component)
    
    def edit_path(self, item=None):
        """Edit the selected path"""
        if not item:
            item = self.paths_list.currentItem()
            if not item:
                return
        
        path = item.data(Qt.UserRole)
        dialog = HVACPathDialog(self, self.project_id, path)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()
            self.path_updated.emit(path)
    
    def edit_component(self, item=None):
        """Edit the selected component"""
        if not item:
            item = self.components_list.currentItem()
            if not item:
                return
        
        component = item.data(Qt.UserRole)
        dialog = HVACComponentDialog(self, self.project_id, None, component)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()
            self.component_updated.emit(component)
    
    def delete_path(self):
        """Delete the selected path"""
        if not self.current_path:
            return
        
        reply = QMessageBox.question(
            self, "Delete Path",
            f"Are you sure you want to delete '{self.current_path.name}'?\n\n"
            "This will also remove all segments and fittings associated with this path.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                session.delete(self.current_path)
                session.commit()
                session.close()
                
                self.load_data()
                self.path_deleted.emit(self.current_path.id)
                self.current_path = None
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete path:\n{str(e)}")
    
    def delete_component(self):
        """Delete the selected component"""
        if not self.current_component:
            return
        
        reply = QMessageBox.question(
            self, "Delete Component",
            f"Are you sure you want to delete '{self.current_component.name}'?\n\n"
            "This will also remove any segments connected to this component.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                session = get_session()
                session.delete(self.current_component)
                session.commit()
                session.close()
                
                self.load_data()
                self.component_deleted.emit(self.current_component.id)
                self.current_component = None
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete component:\n{str(e)}")
    
    def add_segment(self):
        """Add a new segment to the current path"""
        if not self.current_path:
            return
        
        # Get components for this path
        components = []
        for segment in self.current_path.segments:
            if segment.from_component and segment.from_component not in components:
                components.append(segment.from_component)
            if segment.to_component and segment.to_component not in components:
                components.append(segment.to_component)
        
        if len(components) < 2:
            QMessageBox.warning(self, "Not Enough Components", 
                               "Need at least 2 components to create a segment.")
            return
        
        # Determine from and to components
        from_component = components[-2] if len(components) > 1 else components[0]
        to_component = components[-1]
        
        dialog = HVACSegmentDialog(self, self.current_path.id, from_component, to_component, None)
        if dialog.exec() == QDialog.Accepted:
            self.update_segments_table()
    
    def edit_segment(self, segment=None):
        """Edit a segment"""
        if not segment:
            # Get selected segment from table
            current_row = self.segments_table.currentRow()
            if current_row < 0:
                return
            
            # This would need to be implemented based on how segments are stored
            return
        
        dialog = HVACSegmentDialog(self, self.current_path.id,
                                 segment.from_component, segment.to_component, segment)
        if dialog.exec() == QDialog.Accepted:
            self.update_segments_table()
    
    def analyze_paths(self):
        """Open the HVAC path analysis dialog"""
        dialog = HVACPathAnalysisDialog(self, self.project_id)
        dialog.exec()
    
    def analyze_current_path(self):
        """Analyze the current path"""
        if not self.current_path:
            return
        
        try:
            result = self.path_calculator.calculate_path_noise(self.current_path.id)
            
            html = "<h4>Path Analysis Results</h4>"
            
            if result.calculation_valid:
                html += f"<p><b>Source Noise:</b> {result.source_noise:.1f} dB(A)<br>"
                html += f"<b>Terminal Noise:</b> {result.terminal_noise:.1f} dB(A)<br>"
                html += f"<b>Total Attenuation:</b> {result.total_attenuation:.1f} dB<br>"
                html += f"<b>NC Rating:</b> NC-{result.nc_rating:.0f}</p>"
                
                # Segment breakdown
                html += "<h5>Segment Breakdown</h5>"
                html += "<table border='1' cellpadding='3'>"
                html += "<tr><th>Segment</th><th>Length</th><th>Noise Before</th><th>Noise After</th></tr>"
                
                for segment_result in result.segment_results:
                    html += f"<tr><td>{segment_result['segment_number']}</td>"
                    html += f"<td>{segment_result.get('length', 0):.1f} ft</td>"
                    html += f"<td>{segment_result['noise_before']:.1f} dB</td>"
                    html += f"<td>{segment_result['noise_after']:.1f} dB</td></tr>"
                
                html += "</table>"
                
                # Warnings
                if result.warnings:
                    html += "<h5>Warnings</h5><ul>"
                    for warning in result.warnings:
                        html += f"<li>{warning}</li>"
                    html += "</ul>"
            else:
                html += f"<p style='color: red;'>Calculation failed: {result.error_message}</p>"
            
            self.analysis_text.setHtml(html)
            
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"Failed to analyze path:\n{str(e)}")
    
    def calculate_all_paths(self):
        """Calculate all paths in the project"""
        try:
            results = self.path_calculator.calculate_all_project_paths(self.project_id)
            
            valid_results = [r for r in results if r.calculation_valid]
            
            html = "<h4>All Paths Analysis</h4>"
            html += f"<p><b>Paths Analyzed:</b> {len(results)}<br>"
            html += f"<b>Valid Calculations:</b> {len(valid_results)}</p>"
            
            if valid_results:
                avg_noise = sum(r.terminal_noise for r in valid_results) / len(valid_results)
                avg_nc = sum(r.nc_rating for r in valid_results) / len(valid_results)
                
                html += f"<p><b>Average Terminal Noise:</b> {avg_noise:.1f} dB(A)<br>"
                html += f"<b>Average NC Rating:</b> NC-{avg_nc:.0f}</p>"
                
                # Performance summary
                excellent = len([r for r in valid_results if r.nc_rating <= 30])
                good = len([r for r in valid_results if 30 < r.nc_rating <= 40])
                poor = len([r for r in valid_results if r.nc_rating > 40])
                
                html += "<h5>Performance Distribution</h5>"
                html += f"<p>Excellent (NC ≤ 30): {excellent} paths<br>"
                html += f"Good (NC 31-40): {good} paths<br>"
                html += f"Poor (NC > 40): {poor} paths</p>"
            
            self.performance_text.setHtml(html)
            
            # Refresh data to show updated calculations
            self.load_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Failed to calculate all paths:\n{str(e)}")
    
    def set_project_id(self, project_id):
        """Set the project ID and reload data"""
        self.project_id = project_id
        self.load_data() 